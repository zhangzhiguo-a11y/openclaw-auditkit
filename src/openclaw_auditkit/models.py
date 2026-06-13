"""Core data structures for AuditKit.

The structures are intentionally small and JSON-friendly so projects can adopt
the audit packet format without depending on a database or service.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
import hashlib
import json
import re


RiskClass = Literal["A", "B", "C"]
AuditStatus = Literal[
    "pending",
    "approved",
    "rejected",
    "needs_evidence",
    "needs_owner_action",
    "needs_verification",
    "defer",
]


AUDIT_ID_RE = re.compile(r"^audit-[a-z0-9][a-z0-9-]{4,96}$")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def stable_json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_rel_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        raise ValueError(f"changed file must be repository-relative: {value}")
    parts = path.parts
    if any(part in {"..", ""} for part in parts):
        raise ValueError(f"changed file must not contain traversal: {value}")
    return path.as_posix()


@dataclass(frozen=True)
class EvidenceRef:
    source_type: str
    reference: str
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReviewResult:
    status: AuditStatus
    reviewer: str
    reviewed_at: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditPacket:
    audit_id: str
    created_at: str
    owner: str
    requester: str
    risk_class: RiskClass
    title: str
    summary: str
    changed_files: list[str]
    proposed_action: str
    expected_impact: str
    rollback: str
    evidence: list[EvidenceRef] = field(default_factory=list)
    status: AuditStatus = "pending"
    review_result: ReviewResult | None = None
    followup_task: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        if not AUDIT_ID_RE.match(self.audit_id):
            raise ValueError(f"invalid audit_id: {self.audit_id}")
        if self.risk_class not in {"A", "B", "C"}:
            raise ValueError(f"invalid risk_class: {self.risk_class}")
        self.changed_files = [normalize_rel_path(item) for item in self.changed_files]
        if not self.owner:
            raise ValueError("owner is required")
        if not self.title:
            raise ValueError("title is required")

    @property
    def intent_hash(self) -> str:
        payload = {
            "audit_id": self.audit_id,
            "owner": self.owner,
            "requester": self.requester,
            "risk_class": self.risk_class,
            "title": self.title,
            "summary": self.summary,
            "changed_files": self.changed_files,
            "proposed_action": self.proposed_action,
            "expected_impact": self.expected_impact,
            "rollback": self.rollback,
        }
        return sha256_text(stable_json(payload))

    def to_dict(self) -> dict[str, Any]:
        data = {
            "audit_id": self.audit_id,
            "created_at": self.created_at,
            "owner": self.owner,
            "requester": self.requester,
            "risk_class": self.risk_class,
            "title": self.title,
            "summary": self.summary,
            "changed_files": self.changed_files,
            "proposed_action": self.proposed_action,
            "expected_impact": self.expected_impact,
            "rollback": self.rollback,
            "intent_hash": self.intent_hash,
            "evidence": [item.to_dict() for item in self.evidence],
            "status": self.status,
        }
        if self.review_result:
            data["review_result"] = self.review_result.to_dict()
        if self.followup_task:
            data["followup_task"] = self.followup_task
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditPacket":
        packet = cls(
            audit_id=str(data["audit_id"]),
            created_at=str(data.get("created_at") or now_iso()),
            owner=str(data["owner"]),
            requester=str(data.get("requester") or data["owner"]),
            risk_class=str(data["risk_class"]),  # type: ignore[arg-type]
            title=str(data["title"]),
            summary=str(data.get("summary") or ""),
            changed_files=[str(item) for item in data.get("changed_files", [])],
            proposed_action=str(data.get("proposed_action") or ""),
            expected_impact=str(data.get("expected_impact") or ""),
            rollback=str(data.get("rollback") or ""),
            evidence=[
                EvidenceRef(
                    source_type=str(item.get("source_type") or ""),
                    reference=str(item.get("reference") or ""),
                    summary=str(item.get("summary") or ""),
                )
                for item in data.get("evidence", [])
            ],
            status=str(data.get("status") or "pending"),  # type: ignore[arg-type]
            review_result=ReviewResult(
                status=str(data["review_result"]["status"]),  # type: ignore[arg-type]
                reviewer=str(data["review_result"]["reviewer"]),
                reviewed_at=str(data["review_result"]["reviewed_at"]),
                notes=str(data["review_result"].get("notes") or ""),
            )
            if data.get("review_result")
            else None,
            followup_task=data.get("followup_task"),
        )
        expected_hash = data.get("intent_hash")
        if expected_hash and expected_hash != packet.intent_hash:
            raise ValueError("audit packet intent_hash does not match packet content")
        return packet

