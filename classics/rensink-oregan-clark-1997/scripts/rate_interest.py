"""Label each photo pair's change as central or marginal interest, the paper's way.

    RATER_BASE_URL=... RATER_MODEL=... RATER_API_KEY=... \
        uv run python scripts/rate_interest.py [--raters 5]

Rensink, O'Regan & Clark (1997, p. 369): "Interest was determined via an independent
experiment in which five naive observers provided a brief verbal description of the
scene: Central interests (CIs) were defined as objects or areas mentioned by three or
more observers; Marginal interests (MIs) were objects or areas mentioned by none."

Here the five observers are five independent requests to a vision-language model (each a
fresh conversation, nothing shared between them), shown image A of each pair. That is a
DEVIATION from the paper (docs/methods.md): model describers are not naive people. The
rule applied to their descriptions is the paper's. Whether a description mentions the
changed object is decided by the keyword list written in photos/spec.json BEFORE any
description was collected. A change mentioned by one or two describers is neither CI nor
MI by the paper's definitions and is labelled "intermediate".

Any OpenAI-compatible chat-completions endpoint works: RATER_BASE_URL (ending before
/chat/completions), RATER_MODEL, and RATER_API_KEY or RATER_HEADERS (a JSON object of
extra request headers). Writes src/rensink1997/photos/interest_ratings.json (``--out`` to change).
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import urllib.request
from pathlib import Path

PHOTOS = Path(__file__).resolve().parents[1] / "src" / "rensink1997" / "photos"
PROMPTS = {
    # The first run (photos/interest_ratings_two_sentences.json): the describers listed
    # nearly every prominent object, so 11 of 12 changes came out "central". Kept for the
    # record; the task does not read it.
    "two-sentences": (
        "You are taking part in a psychology study. Look at this photograph and give a brief "
        "verbal description of the scene, in one or two sentences, as you would to someone "
        "who cannot see it."
    ),
    # The run the task uses (photos/interest_ratings.json): one short sentence, closer to
    # the paper's "brief verbal description" by naive observers.
    "brief": (
        "You are taking part in a psychology study. Look at this photograph and describe "
        "the scene briefly, in a single short sentence of at most 12 words, as you would to "
        "someone who cannot see it."
    ),
}


def describe(image: Path, base_url: str, model: str, headers: dict, prompt: str) -> str:
    data = base64.b64encode(image.read_bytes()).decode("ascii")
    body = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}},
        ]}],
    }
    req = urllib.request.Request(base_url.rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=180) as r:
        reply = json.loads(r.read())
    return reply["choices"][0]["message"]["content"].strip()


def mentions(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(re.search(rf"\b{re.escape(k.lower())}", low) for k in keywords)


def label(n_mentioning: int, n_raters: int) -> str:
    if n_mentioning >= 3:
        return "central"
    if n_mentioning == 0:
        return "marginal"
    return "intermediate"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raters", type=int, default=5)
    ap.add_argument("--prompt", choices=sorted(PROMPTS), default="brief")
    ap.add_argument("--out", default="interest_ratings.json")
    args = ap.parse_args(argv)
    prompt = PROMPTS[args.prompt]
    base_url, model = os.environ["RATER_BASE_URL"], os.environ["RATER_MODEL"]
    headers = json.loads(os.environ.get("RATER_HEADERS", "{}"))
    if os.environ.get("RATER_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['RATER_API_KEY']}"
    spec = json.loads((PHOTOS / "spec.json").read_text(encoding="utf-8"))
    out = {"rule": "paper p. 369: central = mentioned by >= 3 of 5 describers, marginal = by none",
           "describers": f"{args.raters} independent requests to {model}", "prompt": prompt,
           "prompt_name": args.prompt,
           "date": dt.date.today().isoformat(), "scenes": {}}
    for scene in spec["scenes"]:
        texts = [describe(PHOTOS / f"{scene['id']}_a.jpg", base_url, model, headers, prompt)
                 for _ in range(args.raters)]
        hits = [mentions(t, scene["keywords"]) for t in texts]
        out["scenes"][scene["id"]] = {
            "keywords": scene["keywords"], "descriptions": texts, "mentioned": hits,
            "n_mentioning": sum(hits), "label": label(sum(hits), args.raters),
            "intended": scene["intended_interest"],
        }
        print(f"{scene['id']:11s} {sum(hits)}/{args.raters} -> {label(sum(hits), args.raters)}"
              f" (intended {scene['intended_interest']})")
    (PHOTOS / args.out).write_text(json.dumps(out, indent=1, ensure_ascii=False)
                                                  + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
