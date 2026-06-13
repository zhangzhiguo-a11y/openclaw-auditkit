# Simple Change Example

This example shows the intended flow for a repository change:

```bash
auditkit create \
  --title "Improve retry handling" \
  --owner "workflow-maintainer" \
  --changed-file "src/retry.py" \
  --summary "Retry failures should route to the original owner." \
  --proposed-action "Add owner-routed follow-up task generation." \
  --rollback "Revert the retry handling patch." \
  --output ".auditkit/audit-packet.json"

auditkit evidence --packet .auditkit/audit-packet.json --repo . --output-dir .auditkit/evidence
auditkit review --packet .auditkit/audit-packet.json
auditkit followup --packet .auditkit/audit-packet.json --output-dir .auditkit/evidence
```

No API key is required. The default reviewer is deterministic and conservative.

