#!/usr/bin/env python3
"""Build and validate small human-first compressed knowledge graph bundles.

The tool accepts either:
- <bundle>/ckg.json
- <bundle>/concepts/*.md with OKF-style YAML frontmatter
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


EDGE_TYPES = {"REQUIRES", "ENABLES", "IMPLEMENTS", "RELATES_TO"}
EDGE_STYLE = {
    "REQUIRES": {"color": "#b45309", "style": "solid"},
    "ENABLES": {"color": "#15803d", "style": "solid"},
    "IMPLEMENTS": {"color": "#2563eb", "style": "solid"},
    "RELATES_TO": {"color": "#64748b", "style": "dashed"},
}
TYPE_COLOR = {
    "claim": "#fecaca",
    "paper_claim": "#fecaca",
    "method": "#bbf7d0",
    "experiment": "#bfdbfe",
    "metric": "#fde68a",
    "artifact": "#ddd6fe",
    "implementation": "#bae6fd",
    "implementation_unit": "#bae6fd",
    "source": "#e5e7eb",
    "term": "#e5e7eb",
    "risk": "#fed7aa",
    "runbook": "#d9f99d",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def dot_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def slug(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9가-힣]+", "-", text)
    return text.strip("-") or "concept"


def parse_scalar(value: str):
    value = value.strip()
    if not value:
        return ""
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    if value == "[]":
        return []
    return value


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].splitlines()
    body = text[text.find("\n", end + 4) + 1 :]
    data: dict = {}
    current_key = None
    current_list_item = None
    for line in raw:
        if not line.strip() or line.strip().startswith("#"):
            continue
        if not line.startswith(" ") and ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = parse_scalar(value)
                current_key = None
            else:
                data[key] = []
                current_key = key
            current_list_item = None
            continue
        if current_key and line.strip().startswith("- "):
            item = line.strip()[2:]
            if ":" in item:
                k, v = item.split(":", 1)
                current_list_item = {k.strip(): parse_scalar(v)}
                data[current_key].append(current_list_item)
            else:
                current_list_item = None
                data[current_key].append(parse_scalar(item))
            continue
        if current_key and current_list_item is not None and ":" in line:
            k, v = line.strip().split(":", 1)
            current_list_item[k.strip()] = parse_scalar(v)
    return data, body


def load_from_markdown(bundle: Path) -> dict:
    concepts = []
    sources_by_id = {}
    edges = []
    for path in sorted((bundle / "concepts").glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        if not meta:
            continue
        concept = {
            "id": meta["id"],
            "title": meta.get("title", meta["id"]),
            "type": meta.get("type", "concept"),
            "taxonomy": meta.get("taxonomy", meta.get("type", "concept")),
            "status": meta.get("status", "draft"),
            "review_state": meta.get("review_state", "unreviewed"),
            "visibility": meta.get("visibility", "internal"),
            "summary": meta.get("summary", body.strip().split("\n", 1)[0] if body.strip() else ""),
            "why_it_matters": meta.get("why_it_matters", ""),
            "sources": meta.get("sources", []),
        }
        concepts.append(concept)
        for edge in meta.get("edges", []):
            edges.append({
                "source": concept["id"],
                "target": edge["target"],
                "type": edge.get("type", "RELATES_TO"),
                "rationale": edge.get("rationale", ""),
            })
    source_file = bundle / "sources.json"
    if source_file.exists():
        for src in json.loads(source_file.read_text(encoding="utf-8")):
            sources_by_id[src["id"]] = src
    return {
        "domain": bundle.name.replace("-", "_"),
        "title": bundle.name.replace("-", " ").title(),
        "description": "CKG bundle generated from OKF-style Markdown cards.",
        "version": "0.1.0",
        "sources": list(sources_by_id.values()),
        "concepts": concepts,
        "edges": edges,
    }


def load_bundle(bundle: Path) -> dict:
    json_path = bundle / "ckg.json"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    if (bundle / "concepts").exists():
        return load_from_markdown(bundle)
    raise FileNotFoundError(f"No ckg.json or concepts/*.md found under {bundle}")


def validate(bundle: Path, data: dict) -> dict:
    source_ids = {s["id"] for s in data.get("sources", [])}
    concept_ids = [c["id"] for c in data.get("concepts", [])]
    concept_set = set(concept_ids)
    errors = []
    warnings = []
    stale_sources = []

    duplicates = [cid for cid, count in Counter(concept_ids).items() if count > 1]
    for cid in duplicates:
        errors.append(f"duplicate concept id: {cid}")

    for concept in data.get("concepts", []):
        for field in ("id", "title", "type", "summary"):
            if not concept.get(field):
                errors.append(f"{concept.get('id', '<missing>')} missing required field {field}")
        for source_id in concept.get("sources", []):
            if source_id not in source_ids:
                warnings.append(f"{concept['id']} references missing source {source_id}")

    seen_edges = set()
    for edge in data.get("edges", []):
        key = (edge.get("source"), edge.get("target"), edge.get("type"))
        if key in seen_edges:
            warnings.append(f"duplicate edge {key}")
        seen_edges.add(key)
        if edge.get("source") not in concept_set:
            errors.append(f"edge source missing: {edge.get('source')}")
        if edge.get("target") not in concept_set:
            errors.append(f"edge target missing: {edge.get('target')}")
        if edge.get("type") not in EDGE_TYPES:
            errors.append(f"unsupported edge type: {edge.get('type')}")
        if not edge.get("rationale"):
            warnings.append(f"edge lacks rationale: {key}")

    for src in data.get("sources", []):
        rel = src.get("path")
        expected = src.get("source_hash")
        if not rel or not expected or not expected.startswith("sha256:"):
            continue
        path = bundle / rel
        if not path.exists():
            path = Path(rel)
        if not path.exists():
            warnings.append(f"source file missing: {rel}")
            continue
        actual = sha256_file(path)
        if actual != expected:
            stale_sources.append({"id": src["id"], "path": rel, "expected": expected, "actual": actual})

    report = {
        "domain": data.get("domain", bundle.name),
        "version": data.get("version", "0.1.0"),
        "concepts": len(data.get("concepts", [])),
        "edges": len(data.get("edges", [])),
        "sources": len(data.get("sources", [])),
        "edge_types": dict(Counter(e.get("type") for e in data.get("edges", []))),
        "concept_types": dict(Counter(c.get("type") for c in data.get("concepts", []))),
        "errors": errors,
        "warnings": warnings,
        "stale_sources": stale_sources,
        "status": "pass" if not errors else "fail",
    }
    return report


def write_cards(bundle: Path, data: dict):
    out = bundle / "cards"
    out.mkdir(exist_ok=True)
    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    concepts = {c["id"]: c for c in data["concepts"]}
    for edge in data["edges"]:
        outgoing[edge["source"]].append(edge)
        incoming[edge["target"]].append(edge)
    for concept in data["concepts"]:
        lines = [
            f"# {concept['title']}",
            "",
            f"**ID:** `{concept['id']}`",
            f"**Type:** `{concept.get('type', '')}`",
            f"**Status:** `{concept.get('status', '')}` / `{concept.get('review_state', '')}` / `{concept.get('visibility', '')}`",
            "",
            f"**Summary:** {concept.get('summary', '')}",
            "",
            f"**Why it matters:** {concept.get('why_it_matters', '')}",
            "",
            "## Connections",
            "",
        ]
        for edge in outgoing[concept["id"]]:
            target = concepts.get(edge["target"], {"title": edge["target"]})
            lines.append(f"- `{edge['type']}` -> **{target['title']}**: {edge.get('rationale', '')}")
        for edge in incoming[concept["id"]]:
            source = concepts.get(edge["source"], {"title": edge["source"]})
            lines.append(f"- **{source['title']}** -> `{edge['type']}`: {edge.get('rationale', '')}")
        if not outgoing[concept["id"]] and not incoming[concept["id"]]:
            lines.append("- No declared connections yet.")
        (out / f"{concept['id']}_{slug(concept['title'])}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(bundle: Path, data: dict, report: dict):
    domain = data.get("domain", bundle.name.replace("-", "_"))
    domains = bundle / "domains"
    build = bundle / "build"
    viz = bundle / "visualizations"
    domains.mkdir(exist_ok=True)
    build.mkdir(exist_ok=True)
    viz.mkdir(exist_ok=True)

    sources = {s["id"]: s for s in data.get("sources", [])}
    deps = defaultdict(list)
    for edge in data["edges"]:
        deps[edge["source"]].append(f"{edge['target']}:{edge['type']}")

    with (domains / f"{domain}.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["ConceptID", "ConceptLabel", "Dependencies", "TaxonomyID", "SourceURL", "SourceHash"])
        for concept in data["concepts"]:
            src = sources.get((concept.get("sources") or [""])[0], {})
            writer.writerow([
                concept["id"],
                concept["title"],
                "|".join(deps[concept["id"]]),
                concept.get("taxonomy", concept.get("type", "")),
                src.get("url") or src.get("path", ""),
                src.get("source_hash", "sha256:no-source-url"),
            ])

    metadata = {
        domain: {
            "nodes": len(data["concepts"]),
            "edges": len(data["edges"]),
            "description": data.get("description", ""),
            "version": data.get("version", "0.1.0"),
        }
    }
    (domains / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (build / "graph_index.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (build / "validation_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_visualizations(viz, domain, data)
    write_cards(bundle, data)


def write_visualizations(viz: Path, domain: str, data: dict):
    concepts = {c["id"]: c for c in data["concepts"]}
    incoming = Counter(e["target"] for e in data["edges"])
    outgoing = Counter(e["source"] for e in data["edges"])
    hubs = {cid for cid, _ in Counter({cid: incoming[cid] + outgoing[cid] for cid in concepts}).most_common(6)}

    dot = [
        f"digraph {domain} {{",
        "  graph [rankdir=LR, bgcolor=\"#ffffff\", pad=\"0.35\", nodesep=\"0.45\", ranksep=\"0.85\", splines=true, overlap=false];",
        "  node [shape=box, style=\"rounded,filled\", fontname=\"Arial\", fontsize=14, margin=\"0.11,0.07\", color=\"#334155\"];",
        "  edge [fontname=\"Arial\", fontsize=10, arrowsize=0.65, penwidth=1.2];",
        f"  label={dot_quote(data.get('title', domain) + ' · CKG')};",
        "  labelloc=\"t\";",
    ]
    for c in data["concepts"]:
        node = c["id"].replace("-", "_")
        fill = TYPE_COLOR.get(c.get("type"), "#f8fafc")
        width = 2.6 if c["id"] in hubs else 1.1
        label = f"{c['title']}\\n{c['id']} · {c.get('type', '')}"
        dot.append(f"  {node} [label={dot_quote(label)}, fillcolor={dot_quote(fill)}, penwidth={width}];")
    for e in data["edges"]:
        style = EDGE_STYLE[e["type"]]
        dot.append(
            f"  {e['source'].replace('-', '_')} -> {e['target'].replace('-', '_')} "
            f"[label={dot_quote(e['type'])}, color={dot_quote(style['color'])}, "
            f"fontcolor={dot_quote(style['color'])}, style={dot_quote(style['style'])}];"
        )
    dot.append("}")
    dot_path = viz / f"{domain}.dot"
    dot_path.write_text("\n".join(dot) + "\n", encoding="utf-8")

    mmd = ["---", f"title: {data.get('title', domain)}", "---", "flowchart LR"]
    for c in data["concepts"]:
        mmd.append(f"  {c['id'].replace('-', '_')}[\"{c['title']}<br/>{c.get('type', '')}\"]")
    for e in data["edges"]:
        mmd.append(f"  {e['source'].replace('-', '_')} -- {e['type']} --> {e['target'].replace('-', '_')}")
    (viz / f"{domain}.mmd").write_text("\n".join(mmd) + "\n", encoding="utf-8")

    dot_cmd = shutil.which("dot") or (r"C:\Program Files\Graphviz\bin\dot.exe" if Path(r"C:\Program Files\Graphviz\bin\dot.exe").exists() else None)
    svg_path = viz / f"{domain}.svg"
    if dot_cmd:
        subprocess.run([dot_cmd, "-Tsvg", str(dot_path), "-o", str(svg_path)], check=True)
        subprocess.run([dot_cmd, "-Tpng", "-Gdpi=150", str(dot_path), "-o", str(viz / f"{domain}.png")], check=True)

    edge_rows = "".join(f"<tr><td>{html.escape(str(k))}</td><td>{v}</td></tr>" for k, v in Counter(e["type"] for e in data["edges"]).most_common())
    cards = []
    outgoing_edges = defaultdict(list)
    for e in data["edges"]:
        outgoing_edges[e["source"]].append(e)
    for c in data["concepts"]:
        cards.append(
            f"<article><h3>{html.escape(c['title'])}</h3>"
            f"<p><strong>{html.escape(c.get('type', ''))}</strong> · {html.escape(c.get('taxonomy', ''))}</p>"
            f"<p>{html.escape(c.get('summary', ''))}</p>"
            f"<details><summary>Declared edges</summary><ul>"
            + "".join(
                f"<li>{html.escape(e['type'])} → {html.escape(concepts.get(e['target'], {'title': e['target']})['title'])}: {html.escape(e.get('rationale', ''))}</li>"
                for e in outgoing_edges[c["id"]]
            )
            + "</ul></details></article>"
        )
    image = f'<img src="{domain}.svg" alt="CKG graph">' if svg_path.exists() else "<p>Install Graphviz to render SVG/PNG.</p>"
    html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(data.get('title', domain))}</title>
<style>
body {{ margin:0; background:#f8fafc; color:#0f172a; font-family:Arial,sans-serif; }}
header {{ padding:22px 28px; background:#111827; color:white; }}
main {{ padding:18px 24px 32px; }}
table {{ border-collapse:collapse; background:white; border:1px solid #e5e7eb; margin-bottom:16px; }}
td,th {{ border-bottom:1px solid #e5e7eb; padding:7px 9px; }}
.figure {{ background:white; border:1px solid #e5e7eb; padding:12px; overflow:auto; margin-bottom:18px; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(310px,1fr)); gap:12px; }}
article {{ background:white; border:1px solid #e5e7eb; border-radius:8px; padding:12px; }}
img {{ max-width:none; }}
</style>
</head>
<body>
<header><h1>{html.escape(data.get('title', domain))}</h1><p>{len(data['concepts'])} concepts / {len(data['edges'])} edges</p></header>
<main><h2>Edge Types</h2><table>{edge_rows}</table><section class="figure">{image}</section><section class="cards">{''.join(cards)}</section></main>
</body></html>
"""
    (viz / f"{domain}.html").write_text(html_doc, encoding="utf-8")


