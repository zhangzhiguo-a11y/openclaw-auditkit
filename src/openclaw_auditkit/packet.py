"""Audit packet creation and persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json
import re

from .models import AuditPacket, EvidenceRef, now_iso, sha256_text
from .policy import classify_paths


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or "change"


def stable_audit_id(title: str, changed_files: Iterable[str]) -> str:
    digest = sha256_text("\n".join([title, *changed_files]))[:12]
    return f"audit-{slugify(title)}-{digest}"


def create_packet(
    *,
    title: str,
    owner: str,
    requester: str | None,
    changed_files: Iterable[str],
    summary: str = "",
    proposed_action: str = "",
    expected_impact: str = "",
    rollback: str = "",
) -> AuditPacket:
    files = list(changed_files)
    classification = classify_paths(files)
    evidence = [
        EvidenceRef(
            source_type="changed_file",
            reference=path,
            summary="Repository-relative changed file declared for audit evidence.",
        )
        for path in classification.changed_files
    ]
    return AuditPacket(
        audit_id=stable_audit_id(title, classification.changed_files),
        created_at=now_iso(),
        owner=owner,
        requester=requester or owner,
        risk_class=classification.risk_class,
        title=title,
        summary=summary,
        changed_files=classification.changed_files,
        proposed_action=proposed_action,
        expected_impact=expected_impact,
        rollback=rollback,
        evidence=evidence,
    )


def read_packet(path: Path) -> AuditPacket:
    return AuditPacket.from_dict(json.loads(path.read_text(encoding="utf-8")))


def write_packet(packet: AuditPacket, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

