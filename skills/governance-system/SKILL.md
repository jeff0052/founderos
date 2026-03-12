---
name: governance-system
description: "Manage three-department governance workflow"
metadata: {"openclaw":{}}
---

# Three-Department Governance System

Manage the three-department governance workflow: PROPOSER → AUDITOR → EXECUTOR.

## When to Use

- User requests system changes (configuration, features, processes)
- Need to implement governance for decision-making
- Requires structured approval workflow for sensitive changes

## Workflow

### Department Roles

1. **PROPOSER** - Analyzes requirements, proposes solutions
2. **AUDITOR** - Reviews proposals, assesses risks, approves/rejects  
3. **EXECUTOR** - Implements approved proposals strictly

### Process Flow

```
User Request → PROPOSER → Proposal → AUDITOR → Approval/Rejection → EXECUTOR → Implementation
```

### Step 1: Generate Proposal
- Spawn PROPOSER subagent
- PROPOSER creates detailed proposal in `memory/decisions/proposals/`
- Assigns proposal ID: `D-YYYY-MM-DD-NNN`

### Step 2: Review & Audit
- Spawn AUDITOR subagent
- AUDITOR reviews proposal against safety/security criteria
- Writes audit result in `memory/decisions/audits/`
- Decision: ✅ 通过 | ⚠️ 有条件通过 | ❌ 拒绝

### Step 3: Execute (if approved)
- Spawn EXECUTOR subagent
- EXECUTOR follows approved proposal exactly
- Records execution log in `memory/decisions/executions/`
- Reports completion status

## Templates

Use templates in `templates/` directory:
- `proposal-template.md` - Standard proposal format
- `audit-template.md` - Standard audit checklist
- `execution-template.md` - Execution log format

## Safety Rules

- All system changes must go through three-department process
- No direct execution without audit approval
- EXECUTOR never deviates from approved proposals
- Each department operates independently

## Directory Structure

```
memory/decisions/
  ├── proposals/D-YYYY-MM-DD-NNN-proposal.md
  ├── audits/D-YYYY-MM-DD-NNN-audit.md
  └── executions/D-YYYY-MM-DD-NNN-execution.md
```