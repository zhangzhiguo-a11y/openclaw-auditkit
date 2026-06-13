"""Deterministic local reviewer.

This reviewer is deliberately conservative. It gives projects a useful default
without requiring API keys or model access.
"""

from __future__ import annotations

from .models import AuditPacket, ReviewResult, now_iso


def review_packet(packet: AuditPacket, *, reviewer: str = "auditkit-local") -> ReviewResult:
    if packet.risk_class == "C":
        return ReviewResult(
            status="rejected",
            reviewer=reviewer,
            reviewed_at=now_iso(),
            notes="C-class packets touch protected paths and are rejected by default.",
        )
    if not packet.evidence:
        return ReviewResult(
            status="needs_evidence",
            reviewer=reviewer,
            reviewed_at=now_iso(),
            notes="No evidence references are attached to the packet.",
        )
    if not packet.rollback:
        return ReviewResult(
            status="needs_owner_action",
            reviewer=reviewer,
            reviewed_at=now_iso(),
            notes="Rollback instructions are required before approval.",
        )
    if packet.risk_class == "B":
        return ReviewResult(
            status="needs_verification",
            reviewer=reviewer,
            reviewed_at=now_iso(),
            notes="B-class packets require maintainer verification and closeout receipt.",
        )
    return ReviewResult(
        status="approved",
        reviewer=reviewer,
        reviewed_at=now_iso(),
        notes="A-class packet has evidence and rollback instructions.",
    )

