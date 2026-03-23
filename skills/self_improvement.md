# Self-Improvement

Log corrections, errors, and useful discoveries to `.learnings/` so they persist across sessions and can be reviewed before major work.

## When to log

| Situation | File |
|-----------|------|
| User corrects you ("No, actually...", "That's wrong...") | `.learnings/LEARNINGS.md` |
| You realise your knowledge was outdated or wrong | `.learnings/LEARNINGS.md` |
| You find a better approach to something recurring | `.learnings/LEARNINGS.md` |
| A command or operation fails unexpectedly | `.learnings/ERRORS.md` |
| User requests a capability that doesn't exist | `.learnings/FEATURE_REQUESTS.md` |

## Log format

### Learning entry (append to `.learnings/LEARNINGS.md`)

```
## [LRN-YYYYMMDD-NNN] category

**Logged**: timestamp
**Priority**: low | medium | high
**Category**: correction | knowledge_gap | best_practice

### Summary
One line.

### Details
What happened, what was wrong, what is correct.

### Suggested Action
Specific next step, or "none".
```

### Error entry (append to `.learnings/ERRORS.md`)

```
## [ERR-YYYYMMDD-NNN] description

**Logged**: timestamp
**Priority**: high
**Reproducible**: yes | no | unknown

### Summary
One line.

### Error
Exact error message or output.

### Context
What was attempted, with what inputs.

### Suggested Fix
If identifiable.
```

### Feature request entry (append to `.learnings/FEATURE_REQUESTS.md`)

```
## [FEAT-YYYYMMDD-NNN] capability_name

**Logged**: timestamp
**Priority**: low | medium | high

### Requested Capability
What the user wanted.

### User Context
Why they needed it.
```

## ID format

`TYPE-YYYYMMDD-NNN` — e.g. `LRN-20260323-001`, `ERR-20260323-A3F`

## Before starting a major task

Check `.learnings/` for relevant past entries:

[READ_FILE: .learnings/LEARNINGS.md]
[READ_FILE: .learnings/ERRORS.md]

Apply any applicable learnings before proceeding.

## Resolving entries

When an issue is fixed, update the entry's status:

- Change `pending` → `resolved` and add a brief resolution note
- Change `pending` → `promoted` if the learning was added to `RULES.MD`

## Promoting to RULES.MD

If a learning is broadly applicable (not a one-off), propose promoting it to `RULES.MD` as a short rule. Always ask the user to confirm before writing:

> "This learning seems broadly applicable — shall I add it to RULES.MD?"

Never modify `RULES.MD`, `IDENTITY.MD`, or `ROLE.MD` without explicit user confirmation.

## Initialising the log files

If `.learnings/` does not exist, create it when first needed:

[MODIFY_FILE: .learnings/LEARNINGS.md]
# Learnings

Corrections, knowledge gaps, and best practices discovered in use.

---
[/MODIFY_FILE]

[MODIFY_FILE: .learnings/ERRORS.md]
# Errors

Unexpected failures and their context.

---
[/MODIFY_FILE]

[MODIFY_FILE: .learnings/FEATURE_REQUESTS.md]
# Feature Requests

Capabilities the user has asked for that don't yet exist.

---
[/MODIFY_FILE]
