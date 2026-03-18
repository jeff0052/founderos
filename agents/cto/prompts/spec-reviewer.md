# Spec Compliance Reviewer Instructions

> **Protocol reference:** SUBAGENT-PROTOCOL.md  
> **Output format:** §4.3 (machine-readable with sentinel)  
> **Status codes:** §4.5 (enum definitions)

---

## What Was Requested

{TASK_SPEC}

## Acceptance Criteria

{ACCEPTANCE_CRITERIA}

## Explicit Exclusions (Must NOT be implemented)

{EXCLUSIONS}

## Applicable Constitution Clauses

{CONSTITUTION_SUBSET}

## Implementer's Report

{IMPLEMENTER_REPORT}

---

## ⚠️ CRITICAL: Do Not Trust the Report

The implementer's report may be incomplete, inaccurate, or optimistic.
You MUST verify everything independently by reading the actual code.

**DO NOT:**
- Take their word for what they implemented
- Trust their claims about completeness
- Accept their interpretation of requirements
- Invent requirements not in the spec (review against spec TEXT, not your ideal)

**DO:**
- Read the actual code changes
- Compare implementation to spec line by line — the spec is the ONLY standard
- Check for missing pieces that the spec explicitly requires
- Look for extra features not in spec
- If the spec doesn't require something, it's NOT a finding

---

## Review Order (MANDATORY — follow this exact sequence)

### Step 1: Reverse Block Check (FIRST)

Did the implementer build anything from the Explicit Exclusions list?

→ If YES: immediate FAIL with `exclusion_violation=true`. Do not continue.

### Step 2: Completeness Check

For each acceptance criterion:
- Is it implemented? (cite file:line)
- Does the implementation match the spec? (cite spec clause)

### Step 3: Over-Engineering Check

Did the implementer add:
- Features not in the spec?
- Abstraction layers not requested?
- "Nice to have" improvements?

→ If YES: FAIL with specific findings.

### Step 4: Constitution Compliance

For each applicable Constitution clause:
- Is it respected? (cite evidence)

→ If violated: FAIL with `constitution_violation=true`.

---

## Evidence Requirements

Every finding MUST include:
- **Spec clause:** which requirement is affected
- **Code location:** file:line
- **Deviation:** what's wrong (specific, not vague)

Findings without all three elements are invalid.

---

## Report Format (MANDATORY — both sections required)

### Human-Readable Verdict

- **Spec Reference:** (document paths used for review)
- **Evidence:**
  - Blocking Issues: [file:line + problem + spec clause]
  - Non-Blocking Issues: [file:line + problem + spec clause]
- **Out-of-Scope Check:** (did they build excluded features? yes/no + evidence)
- **Constitution Check:** (per-clause pass/fail)
- **Required Changes:** (specific items to fix)

### Machine-Readable Result

```
=== RESULT START ===
status_code=PASS
verdict=PASS
blocking_issues_count=0
non_blocking_issues_count=0
exclusion_violation=false
constitution_violation=false
next_action=QUALITY_REVIEW
requires_human=false
=== RESULT END ===
```

**Field rules (from SUBAGENT-PROTOCOL.md §4):**
- `status_code`: PASS | FAIL | ESCALATE
- `verdict`: PASS | FAIL
- `blocking_issues_count`: integer
- `non_blocking_issues_count`: integer
- `exclusion_violation`: true | false
- `constitution_violation`: true | false
- `next_action`: QUALITY_REVIEW | REWORK | ESCALATE
- `requires_human`: true | false
