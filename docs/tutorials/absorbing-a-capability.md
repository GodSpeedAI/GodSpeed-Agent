# Tutorial: Absorbing an External Capability

This tutorial guides you through safely evaluating, staging, and absorbing an external module into a receiving project using GodSpeed-Agent's absorbability engine and git worktrees.

---

## 1. Prerequisites

- A functioning GodSpeed-Agent installation.
- A local git repository representing your target application project.
- A candidate external tool or module to absorb (e.g. an external PDF extraction script).

---

## 2. Step 1: Stage the Candidate in Ingest Root

GodSpeed-Agent expects external candidates to be staged under the project's ingest root:
`ingest/absorption/<candidate-name>/`

```bash
mkdir -p ingest/absorption/pdf-extractor
```

Create two staging files inside that directory:

### `ingest/absorption/pdf-extractor/license-summary.json`
```json
{
  "license": "MIT",
  "compatible": true,
  "notes": "Verified permissive license compatible with project."
}
```

### `ingest/absorption/pdf-extractor/candidate-notes.md`
```markdown
# Candidate: PDF Extractor
Provides robust text and table extraction from PDF files using pdfplumber.
Requires Python >=3.10 and pdfplumber >=0.10.
```

---

## 3. Step 2: Audit Absorbability via CLI

Run the absorbability command to evaluate whether the candidate is currently spendable:

```bash
uv run godspeed-nav absorbability \
  --workspace-root . \
  --root-state '{"pdf_support": false}' \
  --external-state '{"pdf_support": true}' \
  --desired '{"statement": "Extract text from uploaded invoice PDFs"}' \
  --capability-delta '["pdf_parsing", "table_extraction"]' \
  --license '{"compatible": true}' \
  --pathway "wrap pdfplumber in internal app/services/pdf.py adapter"
```

**Expected Output**:
```json
{
  "absorbability_status": "absorbable",
  "blocking_reasons": [],
  "missing_pathway": false,
  "payment_estimate": {
    "dominant_cost": "integration",
    "payment_burden": 4
  },
  "policy_gate": {
    "code": "human_review_required",
    "decision": "requires_review",
    "reason": "Absorption requires human review before execution."
  },
  "proposed_worktree_plan": {
    "branch": "absorb/external-capability",
    "enabled": true
  },
  "required_human_review": true,
  "settlement_plan": [
    "Prove Extract text from uploaded invoice PDFs with local tests",
    "Record before/after settlement evidence",
    "Document the local pathway and review decision before absorption"
  ]
}
```

*Key Takeaway*:
- Status is `"absorbable"`.
- `policy_gate.decision` is `"requires_review"`. The runtime reminds the operator that external software must be reviewed before execution.

---

## 4. Step 3: Isolate Execution in a Git Worktree

To ensure unvetted code cannot break your active branch, create an isolated worktree branch:

```bash
# Create isolated worktree
git worktree add -b absorb/pdf-extractor .godspeed-harness/experiments/pdf-extractor

# Navigate into the worktree
cd .godspeed-harness/experiments/pdf-extractor
```

In the worktree:
1. Implement your internal adapter (`app/services/pdf.py`).
2. Add unit tests in `tests/test_pdf.py`.
3. Execute the test suite:
   ```bash
   pytest tests/test_pdf.py
   ```

---

## 5. Step 4: Settle Consequence and Merge

Once tests pass within the worktree, record the settlement against your project's ledger:

```bash
uv run godspeed-nav record-settlement \
  --workspace-root ../../.. \
  --affordance-id "aff-pdf-extractor" \
  --before '{"pdf_support": false}' \
  --after '{"pdf_support": true}' \
  --payment '{"time": 2, "integration": 2}' \
  --evidence '["pytest tests/test_pdf.py: 8 passed in 0.4s"]' \
  --horizon-delta 2.0
```

Finally, merge the validated worktree back into your primary branch and clean up:
```bash
cd ../../..
git merge absorb/pdf-extractor
git worktree remove .godspeed-harness/experiments/pdf-extractor
```

The capability is now part of your project, and the evidence of how it was absorbed is permanently preserved in developmental memory.

---

### What to Read Next
- [Subsystem: Policy & Governance](../subsystems/policy-and-governance.md)
- [Operational Runbook: Absorption Ingest](../runbooks/absorption-ingest.md)
- [Workflow: Absorption Lifecycle](../workflows/absorption-lifecycle.md)
