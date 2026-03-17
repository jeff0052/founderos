# CDRE Methodology — AI Execution Spec

_Contract-Driven Rapid Evolution_

**Audience: AI agents operating within FounderOS**
**Purpose: Defines how you build, validate, and evolve software in this system.**

---

## Core Principle

> Code is disposable. Contracts are the asset.
> If you're unsure, check the contract. If there's no contract, ask the human to create one.

---

## Architecture (4 Layers)

You operate within a strict layer hierarchy. Never violate layer boundaries.

```
Layer 1: CONTRACT    (human-owned, rarely changes)
Layer 2: SPEC        (human-owned, changes per quarter)
Layer 3: IMPL        (AI-owned, disposable, changes constantly)
Layer 4: VERIFY      (automated + human review)
```

### Layer 1: Contract — DO NOT MODIFY without ADR

Contains:
- `contracts/` — ADR files, interface types, DB schemas, boundary diagrams
- These are the system's constitution

Rules:
- NEVER change a contract without explicit human approval
- ALWAYS check contracts before implementing anything
- If implementation contradicts a contract → implementation is wrong

### Layer 2: Spec — Your work instructions

Contains:
- Module specs (one page max per module)
- Test specs (executable acceptance criteria)
- Prompt templates (`prompts/`)

Rules:
- Read the full spec before starting any implementation
- If spec has an "Excludes" section → DO NOT build those things
- If you keep failing on a task → tell the human to tighten the spec

### Layer 3: Implementation — Your output

Rules:
- DO NOT patch. Regenerate from spec if output is wrong.
- ALWAYS inject full context (contracts + spec) before generating
- DO NOT add features not in the spec (you will over-engineer; resist it)
- DO NOT get attached to generated code. It is disposable.
- Treat implementation as SEARCH, not construction — sample candidates, converge via tests

### Layer 4: Verification — Quality gate

Execution order (mandatory):
1. Type check → does impl match contract types?
2. Lint → style consistency
3. Unit tests → function-level behavior
4. Integration tests → module interactions
5. E2E tests → business flow end-to-end
6. Contract consistency → interfaces match contracts exactly

Your review focus:
- Architecture compliance (follows ADRs? modules stay in bounds?)
- Over-engineering detection (features outside spec?)
- Security review

NOT your concern: formatting (lint handles it), type safety (compiler handles it)

---

## Workflow (5 Phases)

When given a task, follow this sequence:

```
Phase 0: UNDERSTAND  → What and why? Clarify with human if unclear.
Phase 1: CONTRACT    → Check/create ADRs, interface types, schemas.
Phase 2: SPEC        → Write module spec, test spec, prompt template.
Phase 3: IMPLEMENT   → Generate code. Don't like it? Regenerate. Don't patch.
Phase 4: VERIFY      → Run automated pipeline. Human reviews architecture.
Phase 5: FEEDBACK    → Update specs based on what went wrong.
```

### Time allocation guide

| Phase | % of effort | Owner |
|-------|-------------|-------|
| Contract design | 40% | Human |
| Spec writing | 30% | Human |
| Implementation | 10% | AI |
| Verification | 20% | Automated + Human |

70% of effort is "documentation." This is correct. Do not skip it.

---

## Feedback Loop

When you observe problems, take these actions:

| Problem | Action |
|---------|--------|
| You keep generating features outside spec | Add to spec's "Excludes" section |
| You misunderstand an interface | Ask human to tighten type definitions |
| Tests pass but bugs leak | Add boundary test cases |
| Requirements changed | Flag: may need new ADR |
| Prompt gives inconsistent results | Iterate prompt template, version it |

---

## FounderOS Mapping

This methodology maps directly to FounderOS layers:

| CDRE Layer | FounderOS Equivalent |
|------------|---------------------|
| Contract | Vision + Objectives (rarely change) |
| Spec | Key Results (quarterly) |
| Implementation | Missions / Tasks (daily, AI executes) |
| Verification | KR achievement checks (automated + Jeff review) |

---

## Rules for AI Agents (Summary)

1. **Contract first.** Always read contracts before implementing.
2. **Spec is your boundary.** Don't go outside it.
3. **Regenerate, don't patch.** Bad output → full regeneration with better context.
4. **No gold-plating.** Build exactly what's specified. Nothing more.
5. **Excludes are sacred.** If spec says "don't build X," don't build X.
6. **Flag uncertainty.** If spec is ambiguous, ask. Don't guess.
7. **Tests before code.** Tests define correctness. Code is just a candidate.
8. **Context is everything.** Inject full context every time. You have no memory.
9. **Document changes.** If you discover something, update the feedback loop.
10. **Contracts are above you.** You cannot override them. Only humans can.
