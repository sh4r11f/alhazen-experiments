#!/usr/bin/env python3
"""Check every experiment folder against the standalone-folder contract (README.md).

    python scripts/validate_catalog.py                 # every folder, lock check included
    python scripts/validate_catalog.py classics/stroop # one folder
    python scripts/validate_catalog.py --no-lock       # skip `uv lock --check` (offline)

Stdlib only (tomllib needs Python 3.11), so it runs before any environment exists.
Exit status 1 when any folder fails; every problem is reported, not just the first.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ["pyproject.toml", "uv.lock", "run.py", "instructions.md", "README.md",
            "docs/methods.md", "docs/experiment.json", "docs/listing.json", "docs/preview.png",
            "notebooks/analysis.ipynb"]
REQUIRED_DIRS = ["configs", "tests", "src"]
STATUSES = {"original-protocol", "adaptation", "demo"}
HARDWARE = {"display", "keyboard", "audio", "eye_tracker", "reward", "microstimulation",
            "recording", "mouse"}
DOC_TOP = {"schema", "schema_version", "title", "summary", "methods", "references", "tasks",
           "assumed", "deviations"}
DOC_TASK = {"id", "title", "summary", "description", "parameters_file", "parameters",
            "outcomes", "events", "timeline", "diagram"}
DOC_PARAM = {"name", "label", "group", "type", "unit", "default", "constraints", "meaning",
             "interactions", "source"}
PARAM_TYPES = {"duration", "number", "integer", "boolean", "string", "choice", "object"}
LISTING_KEYS = {"status", "status_reason", "collection", "authors", "original", "hardware",
                "subjects", "category", "tags", "art", "assets", "notes"}
# Identifiable or machine-specific strings that must never be committed.
PRIVATE = [
    (re.compile(r"/Users/[A-Za-z]"), "a macOS home path"),
    (re.compile(r"/home/[a-z]"), "a Linux home path"),
    (re.compile(r"[A-Za-z]:\\\\Users\\\\"), "a Windows home path"),
    (re.compile(r"/oak/|/scratch/users|/workspace/", re.I), "a cluster or sandbox path"),
    (re.compile(r"\bsherlock\b|\bsunet\b|\bfarmshare\b", re.I), "an institution host or ID"),
    (re.compile(r"\b(?!127\.0\.0\.1\b)(?!100\.1\.1\.1\b)(?!0\.0\.0\.0\b)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
     "an IP address (only 127.0.0.1 and the EyeLink default 100.1.1.1 are allowed)"),
    (re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.)[A-Za-z0-9.-]+\.[a-z]{2,}"), "an e-mail address"),
]
TEXT_EXT = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".txt", ".ipynb", ".cfg", ".csv"}


def folders(args: list[str]) -> list[Path]:
    if args:
        return [(ROOT / a).resolve() for a in args]
    out = sorted(p for p in (ROOT / "classics").iterdir() if p.is_dir() and not p.name.startswith("."))
    contributed = ROOT / "contributed"
    if contributed.is_dir():
        for author in sorted(p for p in contributed.iterdir() if p.is_dir()):
            out += sorted(p for p in author.iterdir() if p.is_dir())
    return out


def tracked_files(folder: Path) -> list[Path]:
    r = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z", "."], cwd=folder,
                       capture_output=True)
    if r.returncode == 0 and r.stdout:
        return [folder / n for n in r.stdout.decode().split("\0") if n]
    return [p for p in folder.rglob("*") if p.is_file() and ".venv" not in p.parts]


def dig(data, dotted):
    for part in dotted.split("."):
        if not isinstance(data, dict) or part not in data:
            raise KeyError(dotted)
        data = data[part]
    return data


def check(folder: Path, lock: bool) -> list[str]:
    errs: list[str] = []
    rel = folder.relative_to(ROOT).as_posix()
    parts = rel.split("/")
    collection = parts[0]
    if not ((collection == "classics" and len(parts) == 2) or (collection == "contributed" and len(parts) == 3)):
        return [f"{rel}: not classics/<name> or contributed/<author>/<name>"]
    for f in REQUIRED:
        if not (folder / f).is_file():
            errs.append(f"missing {f}")
    for d in REQUIRED_DIRS:
        if not (folder / d).is_dir():
            errs.append(f"missing {d}/")
    if errs:
        return errs

    # pyproject: alhazen-vision pinned by a release tag
    py = tomllib.loads((folder / "pyproject.toml").read_text(encoding="utf-8"))
    src = py.get("tool", {}).get("uv", {}).get("sources", {}).get("alhazen-vision", {})
    if src.get("git") != "https://github.com/sh4r11f/alhazen" or not re.fullmatch(r"v\d+\.\d+\.\d+", str(src.get("tag", ""))):
        errs.append("pyproject: [tool.uv.sources] alhazen-vision must be the GitHub repo at a vX.Y.Z tag")
    deps = " ".join(py.get("project", {}).get("dependencies", []))
    if "alhazen-vision" not in deps:
        errs.append("pyproject: alhazen-vision is not a dependency")
    lock_text = (folder / "uv.lock").read_text(encoding="utf-8")
    tag = src.get("tag")
    if tag and f"tag={tag}" not in lock_text and f"tag%3D{tag}" not in lock_text:
        errs.append(f"uv.lock does not pin alhazen at {tag}")
    if lock:
        env = dict(os.environ, UV_CACHE_DIR=os.environ.get("UV_CACHE_DIR", "/tmp/uv-cache"))
        env.pop("VIRTUAL_ENV", None)
        r = subprocess.run(["uv", "lock", "--check"], cwd=folder, capture_output=True, text=True, env=env)
        if r.returncode != 0:
            errs.append("uv.lock does not match pyproject.toml (`uv lock --check`): " + r.stderr.strip()[-300:])

    # run.py: TASKS / PARAMETERS / LADDERS as dict literals
    tree = ast.parse((folder / "run.py").read_text(encoding="utf-8"))
    tables = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    tables[t.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            tables[node.target.id] = node.value
    for name in ("TASKS", "PARAMETERS", "LADDERS"):
        if not isinstance(tables.get(name), ast.Dict):
            errs.append(f"run.py: {name} is not a module-level dict literal")
    task_ids = set()
    if isinstance(tables.get("TASKS"), ast.Dict):
        task_ids = {ast.literal_eval(k) for k in tables["TASKS"].keys}
    for cfg in re.findall(r'HERE / "configs" / "([^"]+)"', (folder / "run.py").read_text(encoding="utf-8")):
        if not (folder / "configs" / cfg).is_file():
            errs.append(f"run.py names configs/{cfg}, which does not exist")

    # experiment.json
    try:
        doc = json.loads((folder / "docs/experiment.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return errs + [f"docs/experiment.json: {e}"]
    if doc.get("schema") != "alhazen-documentation" or doc.get("schema_version") != 1:
        errs.append("docs/experiment.json: schema must be alhazen-documentation v1")
    for k in set(doc) - DOC_TOP:
        errs.append(f"docs/experiment.json: unknown field {k!r}")
    if len(doc.get("title", "")) > 160 or len(doc.get("summary", "")) > 1000 or not doc.get("summary"):
        errs.append("docs/experiment.json: title <=160, summary 1..1000 characters")
    if not doc.get("tasks"):
        errs.append("docs/experiment.json: no tasks")
    try:
        import yaml  # PyYAML, when present, lets the defaults be checked against the files
    except ModuleNotFoundError:
        yaml = None
    param_names: set[str] = set()
    for t in doc.get("tasks", []):
        for k in set(t) - DOC_TASK:
            errs.append(f"docs/experiment.json: task {t.get('id')}: unknown field {k!r}")
        if t.get("id") not in task_ids:
            errs.append(f"docs/experiment.json: task {t.get('id')!r} is not in run.py TASKS")
        pfile = folder / t.get("parameters_file", "")
        params = None
        if t.get("parameters_file") and not pfile.is_file():
            errs.append(f"docs/experiment.json: {t['parameters_file']} does not exist")
        elif t.get("parameters_file") and yaml:
            params = yaml.safe_load(pfile.read_text(encoding="utf-8"))
        for prm in t.get("parameters", []):
            for k in set(prm) - DOC_PARAM:
                errs.append(f"docs/experiment.json: parameter {prm.get('name')}: unknown field {k!r}")
            if prm.get("type") not in PARAM_TYPES or not prm.get("meaning"):
                errs.append(f"docs/experiment.json: parameter {prm.get('name')}: type and meaning required")
            param_names.add(prm.get("name"))
            param_names.add(f"{t.get('id')}/{prm.get('name')}")
            if params is not None:
                try:
                    value = dig(params, prm["name"])
                    if "default" in prm and prm["default"] != value:
                        errs.append(f"docs/experiment.json: {prm['name']} default {prm['default']!r} != {t['parameters_file']} {value!r}")
                except KeyError:
                    errs.append(f"docs/experiment.json: {prm['name']} is not in {t['parameters_file']}")
        for o in t.get("outcomes", []):
            if not re.fullmatch(r"[A-Z][A-Z0-9_]*", o.get("name", "")):
                errs.append(f"docs/experiment.json: outcome {o.get('name')!r} must be UPPER_CASE")

    # methods.md: the two tables, parameter and task references resolve
    methods = (folder / "docs/methods.md").read_text(encoding="utf-8")
    for heading in ("## Deviations from the original", "## Assumed, not in the paper"):
        if heading not in methods:
            errs.append(f"docs/methods.md: no '{heading}' section")
    for ref in re.findall(r"\[\[param:([^\]]+)\]\]", methods):
        if ref not in param_names:
            errs.append(f"docs/methods.md: [[param:{ref}]] is not a documented parameter")
    for ref in re.findall(r"\[\[task:([^\]]+)\]\]", methods):
        if ref not in task_ids:
            errs.append(f"docs/methods.md: [[task:{ref}]] is not a task")
    if "(template)" in methods or "template placeholder" in methods or "CITATION" in methods:
        errs.append("docs/methods.md still holds template text")
    assumed = doc.get("assumed")
    if not isinstance(assumed, list):
        errs.append("docs/experiment.json: 'assumed' must be a list (empty only if the paper states everything)")
        assumed = []
    if "## Assumed, not in the paper" in methods:
        section = methods.split("## Assumed, not in the paper", 1)[1].split("\n## ", 1)[0]
        rows = [r for r in section.splitlines() if r.strip().startswith("|") and not set(r.strip()) <= set("|-: ")]
        if max(len(rows) - 1, 0) != len(assumed):
            errs.append(f"docs/methods.md assumed table has {max(len(rows) - 1, 0)} rows, experiment.json lists {len(assumed)}")
    for item in assumed:
        if not all(item.get(k) for k in ("item", "value", "reason")):
            errs.append(f"docs/experiment.json: assumed item needs item, value, reason: {item}")
        key = item.get("key")
        if key:
            f = folder / item.get("file", "configs/task.yaml")
            leaf = key.split(".")[-1]
            lines = f.read_text(encoding="utf-8").splitlines() if f.is_file() else []
            hit = [ln for ln in lines if re.match(rf"\s*-?\s*{re.escape(leaf)}\s*:", ln)]
            if not hit:
                errs.append(f"assumed key {key} not found in {f.relative_to(folder)}")
            elif not any("ASSUMED" in ln for ln in hit):
                errs.append(f"assumed key {key} is not flagged '# ASSUMED' in {f.relative_to(folder)}")
    for d in doc.get("deviations", []):
        if not all(d.get(k) for k in ("item", "original", "here", "reason")):
            errs.append(f"docs/experiment.json: deviation needs item, original, here, reason: {d}")
    if "(template)" in json.dumps(doc) or "template placeholder" in json.dumps(doc):
        errs.append("docs/experiment.json still holds template text")

    # listing.json
    lst = json.loads((folder / "docs/listing.json").read_text(encoding="utf-8"))
    for k in set(lst) - LISTING_KEYS:
        errs.append(f"docs/listing.json: unknown field {k!r}")
    if lst.get("status") not in STATUSES:
        errs.append(f"docs/listing.json: status must be one of {sorted(STATUSES)}")
    if lst.get("collection") != collection:
        errs.append(f"docs/listing.json: collection {lst.get('collection')!r} but the folder is under {collection}/")
    orig = lst.get("original") or {}
    if not orig.get("citation") or not isinstance(orig.get("year"), int) or "CITATION" in orig.get("citation", ""):
        errs.append("docs/listing.json: original.citation and original.year are required")
    hw = lst.get("hardware") or {}
    if set(hw) - HARDWARE or hw.get("display") is not True:
        errs.append(f"docs/listing.json: hardware keys {sorted(HARDWARE)}, display true")
    if not (folder / lst.get("art", "docs/preview.png")).is_file():
        errs.append("docs/listing.json: art file missing")

    # standalone: no sibling imports, no paths out of the folder, nothing private
    siblings = {p.name.replace("-", "_") for p in folder.parent.iterdir() if p.is_dir() and p != folder}
    own = {p.name for p in (folder / "src").iterdir() if p.is_dir()}
    for f in tracked_files(folder):
        if f.suffix not in TEXT_EXT or not f.is_file():
            continue
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        frel = f.relative_to(folder).as_posix()
        if f.suffix == ".py":
            for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", text, re.M):
                pkg = m.group(1)
                if pkg in siblings and pkg not in own:
                    errs.append(f"{frel}: imports {pkg}, a sibling folder's package")
            if re.search(r"parents\[(?:[3-9])\]|\.\./\.\.|sys\.path\.(?:insert|append)\([^)]*\.\.", text):
                errs.append(f"{frel}: reaches outside the folder")
        if f.suffix == ".ipynb":
            nb = json.loads(text)
            if any(c.get("outputs") for c in nb.get("cells", [])):
                errs.append(f"{frel}: commit notebooks without outputs")
        for rx, what in PRIVATE:
            m = rx.search(text)
            if m and not (frel == "pyproject.toml" and what == "an e-mail address"):
                errs.append(f"{frel}: contains {what}: {m.group(0)!r}")
    return errs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="*")
    ap.add_argument("--no-lock", action="store_true")
    a = ap.parse_args()
    bad = 0
    for folder in folders(a.folders):
        errs = check(folder, lock=not a.no_lock)
        rel = folder.relative_to(ROOT).as_posix()
        if errs:
            bad += 1
            print(f"FAIL {rel}")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"ok   {rel}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
