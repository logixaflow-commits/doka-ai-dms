# Doka Self-Audit

Run the repository-local structural and evidence preflight from the repository root:

```bash
python scripts/audit/doka_self_audit.py
```

Write a JSON report to the evidence directory:

```bash
python scripts/audit/doka_self_audit.py --output Phase0_Evidence/self-audit/latest.json
```

The tool uses only the Python standard library. It checks that canonical status/testing/deployment documents exist, checks that required release gates are referenced by `ROADMAP.md`, and checks for an obvious next-action marker in `CURRENT_STATE.md`. References to `Phase0_Evidence/` paths are advisory because some historical or owner-supplied evidence may be stored externally.

Exit codes:
- `0`: no structural failures (evidence gaps may still be reported).
- `1`: one or more structural/documentation failures.
- `2`: `--strict-evidence` was requested and evidence references need review.

**Important:** this is not release approval. A structural PASS does not prove real OCR accuracy, browser acceptance, copied-office safety, measured recovery, authenticated two-user isolation, live provider recovery, or security-setting compliance. Release gates remain governed by `ROADMAP.md` and `CURRENT_STATE.md`.
