"""Walk the operator through the one-phone QShift test on their Mac."""

import http.client
import json
import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import time
from contextlib import ExitStack
from getpass import getpass
from pathlib import Path
from queue import Empty, Queue
from tempfile import mkdtemp
from threading import Thread
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv/bin/python"
TUNNEL = Path(shutil.which("cloudflared") or ROOT / "work/tools/cloudflared")
OLLAMA = ROOT / "work/qshift-ollama"
MODEL_URL = "http://127.0.0.1:11434/api/tags"
MODEL_NAME = "qwen3:1.7b"


def model_ready():
    try:
        with urlopen(MODEL_URL, timeout=2) as response:
            return any(model["name"] == MODEL_NAME for model in json.load(response)["models"])
    except (OSError, ValueError, KeyError):
        return False


def ask(label, pattern, *, prompt):
    while True:
        value = prompt(label + " > ").strip()
        if re.fullmatch(pattern, value):
            return value
        print("Check that you copied the requested value, then try again.")


def local_port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def start(stack, command, env, *, capture=False):
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        start_new_session=True,
    )
    stack.callback(stop, process)
    return process


def wait_until_ready(process, url):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline and process.poll() is None:
        try:
            with urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (OSError, URLError):
            time.sleep(0.25)
    raise RuntimeError("QShift did not start. Check the Terminal output for the failed service.")


def tunnel_address(process):
    addresses = Queue()

    def watch():
        for line in process.stdout:
            match = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line)
            if match:
                addresses.put(match.group())
        addresses.put(None)

    Thread(target=watch, daemon=True).start()
    try:
        address = addresses.get(timeout=40)
    except Empty:
        address = None
    if not address:
        raise RuntimeError(
            "Cloudflare did not give QShift a temporary address. Check your internet and retry."
        )
    return address


