"""Command line interface for OpenClaw AuditKit."""

from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from .closeout import closeout_packet
from .evidence import collect_evidence
from .followup import write_owner_followup
from .models import AuditPacket
from .packet import create_packet, read_packet, write_packet
from .policy import classify_paths
from .reviewer import review_packet


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_classify(args: argparse.Namespace) -> int:
    result = classify_paths(args.changed_file)
    print_json(result.to_dict())
    return 0 if result.risk_class != "C" or args.allow_c else 2


def cmd_create(args: argparse.Namespace) -> int:
    packet = create_packet(
        title=args.title,
        owner=args.owner,
        requester=args.requester,
        changed_files=args.changed_file,
        summary=args.summary or "",
        proposed_action=args.proposed_action or "",
        expected_impact=args.expected_impact or "",
        rollback=args.rollback or "",
    )
    write_packet(packet, Path(args.output))
    print_json({"ok": True, "audit_id": packet.audit_id, "risk_class": packet.risk_class, "output": args.output})
    return 0


def cmd_evidence(args: argparse.Namespace) -> int:
    packet_path = Path(args.packet)
    packet = read_packet(packet_path)
    output_dir = Path(args.output_dir)
    result = collect_evidence(packet, repo=Path(args.repo), output_dir=output_dir, base_ref=args.base_ref)
    write_packet(packet, packet_path)
    print_json({"ok": True, "audit_id": packet.audit_id, "evidence": result})
    return 0


def cmd_review(args: argparse.Namespace) -> int:
    packet_path = Path(args.packet)
    packet = read_packet(packet_path)
    result = review_packet(packet)
    packet.status = result.status
    packet.review_result = result
    write_packet(packet, packet_path)
    print_json({"ok": True, "audit_id": packet.audit_id, "status": result.status, "notes": result.notes})
    return 0 if result.status == "approved" else 1


def cmd_followup(args: argparse.Namespace) -> int:
    packet_path = Path(args.packet)
    packet = read_packet(packet_path)
    path = write_owner_followup(packet, Path(args.output_dir))
    write_packet(packet, packet_path)
    print_json({"ok": True, "audit_id": packet.audit_id, "owner": packet.owner, "task": str(path)})
    return 0


def cmd_closeout(args: argparse.Namespace) -> int:
    packet_path = Path(args.packet)
    packet = read_packet(packet_path)
    path = closeout_packet(packet, output_dir=Path(args.output_dir), verified_by=args.verified_by, notes=args.notes or "")
    write_packet(packet, packet_path)
    print_json({"ok": True, "audit_id": packet.audit_id, "status": packet.status, "receipt": str(path)})
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="auditkit", description="Owner-routed three-tier audit packets.")
    sub = parser.add_subparsers(dest="command", required=True)

    classify = sub.add_parser("classify", help="Classify repository-relative changed files.")
    classify.add_argument("--changed-file", action="append", required=True)
    classify.add_argument("--allow-c", action="store_true", help="Return exit 0 for C-class results.")
    classify.set_defaults(func=cmd_classify)

    create = sub.add_parser("create", help="Create an audit packet.")
    create.add_argument("--title", required=True)
    create.add_argument("--owner", required=True)
    create.add_argument("--requester")
    create.add_argument("--changed-file", action="append", required=True)
    create.add_argument("--summary")
    create.add_argument("--proposed-action")
    create.add_argument("--expected-impact")
    create.add_argument("--rollback")
    create.add_argument("--output", default=".auditkit/audit-packet.json")
    create.set_defaults(func=cmd_create)

    evidence = sub.add_parser("evidence", help="Collect local evidence for a packet.")
    evidence.add_argument("--packet", default=".auditkit/audit-packet.json")
    evidence.add_argument("--repo", default=".")
    evidence.add_argument("--output-dir", default=".auditkit/evidence")
    evidence.add_argument("--base-ref", default="HEAD")
    evidence.set_defaults(func=cmd_evidence)

    review = sub.add_parser("review", help="Run deterministic local review.")
    review.add_argument("--packet", default=".auditkit/audit-packet.json")
    review.set_defaults(func=cmd_review)

    followup = sub.add_parser("followup", help="Write owner-routed follow-up task.")
    followup.add_argument("--packet", default=".auditkit/audit-packet.json")
    followup.add_argument("--output-dir", default=".auditkit/evidence")
    followup.set_defaults(func=cmd_followup)

    closeout = sub.add_parser("closeout", help="Write a closeout receipt and approve a non-C packet.")
    closeout.add_argument("--packet", default=".auditkit/audit-packet.json")
    closeout.add_argument("--output-dir", default=".auditkit/evidence")
    closeout.add_argument("--verified-by", required=True)
    closeout.add_argument("--notes")
    closeout.set_defaults(func=cmd_closeout)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
