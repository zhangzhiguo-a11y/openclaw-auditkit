"""Closeout receipts for approved or verified packets."""

from __future__ import annotations

from pathlib import Path
import json

from .models import AuditPacket, EvidenceRef, now_iso
from .packet import write_packet


def build_closeout_receipt(packet: AuditPacket, *, verified_by: str, notes: str = "") -> dict[str, object]:
    if packet.risk_class == "C":
        raise ValueError("C-class packets cannot be closed out; submit a safer superseding packet instead")
    if not verified_by:
        raise ValueError("verified_by is required")
    if not packet.rollback:
        raise ValueError("rollback instructions are required before closeout")
    if not packet.evidence:
        raise ValueError("evidence is required before closeout")
    return {
        "receipt_type": "auditkit_closeout_receipt",
        "created_at": now_iso(),
        "audit_id": packet.audit_id,
        "risk_class": packet.risk_class,
        "verified_by": verified_by,
        "decision": "approved",
        "intent_hash": packet.intent_hash,
        "notes": notes,
        "boundary": (
            "This receipt confirms closeout after technical evidence and owner responsibility checks. "
            "It is not a substitute for missing evidence or unresolved owner action."
        ),
    }


def closeout_packet(packet: AuditPacket, *, output_dir: Path, verified_by: str, notes: str = "") -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    receipt = build_closeout_receipt(packet, verified_by=verified_by, notes=notes)
    path = output_dir / "closeout-receipt.json"
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    packet.status = "approved"
    if not any(item.source_type == "closeout_receipt" and item.reference == str(path) for item in packet.evidence):
        packet.evidence.append(
            EvidenceRef(
                source_type="closeout_receipt",
                reference=str(path),
                summary="Maintainer or duty-officer closeout receipt.",
            )
        )
    write_packet(packet, output_dir.parent / "audit-packet.json")
    return path

