# Automation Loop Pattern

AuditKit is intentionally small: it creates packets, collects evidence, reviews
changes, routes unresolved feedback to the owner, and records closeout receipts.
Projects can wrap those commands in their own scheduled automation.

The key rule for scheduled use is:

> Reviewer cooldown must not stop non-review progress.

If an external reviewer, model, or audit service is rate-limited or temporarily
unavailable, pause only that reviewer call. Continue work that is deterministic
and local.

## Recommended Loop

```text
discover signals
  -> create candidate changes only when evidence exists
  -> classify
  -> create audit packet
  -> collect local evidence
  -> review when reviewer is available
  -> if unresolved, write owner follow-up
  -> later collect more evidence and re-review
  -> close out only after approval and required receipt
```

## Continue During Reviewer Cooldown

These steps are safe to keep running while reviewer calls are cooling down:

- Discovering new evidence-backed signals.
- Collecting local evidence for existing packets.
- Writing owner follow-up tasks for unresolved packets.
- Reporting queue status and stale work.
- Checking whether approved packets have the required closeout receipt.

These steps should pause during reviewer cooldown:

- Calling an external model-based reviewer.
- Burning another request on a packet that already has a bounded retry time.

## Candidate Quality Gate

Automation should not create candidates just to keep daily counts nonzero.
Every generated candidate should include:

- A real signal, such as a failing check, stale unresolved packet, repeated
  manual repair, or missing expected run artifact.
- Expected improvement.
- Evidence reference.
- Validation plan.
- Rollback plan.
- Risk class.
- Owner.

If no real signal exists, record a no-candidate reason instead of fabricating a
proposal.

## Avoiding Regressions

Treat automation as a proposal system until audit passes:

- Class C never merges.
- Class B waits for audit plus the configured confirmation or receipt policy.
- Class A can auto-merge only inside the project's explicitly allowed scope.
- Every merge path needs rollback instructions.
- Status reports should include generated, skipped, rejected, and stale counts.

This keeps self-evolving workflows moving without turning rate limits or missing
evidence into silent queue blockage.
