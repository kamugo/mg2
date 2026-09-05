"""Audit B13 MoveHead provenance and a synthetic writer round-trip.

All Agent B inputs are read from the pinned B13 Git tree.  The only CoNLL-U
document is a three-token synthetic fixture created in a temporary directory.
No corpus, training, inference, checkpoint, or Agent B working-tree file is read.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


B13_SHA = "4199fb284498eae8cc5e2c9aefb1c26834b56864"
EXPECTED_WRITER_SHA256 = "4a8eb82841e35b285cda80659c5259ec99b1ab5269e9671c7384e96d75b48226"
STALE_VERIFICATION_WRITER_SHA256 = (
    "3fefde186bd486f1749f8597a96cf9e3f09cce1644dc04411cfc146b445dd022"
)
MOVEHEAD_SHA256 = "0bd50896d39dcc4ef472c0414ab150cf6e587af88e0159c4b146c748409449e1"

PATHS = {
    "writer": "kod/src/eval/corefud_writer.py",
    "structures": "kod/src/data/structures.py",
    "src_init": "kod/src/__init__.py",
    "data_init": "kod/src/data/__init__.py",
    "eval_init": "kod/src/eval/__init__.py",
    "manifest": "kod/data/agent-debate/round-13/MANIFEST.json",
    "verification": "kod/data/agent-debate/round-13/verification.json",
    "generator": "kod/scripts/verify_round13.py",
}


def _git_blob(repo: Path, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(repo), "show", f"{B13_SHA}:{path}"],
        check=True,
        capture_output=True,
    )
    return completed.stdout


def _git_text(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    return completed.stdout.strip()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _subscript_key(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Subscript):
        return None
    return node.slice.value if isinstance(node.slice, ast.Constant) else None


def _generator_compares_metrics_only(source: str) -> bool:
    tree = ast.parse(source)
    return any(
        isinstance(node, ast.Compare)
        and _subscript_key(node.left) == "metrics"
        and any(_subscript_key(item) == "metrics" for item in node.comparators)
        for node in ast.walk(tree)
    )


ROUND_TRIP_HARNESS = r'''
import hashlib
import json
import tempfile
from pathlib import Path

from src.data.structures import Document, Mention
from src.eval.corefud_writer import write_on_original
from udapi.core.document import Document as UdapiDocument

source = """# newdoc id = synthetic
# global.Entity = eid-etype-head-other
# sent_id = synthetic-s1
1\talpha\t_\tNOUN\t_\t_\t3\tdep\t3:dep|2:dep\tEntity=(gold-x-1-|Bridge=gold<other
2\tbeta\t_\tNOUN\t_\t_\t3\tdep\t3:dep\tEntity=gold)|SplitAnte=gold<other
3\tgamma\t_\tNOUN\t_\t_\t0\troot\t0:root\t_

