"""Run the authenticated fictional studio workspace on loopback."""

import os
import secrets

import uvicorn


def main() -> None:
    os.environ["QSHIFT_STUDIO_MODE"] = "true"
    os.environ["QSHIFT_STUDIO_ORIGIN"] = "http://127.0.0.1:8079"
    os.environ.setdefault("QSHIFT_APPROVAL_SECRET", secrets.token_urlsafe(48))
    os.environ.setdefault("QSHIFT_INTAKE_MODEL", "ollama")
    uvicorn.run("qshift.api.main:app", host="127.0.0.1", port=8079, access_log=False)


if __name__ == "__main__":
    main()
