# Manage CKG

`manage-ckg` is a general-purpose Codex skill and lightweight CLI for maintaining human-readable compressed knowledge graphs (CKGs).

It is designed for teams that want a graph that people can read, review, version in Git, and hand to coding agents without hiding the evidence trail in a vector index.

## What It Does

- Maintains CKG sources as OKF-compatible Markdown cards with YAML frontmatter.
- Supports a compact `ckg.json` seed format for deterministic bulk generation.
- Validates concept IDs, source references, edge types, and source file hashes.
- Generates reviewer-friendly cards, graph indexes, NemoClaw-style CSV exports, Mermaid, DOT, HTML, SVG, and PNG artifacts.
- Keeps generated artifacts rebuildable from source cards.

OKF means **Open Knowledge Format** here. It is not Open Knowledge Foundation/Frictionless Data. OKF is useful for this project because its Markdown + YAML-frontmatter model keeps the authoritative knowledge bundle readable in GitHub while still giving agents structured metadata for provenance, trust, lifecycle, and routing.

## Repository Layout

```text
manage-ckg/
  SKILL.md                 # Codex skill instructions
  README.md                # public project README
  LICENSE                  # MIT license
  agents/openai.yaml       # optional skill metadata
  references/ckg-schema.md # supported CKG/OKF profile
  schemas/                 # JSON schemas for seed files and concept metadata
  scripts/ckg.py           # stdlib-only builder/validator
  examples/minimal/        # synthetic example CKG bundle
  tests/smoke_test.py      # dependency-free smoke test
```

## Quick Start

```bash
python scripts/ckg.py init examples/my-ckg
python scripts/ckg.py build examples/my-ckg
python scripts/ckg.py validate examples/my-ckg
```

For the included example:

```bash
python scripts/ckg.py build examples/minimal
python scripts/ckg.py validate examples/minimal
```

The builder writes:

- `cards/*.md`: one readable card per concept.
- `domains/<domain>.csv`: NemoClaw-compatible compressed graph export.
- `domains/metadata.json`: graph counts and metadata.
- `build/graph_index.json`: query-friendly JSON graph.
- `build/validation_report.json`: validation result.
- `visualizations/<domain>.html`: human-readable graph page.
- `visualizations/<domain>.dot` and `.mmd`: Graphviz and Mermaid source.
- `visualizations/<domain>.svg` and `.png` when Graphviz `dot` is installed.

## Source Model

Use Markdown cards under `concepts/` for public, human-edited graphs:

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

Use `sources.json` to track source files, URLs, visibility, and optional SHA-256 hashes.

Supported edge types are intentionally small:

- `REQUIRES`: the source concept depends on the target concept.
- `ENABLES`: the source concept makes the target possible or easier.
- `IMPLEMENTS`: the source concept concretely implements the target.
- `RELATES_TO`: the concepts should be read together, but there is no hard dependency.

Put nuance in `rationale`, not in a large edge ontology.

## Skill Usage

This directory is itself a Codex skill because it contains `SKILL.md`. To use it as a local skill, copy or install the `manage-ckg` directory into your Codex skills location, then ask Codex to manage a CKG bundle.

The skill instructs the agent to:

- edit source cards or `ckg.json`, not generated files;
- add sources before claims;
- add edge rationales;
- validate before relying on generated artifacts;
- explain graph changes in human terms first, IDs and hashes second.

## Public Release Policy

- Do not publish private prompts, raw generations, Slack exports, secrets, or reviewer/admin-only fields unless explicitly approved.
- Prefer public papers, public code, public reports, and approved release artifacts as CKG sources.
- Treat stale source hashes as evidence drift that requires review.
- Keep generated artifacts rebuildable from source.
- This repository does not bundle NemoClaw graph data. The example graph is synthetic.

## References And Attribution

This project is an independent implementation inspired by public CKG and agent-knowledge conventions. It is not affiliated with, endorsed by, or sponsored by Google, Graphify.md/Graphify-Labs, NVIDIA, Open Knowledge Foundation, or the Frictionless Data project. NemoClaw is a trademark of NVIDIA Corporation. All referenced trademarks belong to their owners.

Primary references:

- Open Knowledge Format introduction, Google Cloud Blog: https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing
- OKF v0.2 trust/provenance update, Google Cloud Blog: https://cloud.google.com/blog/products/data-analytics/okf-v0-2-adds-trust-signals
- Open Knowledge Format repository: https://github.com/GoogleCloudPlatform/open-knowledge-format
- Graphify knowledge graph skill and CLI references: https://graphify.net/
- `ckg-nvidia-nemoclaw` package and CKG/MCP conventions: https://pypi.org/project/ckg-nvidia-nemoclaw/
- Open Definition, for general open-knowledge licensing context: https://opendefinition.org/od/2.1/en/
- Frictionless Data, for tabular data package context when CKG exports become datasets: https://frictionlessdata.io/introduction/

## License

MIT. See `LICENSE`.