def subscribe_test_account(version, account_id, access_token):
    connection = http.client.HTTPSConnection("graph.facebook.com", timeout=12)
    try:
        connection.request(
            "POST",
            f"/{version}/{account_id}/subscribed_apps",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response = connection.getresponse()
        payload = json.loads(response.read(16_384))
        if (
            response.status == 200
            and isinstance(payload, dict)
            and payload.get("success") in (True, "true")
        ):
            print("Meta confirmed the test account subscription.")
        else:
            print(
                f"Meta returned HTTP {response.status} for the subscription. If replies do not arrive, check the test account subscription in Meta."
            )
    except (OSError, http.client.HTTPException, ValueError):
        print(
            "Could not confirm the test account subscription. Check it in Meta if replies do not arrive."
        )
    finally:
        connection.close()


def run(*, prompt=None, hidden_prompt=None, output=print, operator_data=None):
    if prompt is None and not sys.stdin.isatty():
        raise RuntimeError("Open this setup in the Terminal app so your secrets stay hidden.")
    if not PYTHON.is_file() or not TUNNEL.is_file():
        raise RuntimeError("The local QShift installation or Cloudflare tool is missing.")

    prompt = input if prompt is None else prompt
    hidden_prompt = getpass if hidden_prompt is None else hidden_prompt

    def ask_value(label, pattern, *, hidden=False):
        if operator_data and (value := operator_data.get(label)) and re.fullmatch(pattern, value):
            return value
        return ask(label, pattern, prompt=hidden_prompt if hidden else prompt)

    def run_operator_command(command, command_env):
        result = subprocess.run(
            command, cwd=ROOT, env=command_env, text=True, capture_output=True, check=False
        )
        output((result.stdout + result.stderr).strip())

    output(
        "\n1. Open QShift in Meta Developer Apps. Open WhatsApp API Setup and select Meta's test number."
    )
    output("Use only the verified consenting tester’s phone and fictional quote data.")
    account_id = ask_value("WhatsApp Business Account ID", r"[0-9]{5,32}")
    number_id = ask_value("Phone Number ID from Meta API Setup", r"[0-9]{5,32}")
    sender_id = ask_value(
        "Your enrolled phone with country code and digits only", r"[0-9]{5,32}", hidden=True
    )
    output("Open App settings > Basic in Meta. Click Show next to App secret.")
    app_secret = ask_value(
        "Paste the App secret here. The text stays hidden", r"[!-~]{16,}", hidden=True
    )
    output(
        "\n2. QShift will use a free temporary Cloudflare address for Meta's incoming callbacks."
    )
    output(
        "Cloudflare relays the test phone and its fictional messages. The review screen stays on this Mac."
    )

    os.umask(0o077)
    (ROOT / "work").mkdir(exist_ok=True)
    database = Path(mkdtemp(prefix="whatsapp-test-", dir=ROOT / "work")) / "pilot.db"
    verify_token = secrets.token_urlsafe(30)
    base_env = {
        name: value for name, value in os.environ.items() if not name.startswith("QSHIFT_WHATSAPP_")
    }
    env = base_env | {
        "DATABASE_URL": f"sqlite:///{database}",
        "QSHIFT_WHATSAPP_RECEIVE_ENABLED": "true",
        "QSHIFT_WHATSAPP_DURABLE_INBOX": "true",
        "QSHIFT_PILOT_CALLBACK_ONLY": "true",
        "QSHIFT_INTAKE_MODEL": "ollama",
        "QSHIFT_APPROVAL_SECRET": secrets.token_hex(32),
        "QSHIFT_WHATSAPP_SEND_ENABLED": "false",
        "QSHIFT_WHATSAPP_ACCOUNT_ID": account_id,
        "QSHIFT_WHATSAPP_PHONE_NUMBER_ID": number_id,
        "QSHIFT_WHATSAPP_STAFF_SENDER_ID": sender_id,
        "QSHIFT_WHATSAPP_APP_SECRET": app_secret,
        "QSHIFT_WHATSAPP_VERIFY_TOKEN": verify_token,
    }
    subprocess.run([PYTHON, "-m", "alembic", "upgrade", "head"], cwd=ROOT, env=env, check=True)
    pilot_command = [PYTHON, "-m", "qshift.whatsapp_pilot"]
    subprocess.run([*pilot_command, "seed"], cwd=ROOT, env=env, check=True)

    with ExitStack() as stack:
        if not model_ready():
            if not (OLLAMA / "ollama").is_file():
                raise RuntimeError(f"Start local Ollama with {MODEL_NAME} available first.")
            model = start(
                stack,
                [OLLAMA / "ollama", "serve"],
                base_env
                | {
                    "OLLAMA_MODELS": str(OLLAMA / "models"),
                    "OLLAMA_HOST": "127.0.0.1:11434",
                },
            )
            wait_until_ready(model, MODEL_URL)
            if not model_ready():
                raise RuntimeError(f"Local Ollama is missing {MODEL_NAME}.")
        webhook_port = local_port()
        webhook_url = f"http://127.0.0.1:{webhook_port}"
        webhook = start(
            stack,
            [
                PYTHON,
                "-m",
                "uvicorn",
                "qshift.whatsapp_pilot:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(webhook_port),
                "--no-access-log",
            ],
            env,
        )
        probe = urlencode(
            {
                "hub.mode": "subscribe",
                "hub.verify_token": verify_token,
                "hub.challenge": "qshift-ready",
            }
        )
        wait_until_ready(webhook, f"{webhook_url}/webhooks/whatsapp?{probe}")
        tunnel = start(
            stack,
            [
                TUNNEL,
                "tunnel",
                "--no-autoupdate",
                "--protocol",
                "http2",
                "--url",
                webhook_url,
            ],
            base_env,
            capture=True,
        )
        callback = f"{tunnel_address(tunnel)}/webhooks/whatsapp"
        output("\n3. In Meta, open Step 2. Production setup > Configure Webhooks.")
        output("   Paste these into the two fields.")
        output(f"   Callback URL   {callback}")
        output(f"   Verify token   {verify_token}")
        output("   Choose Verify and save. Make sure the messages field says Subscribed.")
        prompt("Press Return once that is done > ")

        output(
            "\n4. Back in API Setup, generate a temporary token and find the API version in the example request."
        )
        access_token = ask_value(
            "Paste the temporary access token here. The text stays hidden", r"[!-~]+", hidden=True
        )
        version = ask_value("Graph API version, including the v", r"v[0-9]+\.[0-9]+")
        output(
            "\n5. This test is for the one enrolled phone. QShift stores its draft and reply receipts locally for review."
        )
        output(
            "Send STOP to end your participation. Press Control-C to close the test and its tunnel."
        )
        output("Use a short reference for the tester’s documented opt-in, for example CONSENT-001.")
        consent = ask_value("Consent reference", r"[A-Za-z0-9_-]{1,64}")
        subscribe_test_account(version, account_id, access_token)
        subprocess.run(
            [*pilot_command, "consent", "--first-quote", "--reference", consent],
            cwd=ROOT,
            env=env,
            check=True,
        )
        delivery_command = [PYTHON, "-m", "qshift.whatsapp_delivery"]
        send_env = env | {
            "QSHIFT_WHATSAPP_SEND_ENABLED": "true",
            "QSHIFT_WHATSAPP_ACCESS_TOKEN": access_token,
            "QSHIFT_WHATSAPP_GRAPH_VERSION": version,
        }
        worker = start(stack, [*delivery_command, "run"], send_env)
        output("\n6. From the verified tester’s phone, send this to Meta’s test number:")
        output("   Need a wardrobe for the guest bedroom, white laminate, 6 ft wide.")
        output("   When QShift asks how tall it is, reply: 7 feet")
        output("   Expected fictional quotation: ₹52,500.")
        output("   Available commands: review, approve <hash>, send <hash>, stop.")
        while True:
            if worker.poll() is not None or tunnel.poll() is not None or webhook.poll() is not None:
                raise RuntimeError("A pilot service stopped. Restart the pilot to try again.")
            action, _, digest = prompt("qshift pilot > ").strip().partition(" ")
            if action == "stop":
                break
            if action == "review":
                run_operator_command([*pilot_command, "review"], env)
            elif action in {"approve", "send"} and re.fullmatch(r"[0-9a-f]{64}", digest):
                command = (
                    [*pilot_command, "approve"]
                    if action == "approve"
                    else [*delivery_command, "document"]
                )
                run_operator_command(
                    [*command, "--hash", digest], env if action == "approve" else send_env
                )
            else:
                output("Use review, approve <hash>, send <hash>, or stop.")
        output("Remove the temporary callback in Meta and apply the agreed local retention period.")
        output(f"Private pilot data: {database.parent}")


def interrupt(_signum, _frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGHUP, interrupt)
    signal.signal(signal.SIGTERM, interrupt)
    try:
        run()
    except (EOFError, KeyboardInterrupt):
        print("\nQShift test stopped.")
    except (RuntimeError, OSError, subprocess.CalledProcessError) as error:
        print(f"QShift setup stopped. {error}", file=sys.stderr)
        sys.exit(1)