"""
with tempfile.TemporaryDirectory(prefix="b13-synthetic-roundtrip-") as temporary:
    root = Path(temporary)
    original = root / "synthetic.conllu"
    output = root / "written.conllu"
    original.write_text(source, encoding="utf-8", newline="\n")
    document = Document(
        doc_id="synthetic",
        tokens=["alpha", "beta", "gamma"],
        sentence_spans=[(0, 2)],
    )
    report = write_on_original(
        str(original), [document], [[[Mention(0, 1)]]], str(output)
    )
    rendered = output.read_text(encoding="utf-8")
    parsed = UdapiDocument()
    parsed.from_conllu_string(rendered)
    entities = list(parsed.coref_entities)
    mentions = [mention for entity in entities for mention in entity.mentions]
    mention = mentions[0]
    words = list(mention.words)
    head_position = words.index(mention.head) + 1
    result = {
        "passed": (
            len(entities) == 1
            and len(mentions) == 1
            and head_position == 2
            and all(token not in rendered for token in ("gold", "Bridge=", "SplitAnte="))
        ),
        "entity_count": len(entities),
        "mention_count": len(mentions),
        "head_position_in_mention": head_position,
        "used_second_enhanced_parent": head_position == 2 and "3:dep|2:dep" in source,
        "gold_coreference_removed": all(
            token not in rendered for token in ("gold", "Bridge=", "SplitAnte=")
        ),
        "head_policy": report.head_policy,
        "head_udapi_version": report.head_udapi_version,
        "head_movehead_sha256": report.head_movehead_sha256,
        "rendered_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
    }
print("B13_SYNTHETIC_RESULT=" + json.dumps(result, sort_keys=True))
'''


def _synthetic_round_trip(blobs: dict[str, bytes]) -> dict[str, Any]:
    package_paths = {
        "writer": "src/eval/corefud_writer.py",
        "structures": "src/data/structures.py",
        "src_init": "src/__init__.py",
        "data_init": "src/data/__init__.py",
        "eval_init": "src/eval/__init__.py",
    }
    with tempfile.TemporaryDirectory(prefix="agent-a-b13-package-") as temporary:
        root = Path(temporary)
        for name, relative in package_paths.items():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blobs[name])
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(root)
        completed = subprocess.run(
            [sys.executable, "-B", "-c", ROUND_TRIP_HARNESS],
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    marker = "B13_SYNTHETIC_RESULT="
    lines = [line for line in completed.stdout.splitlines() if line.startswith(marker)]
    if completed.returncode != 0 or len(lines) != 1:
        raise RuntimeError(
            "Synthetic B13 writer round-trip failed: "
            f"exit={completed.returncode}, stderr_sha256="
            f"{_sha256(completed.stderr.encode('utf-8'))}"
        )
    result = json.loads(lines[0][len(marker):])
    result.update(
        {
            "exit_code": completed.returncode,
            "stderr_bytes": len(completed.stderr.encode("utf-8")),
            "source": "B13 Git blobs extracted into an isolated temporary package",
        }
    )
    return result


def _writer_provenance(
    writer_blob: bytes, manifest: dict[str, Any], verification: dict[str, Any]
) -> dict[str, Any]:
    normalized = writer_blob.replace(b"\r\n", b"\n")
    manifest_entry = manifest["inputs"]["src/eval/corefud_writer.py"]
    final_hash = _sha256(normalized)
    git_blob_runtime_hash = _sha256(writer_blob)
    stored_hash = verification["current_writer_sha256"]
    return {
        "final_git_blob_sha256_lf": final_hash,
        "final_git_blob_bytes_lf": len(normalized),
        "manifest_sha256_lf": manifest_entry["sha256_lf"],
        "manifest_bytes_lf": manifest_entry["bytes_lf"],
        "committed_verification_current_writer_sha256": stored_hash,
        "git_blob_runtime_sha256": git_blob_runtime_hash,
        "expected_final_hash_confirmed": final_hash == EXPECTED_WRITER_SHA256,
        "manifest_matches_final_blob": (
            manifest_entry["sha256_lf"] == final_hash
            and manifest_entry["bytes_lf"] == len(normalized)
        ),
        "git_blob_runtime_matches_final_blob": git_blob_runtime_hash == final_hash,
        "committed_verification_mismatch": stored_hash != final_hash,
        "known_stale_hash_confirmed": stored_hash == STALE_VERIFICATION_WRITER_SHA256,
    }


def _revision_pin(generator_source: str, verification: dict[str, Any]) -> dict[str, Any]:
    contains_b13 = B13_SHA in generator_source
    mutable_expression = (
        '(ROOT / "src/eval/corefud_writer.py").read_bytes()' in generator_source
    )
    return {
        "report_b_sha": verification["b_sha"],
        "report_b_sha_is_b13": verification["b_sha"] == B13_SHA,
        "generator_contains_b13_sha": contains_b13,
        "generator_asserts_b13_revision": contains_b13 and "rev-parse" in generator_source,
        "generator_hashes_mutable_worktree_writer": mutable_expression,
    }


def _exact_metric_evidence(
    generator_source: str, verification: dict[str, Any]
) -> dict[str, Any]:
    runs = [
        value for name, value in verification["scoring"].items()
        if name.endswith("/exact")
    ]
    metric_keys = sorted(set().union(*(run["metrics"] for run in runs)))
    values = [number for run in runs for number in run["metrics"].values()]
    conll = [run["conll"] for run in runs]
    forbidden_precision_recall = {"precision", "recall", "p", "r"}
    forbidden_counts = {"raw_counts", "counts", "pn", "pd", "rn", "rd"}
    run_keys = set().union(*(run for run in runs))
    nested_keys = set().union(*(run["metrics"] for run in runs))
    return {
        "exact_run_count": len(runs),
        "metric_keys": metric_keys,
        "metric_semantics": "rounded F1 for MUC/B-cubed/CEAF_e/LEA",
        "all_metric_values_rounded_to_two_decimals": all(
            number == round(number, 2) for number in values
        ),
        "conll_is_separate_and_rounded": all(
            "conll" in run and "conll" not in run["metrics"] for run in runs
        ) and all(number == round(number, 2) for number in conll),
        "precision_recall_present": bool(
            forbidden_precision_recall & (run_keys | nested_keys)
        ),
        "raw_counts_present": bool(forbidden_counts & (run_keys | nested_keys)),
        "generator_compares_metrics_dict_only": _generator_compares_metrics_only(
            generator_source
        ),
        "reported_metric_vectors_invariant": verification["exact_metric_vectors_invariant"],
        "reported_conll_invariant_separately": verification["exact_scores_invariant"],
    }


def _udapi_pin_scope(writer_source: str, verification: dict[str, Any]) -> dict[str, Any]:
    a12_modules = sorted(verification["udapi_source_hashes"])
    production_movehead_hashed = (
        "inspect.getsourcefile(MoveHead)" in writer_source
        and "hashlib.sha256(source.read_bytes())" in writer_source
        and MOVEHEAD_SHA256 in writer_source
    )
    document_imported = "from udapi.core.document import Document" in writer_source
    document_hashed = "getsourcefile(UdapiDocument)" in writer_source
    return {
        "production_udapi_version": "0.5.2" if 'UDAPI_VERSION = "0.5.2"' in writer_source else None,
        "production_hashed_modules": (
            ["udapi.block.corefud.movehead"] if production_movehead_hashed else []
        ),
        "production_imported_but_unhashed_modules": (
            ["udapi.core.document"] if document_imported and not document_hashed else []
        ),
        "a12_audit_hashed_modules": a12_modules,
        "a12_audit_hashed_module_count": len(a12_modules),
        "production_pin_is_narrower": production_movehead_hashed and len(a12_modules) == 5,
    }


def audit(agent_b_root: Path) -> dict[str, Any]:
    repo = agent_b_root.resolve()
    if _git_text(repo, "rev-parse", f"{B13_SHA}^{{commit}}") != B13_SHA:
        raise RuntimeError(f"Nie mozna rozstrzygnac przypietego B13: {B13_SHA}")
    blobs = {name: _git_blob(repo, path) for name, path in PATHS.items()}
    manifest = json.loads(blobs["manifest"])
    verification = json.loads(blobs["verification"])
    generator_source = blobs["generator"].decode("utf-8")
    writer_source = blobs["writer"].decode("utf-8")
    return {
        "schema_version": "agent-a-round-15-b13-movehead-audit-1.0",
        "agent_b_sha": B13_SHA,
        "scope": "pinned B13 Git blobs and one three-token synthetic CoNLL-U fixture",
        "inputs": {
            name: {
                "path": PATHS[name],
                "sha256": _sha256(value),
                "bytes": len(value),
            }
            for name, value in blobs.items()
        },
        "writer_provenance": _writer_provenance(
            blobs["writer"], manifest, verification
        ),
        "b13_revision_pin": _revision_pin(generator_source, verification),
        "exact_metric_evidence": _exact_metric_evidence(
            generator_source, verification
        ),
        "udapi_pin_scope": _udapi_pin_scope(writer_source, verification),
        "synthetic_round_trip": _synthetic_round_trip(blobs),
        "limitations": [
            "The metric audit inspects the committed aggregate report, not corpus output.",
            "The synthetic round-trip tests writer mechanics, not model quality.",
            "No legal data, checkpoint, training, inference, or dirty Agent B file is read.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.agent_b_root)
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8", newline="\n")
    else:
        print(serialized, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
