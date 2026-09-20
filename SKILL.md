---
name: manage-ckg
description: Create, update, validate, query, and visualize human-first compressed knowledge graphs. Use when Codex needs to manage OKF-style Markdown/YAML concept cards, JSON CKG seeds, source hashes, typed concept edges, NemoClaw-compatible CSV exports, graph indexes, validation reports, or reviewer-facing claim-evidence traceability.
---

# Manage CKG

## Default Model

Manage the CKG as a human-readable source bundle with generated graph artifacts.

- Prefer OKF-style Markdown concept cards for public, human-edited knowledge.
- Use JSON seeds when deterministic bulk generation is more practical.
- Generate CSV/JSON/DOT/Mermaid/HTML artifacts from the source bundle.
- Do not hand-edit generated artifacts unless repairing the generator.
- Treat missing edges as "not declared yet", not negative evidence.
- Keep private source text out of public CKGs unless the user explicitly marks it public.

## Workflow

1. Identify source format:
   - `ckg.json`: compact seed format.
   - `concepts/*.md`: OKF-style Markdown cards with YAML frontmatter.

2. Inspect before editing:
   - Read `README.md` if present.
   - Read `references/ckg-schema.md` for supported fields and edge semantics.
   - Check `build/validation_report.json` if it already exists.

3. Update source, not generated files:
   - Add `sources` first.
   - Add `concepts` with stable IDs, title, type, summary, visibility, and source IDs.
   - Add typed edges using `REQUIRES`, `ENABLES`, `IMPLEMENTS`, or `RELATES_TO`.
   - Add a human-readable rationale for every edge.

4. Validate and regenerate:
   - Run `python scripts/ckg.py build <bundle-dir>`.
   - Check `build/validation_report.json`.
   - Fix errors before relying on generated graph outputs.

5. Explain results to humans:
   - Lead with titles, summaries, evidence, status, and connection rationale.
   - Show IDs, hashes, and edge types as supporting details.

## Commands

```bash
python scripts/ckg.py init examples/my-ckg
python scripts/ckg.py build examples/my-ckg
python scripts/ckg.py validate examples/my-ckg
```

## References

Read `references/ckg-schema.md` for the bundle schema, OKF profile, edge semantics, and source-hash policy.
