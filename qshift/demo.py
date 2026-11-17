"""Run the complete offline, fictional three-minute workflow from the terminal."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select

from qshift.agent.extraction import MockTranscriber
from qshift.db import Base, SessionLocal, engine
from qshift.models import User
from qshift.services import (
    approve_draft,
    issue_approval_token,
    pin_project,
    project_memory,
    resolve_catalogue,
    seed_demo,
    submit_change,
    versions,
)


def main() -> None:
    session = SessionLocal()
    try:
        Base.metadata.create_all(bind=engine)
        seed_demo(session, reset=True)
        designer = session.scalar(select(User).where(User.id == "user-designer"))
        approver = session.scalar(select(User).where(User.id == "user-approver"))
        assert designer and approver
        print("[0:00] SIMULATED — seed fictional Demo Interiors and Sharma Residence")
        print("[0:20] Pin project Sharma Residence")
        pin_project(session, designer, "project-sharma")
        transcript = MockTranscriber().transcribe("telugu_quartz_change")
        print(f"[0:40] Confirm MockTranscriber transcript: {transcript['text']}")
        draft = submit_change(session, designer, "project-sharma", transcript["text"])
        print(f"[1:10] Extracted {len(draft['ops'])} proposed operations; quartz choice required")
        draft = resolve_catalogue(session, designer, draft["id"], "COUNTER-QUARTZ-CALACATTA")
        print(
            f"[1:35] Draft ready: {draft['original_total']} → {draft['revised_total']} ({draft['net_change']})"
        )
        token = issue_approval_token(session, approver, draft["id"])
        approved = approve_draft(session, approver, token)
        print(f"[2:00] Human approval by APPROVER; revision v{approved['version']} generated")
        print(f"[2:20] PDF: {Path(approved['pdf_path']).resolve()}")
        print(
            "[2:35] Version history:",
            json.dumps(versions(session, designer, "project-sharma"), ensure_ascii=False),
        )
        print(
            "[2:50] Project memory:",
            json.dumps(project_memory(session, designer, "project-sharma"), ensure_ascii=False),
        )
        print("Demo complete. No live messaging or external send occurred.")
    finally:
        session.close()


if __name__ == "__main__":
    main()
