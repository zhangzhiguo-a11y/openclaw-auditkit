"""Owner-routed follow-up tasks for unresolved audit feedback."""

from __future__ import annotations

from pathlib import Path
import json

from .models import AuditPacket, AuditStatus, EvidenceRef, now_iso
from .packet import write_packet


FOLLOWUP_ACTIONS: dict[str, tuple[str, str]] = {
    "needs_evidence": (
        "owner_provide_missing_evidence",
        "The implementing owner must add focused evidence that answers the reviewer notes.",
    ),
    "needs_owner_action": (
        "owner_repair_or_explain",
        "The implementing owner must repair the change or explain why the current proposal is safe.",
    ),
    "needs_verification": (
        "owner_run_verification",
        "The implementing owner must run the required verification and attach the result.",
    ),
    "defer": (
        "owner_clear_blocker",
        "The implementing owner must clear the blocker or attach current blocker evidence.",
    ),
    "rejected": (
        "owner_supersede_or_close",
        "The implementing owner must submit a safer superseding packet or keep the work rejected.",
    ),
}


def build_owner_followup(packet: AuditPacket) -> dict[str, object]:
    action, instruction = FOLLOWUP_ACTIONS.get(
        packet.status,
        ("owner_followup_not_required", "No owner follow-up is required for this status."),
    )
    return {
        "task_type": "audit_owner_followup",
        "created_at": now_iso(),
        "audit_id": packet.audit_id,
        "status": packet.status,
        "risk_class": packet.risk_class,
        "owner": packet.owner,
        "responsible_party": packet.owner,
        "required_owner_action": action,
        "owner_instruction": instruction,
        "reviewer_notes": packet.review_result.notes if packet.review_result else "",
        "intent_hash": packet.intent_hash,
        "confirmation_boundary": (
            "Maintainer or duty-officer closeout receipts are only for approved B-class packets. "
            "They do not replace the implementing owner's responsibility for evidence, repair, "
            "verification, or superseding rejected work."
        ),
    }


def write_owner_followup(packet: AuditPacket, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    task = build_owner_followup(packet)
    path = output_dir / "owner-followup-task.json"
    path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    packet.followup_task = task
    if not any(item.source_type == "owner_followup_task" and item.reference == str(path) for item in packet.evidence):
        packet.evidence.append(
            EvidenceRef(
                source_type="owner_followup_task",
                reference=str(path),
                summary="Owner-routed task for unresolved audit feedback.",
            )
        )
    write_packet(packet, output_dir.parent / "audit-packet.json")
    return path

