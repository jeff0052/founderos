# Code Quality Reviewer Instructions

> **Protocol reference:** SUBAGENT-PROTOCOL.md  
> **Output format:** §4.4 (machine-readable with sentinel)  
> **Severity definitions:** CODE-REVIEW-STANDARD.md (single source of truth)  
> **Status codes:** SUBAGENT-PROTOCOL.md §4.5 (enum definitions)

---

## Prerequisite

This review ONLY happens after spec compliance review has PASSED.
If spec review has not passed, do NOT proceed — report ESCALATE.

## What Was Implemented

{TASK_DESCRIPTION}

## Code Changes

Base SHA: {BASE_SHA}
Head SHA: {HEAD_SHA}

Review the git diff between these commits.

## Applicable Constitution Clauses

{CONSTITUTION_SUBSET}

---

## Review Dimensions

Review in this order. For each finding, assign severity P0-P3.

### 1. Safety Boundaries

- [ ] Float arithmetic for money? (Constitution §13 — P0)
- [ ] Hardcoded secrets/keys? (Constitution §11 — P0)
- [ ] Silent exception swallowing on critical paths? (P0)
- [ ] Direct production environment access? (Constitution §12 — P0)
- [ ] Payment-specific: idempotency? state machine integrity? reconciliation?

### 2. Code Quality

- [ ] Single responsibility per module?
- [ ] Circular dependencies?
- [ ] Import style consistency?
- [ ] Error handling (no bare except, no swallowed errors)?
- [ ] Comments: module header (what/not-what/interactions), key functions (why not what)

### 3. Architecture Health

- [ ] Within Complexity Budget?
- [ ] New modules have Module Spec?
- [ ] CLAUDE.md / ARCHITECTURE.md updated?
- [ ] Irreversible coupling introduced?

### 4. Test Quality

- [ ] Invariant test files modified? (Constitution §5 — P0)
- [ ] Over-mocking? (mock everything + assert call_count = waste test)
- [ ] Boundary conditions tested? (extremes, negatives, concurrency, timeouts)
- [ ] Error paths tested?
- [ ] Tests independently runnable? (no execution order dependency)

---

## Severity Classification (reference: CODE-REVIEW-STANDARD.md)

| Level | Meaning | Action |
|-------|---------|--------|
| **P0** | Cannot ship | Float money, state machine error, hardcoded secret, invariant test tampered, excluded feature built |
| **P1** | Must fix before merge | Module boundary violation, circular dep, missing critical path, idempotency gap, doc not synced |
| **P2** | Can merge, log to FPMS | Module too large, heavy abstraction, insufficient comments, weak boundary tests |
| **P3** | Optional | Naming improvements, local structure optimization |

## Verdict Rules

- Any P0 → **Reject**
- Any P1 → **Reject** (fix then re-review)
- Only P2/P3 → **Approve with debt** (P2 items → FPMS backlog)
- Clean → **Approve**

---

## Evidence Requirements

Every finding MUST include:
- **Severity:** P0 / P1 / P2 / P3
- **Category:** Safety / Quality / Architecture / Tests
- **Location:** file:line
- **Problem:** (one sentence)
- **Fix suggestion:** (specific)

Findings without all five elements are invalid.

---

## Report Format (MANDATORY — both sections required)

### Human-Readable Verdict

- **Findings:** [per finding: severity + category + file:line + problem + fix suggestion]
- **Constitution Compliance:** [per-clause check result]
- **Complexity Assessment:** module count / max file LOC / dependency depth
- **FPMS Debt Items:** [P2 items to log in backlog]
- **Required Changes:** [P0/P1 items that must be fixed]

### Machine-Readable Result

```
=== RESULT START ===
status_code=APPROVE
verdict=Approve
highest_severity=CLEAN
p0_count=0
p1_count=0
p2_count=0
p3_count=0
constitution_violation=false
next_action=DONE
requires_human=false
fpms_debt_items=[]
=== RESULT END ===
```

**Field rules (from SUBAGENT-PROTOCOL.md §4):**
- `status_code`: APPROVE | REJECT | ESCALATE
- `verdict`: Approve | Approve_with_debt | Reject
- `highest_severity`: P0 | P1 | P2 | P3 | CLEAN
- `p0_count` through `p3_count`: integer
- `constitution_violation`: true | false
- `next_action`: DONE | REWORK | ESCALATE
- `requires_human`: true | false
- `fpms_debt_items`: JSON array of strings (empty if none)
