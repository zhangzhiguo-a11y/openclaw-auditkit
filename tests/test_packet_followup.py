from pathlib import Path

from openclaw_auditkit.closeout import closeout_packet
from openclaw_auditkit.followup import build_owner_followup
from openclaw_auditkit.packet import create_packet, read_packet, write_packet
from openclaw_auditkit.reviewer import review_packet


def test_packet_preserves_changed_files_as_evidence(tmp_path: Path):
    packet = create_packet(
        title="Update workflow",
        owner="maintainer",
        requester=None,
        changed_files=["src/workflow.py"],
        rollback="Revert the workflow patch.",
    )
    assert packet.risk_class == "B"
    assert packet.evidence[0].source_type == "changed_file"
    assert packet.evidence[0].reference == "src/workflow.py"

    path = tmp_path / "audit-packet.json"
    write_packet(packet, path)
    loaded = read_packet(path)
    assert loaded.intent_hash == packet.intent_hash


def test_unresolved_feedback_routes_to_owner():
    packet = create_packet(
        title="Update workflow",
        owner="agent-a",
        requester="agent-b",
        changed_files=["src/workflow.py"],
        rollback="Revert the workflow patch.",
    )
    result = review_packet(packet)
    packet.status = result.status
    packet.review_result = result

    followup = build_owner_followup(packet)
    assert followup["responsible_party"] == "agent-a"
    assert followup["required_owner_action"] == "owner_run_verification"


def test_closeout_writes_receipt(tmp_path: Path):
    packet = create_packet(
        title="Docs update",
        owner="maintainer",
        requester=None,
        changed_files=["docs/guide.md"],
        rollback="Revert the docs patch.",
    )
    receipt = closeout_packet(packet, output_dir=tmp_path / "evidence", verified_by="maintainer")
    assert receipt.exists()
    assert packet.status == "approved"
