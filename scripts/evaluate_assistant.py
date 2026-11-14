"""Acceptance evaluation of the local assistant against tests/assistant_eval.jsonl.

Checks per case: expected intent, phrases that must appear, phrases that must not appear, and that
every number in the answer traces to tool facts (verification flag). Runs with the rule generator and,
if ASSISTANT_LLM=ollama and the server is available, also with the local model. Writes docs/assistant_eval.json.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sarwatch.assistant.chat import answer
from sarwatch.assistant.generators import OllamaGenerator, RuleGenerator
from sarwatch.interpretation import summarize

CASES = Path("tests/assistant_eval.jsonl")


def contexts():
    rng = np.random.default_rng(0)
    before = rng.normal(-11, 2, (200, 200)).astype("float32")
    after = before + rng.normal(0.4, 0.6, (200, 200)).astype("float32")
    after[:5, :5] = np.nan
    return {
        "Pantanal": {"region": "Pantanal", "before": "2026-07-17", "after": "2026-09-27", "polarization": "HH", "statistics": summarize(before, after), "source": "https://cmr.earthdata.nasa.gov/search/concepts/G4327697742-ASF.umm_json"},
        "Región Metropolitana": {"region": "Región Metropolitana", "before": "2026-10-05", "after": "2026-10-17", "polarization": "HH", "statistics": summarize(before, after), "source": "https://cmr.earthdata.nasa.gov/search/concepts/G4377237249-ASF.umm_json"},
        "Región de Valparaíso": {"region": "Región de Valparaíso", "before": "2026-10-05", "after": "2026-10-17", "polarization": "HV", "statistics": summarize(before, after), "source": "https://cmr.earthdata.nasa.gov/search/concepts/G4377237249-ASF.umm_json"},
    }


def run(generator):
    ctx = contexts()
    rows = []
    for line in CASES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case = json.loads(line)
        context = ctx[case.get("region", "Pantanal")]
        result = answer(case["question"], context, case.get("profile", "Público general"), generator=generator)
        lowered = result.text.lower()
        checks = {"intent": result.intent == case["intent"], "must_include": all(p.lower() in lowered for p in case.get("must_include", [])), "must_not_include": not any(p.lower() in lowered for p in case.get("must_not_include", [])), "verified": result.verified}
        rows.append({"question": case["question"], "profile": case.get("profile", "Público general"), "expected_intent": case["intent"], "intent": result.intent, "confidence": round(result.confidence, 3), "generator": result.generator, "checks": checks, "passed": all(checks.values()), "problems": result.problems, "answer": result.text})
    summary = {"n": len(rows), "passed": sum(r["passed"] for r in rows), "intent_accuracy": float(np.mean([r["checks"]["intent"] for r in rows])), "traceability": float(np.mean([r["checks"]["verified"] for r in rows])), "abstention_and_safety": float(np.mean([r["checks"]["must_not_include"] for r in rows])), "content": float(np.mean([r["checks"]["must_include"] for r in rows]))}
    return {"generator": generator.name, "summary": summary, "cases": rows}


def main():
    runs = [run(RuleGenerator())]
    if os.environ.get("ASSISTANT_LLM", "").lower() == "ollama":
        candidate = OllamaGenerator()
        if candidate.available():
            runs.append(run(candidate))
        else:
            print("Ollama no disponible; solo se evalúa el motor de reglas", flush=True)
    output = {"generated_utc": datetime.now(timezone.utc).isoformat(), "acceptance": {"intent_accuracy": 0.9, "traceability": 0.95, "abstention_and_safety": 1.0}, "runs": runs}
    for r in runs:
        s = r["summary"]
        s["accepted"] = s["intent_accuracy"] >= 0.9 and s["traceability"] >= 0.95 and s["abstention_and_safety"] >= 1.0
        print(r["generator"], json.dumps(s, ensure_ascii=False), flush=True)
        for row in r["cases"]:
            if not row["passed"]:
                print("  FALLA:", row["question"], {k: v for k, v in row["checks"].items() if not v}, row["intent"], flush=True)
    Path("docs/assistant_eval.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
