"""Fail-closed official WhatsApp media retrieval helpers.

This module is not invoked by the simulated adapter. It provides the bounded, MIME/signature
checked boundary needed before an authorized live document webhook is connected.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, build_opener

from qshift.whatsapp_webhook import WebhookCredentials


class MediaDownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadedDocument:
    filename: str
    mime_type: str
    content: bytes


def safe_filename(filename: str) -> str:
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)[:120]
    if not name or name in {".", ".."}:
        raise MediaDownloadError("Document filename is invalid")
    return name


def validate_document(filename: str, mime_type: str, content: bytes, max_bytes: int = 10_000_000) -> DownloadedDocument:
    clean = safe_filename(filename)
    if len(content) == 0 or len(content) > max_bytes:
        raise MediaDownloadError("Document exceeds the configured size limit")
    suffix = clean.casefold().rsplit(".", 1)[-1] if "." in clean else ""
    if suffix == "csv":
        try:
            content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise MediaDownloadError("CSV is not valid UTF-8") from exc
        if mime_type not in {"text/csv", "application/csv", "application/octet-stream"}:
            raise MediaDownloadError("CSV MIME type is not allowed")
    elif suffix in {"xlsx", "xlsm"}:
        if mime_type not in {
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-excel.sheet.macroEnabled.12",
            "application/octet-stream",
        } or not content.startswith(b"PK"):
            raise MediaDownloadError("XLSX signature or MIME type is invalid")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if "[Content_Types].xml" not in archive.namelist():
                    raise MediaDownloadError("XLSX package is malformed")
        except zipfile.BadZipFile as exc:
            raise MediaDownloadError("XLSX package is malformed") from exc
    else:
        raise MediaDownloadError("Only CSV and XLSX documents are supported")
    return DownloadedDocument(clean, mime_type, content)


def download_meta_media(
    media_id: str,
    credentials: WebhookCredentials,
    access_token: str,
    graph_version: str,
    *,
    max_bytes: int = 10_000_000,
) -> DownloadedDocument:
    """Resolve and download one Meta media object using the official bearer-token flow."""

    if not re.fullmatch(r"[0-9]+", media_id):
        raise MediaDownloadError("Media ID is invalid")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+", graph_version) or not access_token:
        raise MediaDownloadError("Media credentials are not configured")
    opener = build_opener()
    metadata_request = Request(
        f"https://graph.facebook.com/{graph_version}/{media_id}",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with opener.open(metadata_request, timeout=15) as response:
            metadata = response.read(64_000)
        import json

        data = json.loads(metadata)
        url = data.get("url")
        mime_type = data.get("mime_type")
        filename = data.get("filename", f"qshift-{media_id}")
        if not isinstance(url, str) or not isinstance(mime_type, str) or urlparse(url).scheme != "https":
            raise MediaDownloadError("Meta returned an invalid media descriptor")
        media_request = Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with opener.open(media_request, timeout=30) as response:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = response.read(min(65_536, max_bytes + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > max_bytes:
                    raise MediaDownloadError("Media exceeds the configured size limit")
        return validate_document(str(filename), mime_type, b"".join(chunks), max_bytes)
    except MediaDownloadError:
        raise
    except Exception as exc:
        raise MediaDownloadError("Meta media retrieval failed") from exc
