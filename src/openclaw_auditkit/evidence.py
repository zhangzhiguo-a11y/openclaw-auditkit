"""Evidence collection for audit packets."""

from __future__ import annotations

from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import sys

from .models import AuditPacket, EvidenceRef, now_iso
from .packet import write_packet


MAX_DIFF_LINES = 220
MAX_FILE_BYTES = 256_000


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_repo_path(repo: Path, rel_path: str) -> Path:
    root = repo.resolve()
    path = (root / rel_path).resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"path escapes repository root: {rel_path}")
    return path


def _git_show(repo: Path, revision: str, rel_path: str) -> str | None:
    proc = subprocess.run(
        ["git", "-C", str(repo), "show", f"{revision}:{rel_path}"],
        capture_output=True,
        text=True,
        timeout=15,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _read_current(path: Path) -> str | None:
    if not path.exists() or not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
        return None
    return path.read_text(encoding="utf-8", errors="replace")


def _bounded_diff(before: str | None, after: str | None, rel_path: str) -> str:
    before_lines = [] if before is None else before.splitlines()
    after_lines = [] if after is None else after.splitlines()
    lines = list(
        difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"base/{rel_path}",
            tofile=f"worktree/{rel_path}",
            lineterm="",
            n=3,
        )
    )
    if len(lines) > MAX_DIFF_LINES:
        return "\n".join(lines[:MAX_DIFF_LINES]) + f"\n# diff_truncated=true shown_lines={MAX_DIFF_LINES} total_lines={len(lines)}\n"
    return "\n".join(lines) + ("\n" if lines else "# no textual diff available\n")


def collect_evidence(packet: AuditPacket, *, repo: Path, output_dir: Path, base_ref: str = "HEAD") -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, object] = {
        "evidence_type": "auditkit_evidence_manifest",
        "generated_at": now_iso(),
        "audit_id": packet.audit_id,
        "base_ref": base_ref,
        "files": [],
    }
    diff_sections = [f"# AuditKit implementation diff for {packet.audit_id}", f"# generated_at={now_iso()}", ""]
    file_facts = []

    for rel_path in packet.changed_files:
        current_path = _safe_repo_path(repo, rel_path)
        before = _git_show(repo, base_ref, rel_path)
        after = _read_current(current_path)
        diff_sections.extend([f"## {rel_path}", _bounded_diff(before, after, rel_path), ""])
        fact = {
            "path": rel_path,
            "exists": current_path.exists(),
            "bytes": current_path.stat().st_size if current_path.exists() and current_path.is_file() else None,
            "sha256": sha256_file(current_path) if current_path.exists() and current_path.is_file() else None,
        }
        file_facts.append(fact)

    diff_path = output_dir / "implementation.diff"
    diff_path.write_text("\n".join(diff_sections).rstrip() + "\n", encoding="utf-8")

    facts_path = output_dir / "file-facts.json"
    facts_path.write_text(json.dumps(file_facts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    validation = {
        "generated_at": now_iso(),
        "checks": [
            {"name": "packet_has_owner", "ok": bool(packet.owner)},
            {"name": "packet_has_changed_files", "ok": bool(packet.changed_files)},
            {"name": "risk_class_valid", "ok": packet.risk_class in {"A", "B", "C"}},
            {"name": "intent_hash_present", "ok": bool(packet.intent_hash)},
        ],
    }
    validation_path = output_dir / "validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for path in (diff_path, facts_path, validation_path):
        raw = path.read_bytes()
        manifest["files"].append(
            {
                "path": str(path.relative_to(output_dir)),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )

    manifest_path = output_dir / "evidence-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    existing = {(item.source_type, item.reference) for item in packet.evidence}
    for source_type, path, summary in (
        ("diff", diff_path, "Bounded unified diff for changed files."),
        ("file_facts", facts_path, "File existence, size, and hash facts."),
        ("validation", validation_path, "Deterministic packet validation checks."),
        ("manifest", manifest_path, "Evidence manifest with hashes."),
    ):
        rel = str(path)
        if (source_type, rel) not in existing:
            packet.evidence.append(EvidenceRef(source_type=source_type, reference=rel, summary=summary))
    write_packet(packet, output_dir.parent / "audit-packet.json")
    return {
        "diff": str(diff_path),
        "file_facts": str(facts_path),
        "validation": str(validation_path),
        "manifest": str(manifest_path),
    }

