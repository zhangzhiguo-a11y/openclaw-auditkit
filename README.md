# OpenClaw AuditKit

OpenClaw AuditKit is a small CLI and JSON packet format for owner-routed review
loops in self-evolving tools, agent workflows, and CI automation.

The core idea is simple: when an automated audit says `needs_evidence`,
`needs_verification`, `defer`, or `rejected`, the feedback goes back to the
party that proposed the change. Human or maintainer confirmation is reserved for
approved B-class closeout, not for inventing missing evidence.

No API key is required. The default reviewer is deterministic and conservative.

## Why This Exists

Self-evolving systems often fail in the same way:

- A tool proposes a patch.
- A reviewer asks for more evidence.
- The process stalls because no one is clearly responsible.
- A human confirmation path becomes a catch-all for missing technical proof.

AuditKit turns that into a structured loop:

```text
change -> classify -> audit packet -> evidence -> review
       -> owner follow-up when unresolved -> re-review
       -> approved closeout or rejected/quarantined
```

## Risk Classes

| Class | Meaning | Default behavior |
| --- | --- | --- |
| A | Low-risk files | Audit required, can auto-approve when evidence and rollback exist |
| B | Source, scripts, workflows, schemas, deploy files | Audit required, owner verification and closeout receipt required |
| C | Secrets, credentials, OAuth, customer files, production data | Rejected or quarantined by default |

## Install

```bash
python -m pip install openclaw-auditkit
```

For local development:

```bash
git clone <repository-url>
cd openclaw-auditkit
python -m pip install -e .
```

## CLI Quick Start

Create a packet:

```bash
auditkit create \
  --title "Improve retry handling" \
  --owner "workflow-maintainer" \
  --changed-file "src/retry.py" \
  --summary "Retry failures should route to the original owner." \
  --proposed-action "Add owner-routed follow-up task generation." \
  --rollback "Revert the retry handling patch." \
  --output ".auditkit/audit-packet.json"
```

Collect evidence:

```bash
auditkit evidence \
  --packet ".auditkit/audit-packet.json" \
  --repo "." \
  --output-dir ".auditkit/evidence"
```

Run the deterministic local reviewer:

```bash
auditkit review --packet ".auditkit/audit-packet.json"
```

If the packet is unresolved, route it to the owner:

```bash
auditkit followup \
  --packet ".auditkit/audit-packet.json" \
  --output-dir ".auditkit/evidence"
```

For a reviewed B-class packet, write a closeout receipt:

```bash
auditkit closeout \
  --packet ".auditkit/audit-packet.json" \
  --output-dir ".auditkit/evidence" \
  --verified-by "maintainer"
```

## Packet Format

Audit packets are plain JSON. A minimal packet contains:

- `owner`: the party responsible for evidence and repair.
- `risk_class`: `A`, `B`, or `C`.
- `changed_files`: repository-relative paths.
- `evidence`: references to diffs, file facts, validation output, and manifests.
- `status`: current audit status.
- `followup_task`: optional owner-routed task for unresolved feedback.

See [`schemas/audit_packet.schema.json`](schemas/audit_packet.schema.json).

## GitHub Actions

This repository includes a starter workflow at
[`.github/workflows/auditkit.yml`](.github/workflows/auditkit.yml).

It classifies pull request changes and fails C-class changes by default.

## Security And Privacy

AuditKit is designed for public repositories:

- Changed files must be repository-relative.
- Absolute local paths are rejected for packet changed files.
- C-class patterns reject secret, token, credential, OAuth, customer-file, and
  production-data paths by default.
- The tool does not read environment variables, API keys, OAuth tokens, browser
  sessions, or private account files.
- The default reviewer runs locally and does not call external APIs.

Before publishing packets publicly, still review generated evidence. A diff can
only be as safe as the content committed to your repository.

## Status

AuditKit is an early alpha. The public surface is intentionally small:

- `auditkit classify`
- `auditkit create`
- `auditkit evidence`
- `auditkit review`
- `auditkit followup`
- `auditkit closeout`

Planned additions:

- Configurable policy file.
- SARIF output.
- Optional model-based reviewer plugin interface.
- Configurable closeout receipt policy.