def init_bundle(bundle: Path):
    bundle.mkdir(parents=True, exist_ok=True)
    (bundle / "concepts").mkdir(exist_ok=True)
    (bundle / "sources").mkdir(exist_ok=True)
    sample_source = bundle / "sources" / "source-note.md"
    sample_source.write_text("# Source Note\n\nThis is a sample source file.\n", encoding="utf-8")
    source_hash = sha256_file(sample_source)
    (bundle / "sources.json").write_text(
        json.dumps([
            {
                "id": "SRC-0001",
                "title": "Sample source note",
                "path": "sources/source-note.md",
                "source_hash": source_hash,
                "visibility": "public",
                "kind": "note",
            }
        ], indent=2),
        encoding="utf-8",
    )
    (bundle / "concepts" / "CKG-C-0001_sample-claim.md").write_text(
        """---
id: CKG-C-0001
title: "Sample Claim"
type: claim
taxonomy: claim.example
status: active
review_state: reviewed
visibility: public
summary: "A short claim that depends on one sample method."
why_it_matters: "It demonstrates a human-readable CKG card."
sources:
  - SRC-0001
edges:
  - target: CKG-C-0002
    type: REQUIRES
    rationale: "The claim needs the sample method."
---

# Sample Claim

Longer human-readable notes can live here.
""",
        encoding="utf-8",
    )
    (bundle / "concepts" / "CKG-C-0002_sample-method.md").write_text(
        """---
id: CKG-C-0002
title: "Sample Method"
type: method
taxonomy: method.example
status: active
review_state: reviewed
visibility: public
summary: "A small method node used by the sample claim."
why_it_matters: "It demonstrates typed edges."
sources:
  - SRC-0001
---

# Sample Method
""",
        encoding="utf-8",
    )
    (bundle / "README.md").write_text(
        f"""# Sample CKG Bundle

This bundle uses OKF-style Markdown concept cards plus `sources.json`.

Build:

```bash
python ../../scripts/ckg.py build .
```
""",
        encoding="utf-8",
    )


def cmd_build(args) -> int:
    bundle = Path(args.bundle).resolve()
    data = load_bundle(bundle)
    report = validate(bundle, data)
    write_outputs(bundle, data, report)
    print(f"{report['status']}: {report['concepts']} concepts, {report['edges']} edges")
    if report["errors"]:
        for err in report["errors"]:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    return 0


def cmd_validate(args) -> int:
    bundle = Path(args.bundle).resolve()
    data = load_bundle(bundle)
    report = validate(bundle, data)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "pass" else 1


def cmd_init(args) -> int:
    init_bundle(Path(args.bundle).resolve())
    print(f"initialized {args.bundle}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build and validate CKG bundles.")
    sub = parser.add_subparsers(required=True)

    p_init = sub.add_parser("init", help="create a sample OKF-style CKG bundle")
    p_init.add_argument("bundle")
    p_init.set_defaults(func=cmd_init)

    p_build = sub.add_parser("build", help="validate and generate CKG artifacts")
    p_build.add_argument("bundle")
    p_build.set_defaults(func=cmd_build)

    p_validate = sub.add_parser("validate", help="validate a CKG bundle")
    p_validate.add_argument("bundle")
    p_validate.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
