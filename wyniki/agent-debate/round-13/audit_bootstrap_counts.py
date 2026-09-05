"""Synthetic paired count bootstrap using unmodified pinned scorer methods.

This audits count aggregation, not extraction of metric counts from annotations.
Only the Python standard library and a local scorer Git repository are needed.
No corpus data, training, inference, or rounded scorer output is used.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import random
import subprocess
from pathlib import Path

SCORER_SHA = "4fd7b0e0c661aeeff88bc60c19ef507b84d1b590"
SCORER_PATH = "scorer/eval/evaluator.py"
FIELDS = ("pn", "pd", "rn", "rd")
# Document scores are .9, .5, .15; corpus score is 20/26.
# Division by seven deliberately retains non-terminating fractional counts.
SYSTEM_A = tuple(tuple(x / 7 for x in row) for row in (
    (18.9, 21, 18.9, 21), (0.5, 1, 0.5, 1), (0.6, 4, 0.6, 4),
))
SYSTEM_B = tuple((pn * 0.8, pd, rn * 0.8, rd) for pn, pd, rn, rd in SYSTEM_A)


def load_scorer(repo: Path):
    blob = subprocess.run(
        ["git", "-C", str(repo.resolve()), "show", f"{SCORER_SHA}:{SCORER_PATH}"],
        check=True, capture_output=True,
    ).stdout
    tree = ast.parse(blob)
    f1_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "f1")
    evaluator = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Evaluator")
    names = {"update", "get_f1", "get_counts"}
    methods = [n for n in evaluator.body if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in methods} != names:
        raise RuntimeError("Pinned scorer methods missing")
    # Preserve original method bodies; omit unrelated optional metric dependencies.
    evaluator.body = methods
    namespace = {}
    exec(compile(ast.Module(body=[f1_node, evaluator], type_ignores=[]),
                 f"git:{SCORER_SHA}:{SCORER_PATH}", "exec"), namespace)
    return namespace["Evaluator"], namespace["f1"], hashlib.sha256(blob).hexdigest()


def aggregate(evaluator_class, documents, indices):
    evaluator = evaluator_class()
    evaluator.p_num = evaluator.p_den = evaluator.r_num = evaluator.r_den = 0
    evaluator.beta = 1
    evaluator.keep_aggregated_values = False
    evaluator.align_split_antecedents = lambda *_: ({}, {}, {})
    for index in indices:
        counts = documents[index]
        # Synthetic metric backend: the pinned update method performs accumulation.
        evaluator.__update__ = lambda *_, counts=counts, **__: counts
        evaluator.update((None, None, None, None, None))
    return evaluator.get_counts(), evaluator.get_f1()


def independent_f1(counts):
    pn, pd, rn, rd = counts
    denominator = pn * rd + rn * pd
    return 0.0 if denominator == 0 else 2 * pn * rn / denominator


def audit(scorer_root: Path, samples: int = 10000, seed: int = 13):
    if samples < 1:
        raise ValueError("samples must be positive")
    evaluator, f1, blob_hash = load_scorer(scorer_root)
    indices = tuple(range(3))
    total_a, corpus_a = aggregate(evaluator, SYSTEM_A, indices)
    total_b, corpus_b = aggregate(evaluator, SYSTEM_B, indices)
    rng = random.Random(seed)
    differences = []
    trace = hashlib.sha256()
    max_error = 0.0
    for _ in range(samples):
        selected = tuple(rng.randrange(3) for _ in indices)
        trace.update(bytes(selected))
        scores = []
        for documents in (SYSTEM_A, SYSTEM_B):
            counts, score = aggregate(evaluator, documents, selected)
            expected = tuple(math.fsum(documents[i][j] for i in selected) for j in range(4))
            if not all(math.isclose(x, y, rel_tol=1e-14, abs_tol=1e-14)
                       for x, y in zip(counts, expected)):
                raise AssertionError("Pinned scorer did not sum unrounded counts")
            error = abs(score - independent_f1(expected))
            max_error = max(max_error, error)
            if error > 1e-14:
                raise AssertionError("Corpus F1 disagrees with count reference")
            scores.append(score)
        differences.append(scores[0] - scores[1])
    ordered = sorted(differences)
    return {
        "schema_version": "synthetic-paired-count-bootstrap-1.0",
        "scorer_revision": SCORER_SHA,
        "scorer_blob_path": SCORER_PATH,
        "scorer_blob_sha256": blob_hash,
        "scope": "synthetic metric counts; pinned update/get_counts/get_f1/f1; no annotation metric extraction",
        "count_fields": FIELDS,
        "documents": 3,
        "systems": {"a": SYSTEM_A, "b": SYSTEM_B},
        "totals": {"a": total_a, "b": total_b},
        "corpus_f1": {"a": corpus_a, "b": corpus_b},
        "macro_document_f1_a": math.fsum(f1(*row) for row in SYSTEM_A) / 3,
        "paired_bootstrap": {
            "samples": samples, "seed": seed, "draw_size": 3,
            "same_document_indices_for_both_systems": True,
            "draws_sha256": trace.hexdigest(),
            "all_count_reference_checks_passed": True,
            "max_f1_reference_error": max_error,
            "mean_delta_a_minus_b": math.fsum(differences) / samples,
            "percentile_95_delta_order_statistics": [
                ordered[int((samples - 1) * 0.025)], ordered[int((samples - 1) * 0.975)],
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scorer-root", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    serialized = json.dumps(audit(args.scorer_root, args.samples, args.seed), indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
