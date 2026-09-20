# CKG Schema

This skill supports two source formats:

1. `ckg.json`: compact JSON seed.
2. `source/ckg.json` or `source/*_ckg.json`: compact JSON seed kept under a source folder.
3. OKF-style Markdown concept cards under `concepts/*.md`.

Generated artifacts should be treated as rebuildable outputs.

## Concept Fields

Required:

- `id`: stable concept ID.
- `title`: human-readable title.
- `type`: concept type such as `claim`, `method`, `experiment`, `metric`, `artifact`, `risk`, `source`, or `runbook`.
- `summary`: one or two sentence explanation.

Recommended:

- `cards_dir`: generated card output directory. Defaults to `cards`; use `concepts` only for legacy bundles.
- `taxonomy`: domain-specific class.
- `status`: `draft`, `active`, `stale`, `deprecated`, or `rejected`.
- `review_state`: `unreviewed`, `reviewed`, or `needs_review`.
- `visibility`: `public`, `internal`, `restricted`, or `private`.
- `why_it_matters`: human-oriented rationale.
- `sources`: source IDs that support the concept.

## Source Fields

Required:

- `id`
- `title`
- `path` or `url`

Recommended:

- `source_hash`: `sha256:<hex>` for local stable files.
- `visibility`
- `kind`

For local files, the validator recomputes SHA-256 when possible. A mismatch is reported as stale evidence, not as automatic deletion.

## Edge Fields

Required:

- `source`
- `target`
- `type`
- `rationale`

Supported edge types:

| Edge | Meaning |
|---|---|
| `REQUIRES` | The source concept depends on the target concept. |
| `ENABLES` | The source concept makes the target concept possible or easier. |
| `IMPLEMENTS` | The source concept concretely implements the target concept. |
| `RELATES_TO` | The concepts should be read together, but there is no hard dependency. |

Keep the edge vocabulary small. Put nuance in `rationale`.

## OKF-Compatible Markdown Profile

OKF here means **Open Knowledge Format**, not Open Knowledge Foundation or Frictionless Data.
The Open Knowledge Format pattern uses Markdown files with YAML frontmatter and evolves through
compatible additions such as provenance, freshness, and trust signals. This skill uses a minimal
OKF-compatible profile and keeps typed CKG edges in explicit frontmatter fields:

```markdown
---
id: CKG-C-0001
title: "Boundary Violation Claim"
type: claim
taxonomy: claim.performance
status: active
review_state: reviewed
visibility: public
summary: "Short human-readable claim."
why_it_matters: "Why this claim matters."
sources:
  - SRC-PAPER
edges:
  - target: CKG-C-0002
    type: REQUIRES
    rationale: "The claim depends on this experiment."
---

# Boundary Violation Claim

Longer explanation can go here.
```

The parser intentionally supports a small YAML subset: scalars, lists, and lists of dictionaries. For complex metadata, use `ckg.json`.

Compatibility notes:

- `type`, `title`, `summary`, `sources`, `status`, and `visibility` map naturally to OKF-style frontmatter.
- `review_state`, `why_it_matters`, and `edges` are CKG extension fields.
- Extra frontmatter keys should be preserved by downstream tooling even when this lightweight builder does not interpret them.

## Generated Outputs

`scripts/ckg.py build <bundle-dir>` writes:

- `domains/<domain>.csv`: NemoClaw-compatible compressed graph.
- `domains/metadata.json`: node/edge counts and description.
- `build/graph_index.json`: query-friendly JSON graph.
- `build/validation_report.json`: validation result.
- `visualizations/<domain>.dot`: Graphviz DOT.
- `visualizations/<domain>.mmd`: Mermaid.
- `visualizations/<domain>.html`: human-readable graph/cards.
- `visualizations/<domain>.svg` and `.png` when Graphviz `dot` is available.

## Public Release Policy

- Prefer public/reviewer-facing artifacts as sources for public claims.
- Do not export private raw logs, private prompts, private generations, secrets, Slack transcripts, or admin/reviewer fields unless explicitly approved.
- Include references and attribution for borrowed ideas.
- Use an explicit open-source license for public GitHub repositories.
