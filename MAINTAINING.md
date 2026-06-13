# Maintaining OpenClaw AuditKit

This file is the repo-local maintenance memory for the published AuditKit
package. Keep it public-safe: do not add private machine paths, account names,
customer details, API keys, OAuth details, or internal OpenClaw deployment
paths.

## Repository Role

`openclaw-auditkit` is the public package for reusable audit packets, local
evidence collection, deterministic review, owner follow-up, and closeout
receipts.

It is not the default home for internal OpenClaw production runtime scripts.
Only port an internal repair here when it becomes a reusable, public-safe
AuditKit feature or documented pattern.

## Maintenance Flow

1. Update this local repository first.
2. Keep changes small and package-scoped.
3. Run validation before publishing:

```bash
python -m compileall src tests
python -m pytest
python -m pip install -e .
auditkit --help
```

4. Update version and release notes when behavior changes.
5. Commit locally.
6. Push to GitHub.
7. Verify the public repository page and install path after push.

## Release Checklist

- README still describes the CLI accurately.
- `pyproject.toml` version is bumped for a real release.
- Tests pass locally.
- No `.bak`, local path, credential, token, OAuth, customer, or internal
  operations file is tracked.
- Examples use repository-relative paths only.
- Public docs explain behavior without depending on private OpenClaw services.

## Current Backlog

- Configurable policy file.
- SARIF output.
- Optional model-based reviewer plugin interface.
- Configurable closeout receipt policy.
- Automation-loop guidance or helper primitives for systems that run AuditKit
  on a schedule.

## 2026-06-13 Maintenance Note

An internal OpenClaw repair showed a reusable design rule:

When an external reviewer, model, or audit service is rate-limited, automation
should cool down only that reviewer call. It should still run non-review work
such as evidence collection, owner follow-up task generation, status reporting,
and safe closeout checks.

Do not copy internal scheduler code into this package. The public AuditKit
version of this lesson should be a generic automation-loop pattern, example, or
small helper that keeps reviewer cooldown separate from non-review progress.

Current repository action:
- Commit only this maintenance guide and `.gitignore` backup-file ignores.
- Do not bump the package version for this maintenance-only change.
- Do not change `src/openclaw_auditkit/` until a public-safe automation-loop
  feature or document is designed.

Next version TODO:
- Add public-safe automation-loop documentation or helper code showing how to
  keep reviewer cooldown separate from evidence collection, owner follow-up,
  status reporting, and closeout checks.
