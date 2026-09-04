"""Reproduce Agent B round-9 scorer-range and exporter-representation limits."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path


B_SHA = "c58d6534cf368cafe6cf78ff0c78212177d681fa"


def git_blob(repo: Path, path: str) -> bytes:
    return subprocess.run(
        ["git", "-C", str(repo), "show", f"{B_SHA}:{path}"],
        check=True,
        capture_output=True,
    ).stdout


def module_from_blob(name: str, value: bytes) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__file__ = f"{name}.git-blob.py"
    sys.modules[name] = module
    exec(compile(value, module.__file__, "exec"), module.__dict__)
    return module


def run(argv: list[str], cwd: Path) -> dict[str, object]:
    completed = subprocess.run(
        argv,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "argv": argv,
        "cwd": str(cwd),
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def id_hash(values: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def write_source(path: Path) -> None:
    rows = [
        "# newdoc id = d",
        "# global.Entity = eid-etype-head-other",
        "# sent_id = d-s1",
        "1\tA\t_\tNOUN\t_\t_\t2\tnsubj\t2:nsubj\t_",
        "2\tB\t_\tNOUN\t_\t_\t3\tnsubj\t3:nsubj\t_",
        "3\tC\t_\tVERB\t_\t_\t0\troot\t0:root\t_",
        "4\tD\t_\tNOUN\t_\t_\t3\tobj\t3:obj\t_",
        "5\tE\t_\tNOUN\t_\t_\t3\tobl\t3:obl\t_",
        "",
        "",
    ]
    path.write_text("\n".join(rows), encoding="utf-8", newline="\n")


def write_adjudication(path: Path, segments: list[list[list[int]]]) -> None:
    path.mkdir()
    candidate_ids = ["d#1", "d#2"]
    records = [
        {
            "id": candidate_ids[index],
            "doc": "d",
            "status": "shared",
            "char_segments": value,
            "gold_span": True,
            "gold_cluster": "same",
            "gold_head": 1,
        }
        for index, value in enumerate(segments)
    ]
    records.extend([
        {
            "id": "d#full",
            "doc": "d",
            "status": "full_document_review",
            "gold_mentions": [],
        },
        {
            "id": "d#manifest",
            "doc": "d",
            "status": "adjudication_manifest",
            "candidate_count": 2,
            "candidate_ids_sha256": id_hash(candidate_ids),
            "random_window_count": 0,
            "random_window_ids_sha256": id_hash([]),
        },
    ])
    (path / "d.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
        newline="\n",
    )


def write_self_score_fixture(path: Path) -> None:
    path.write_text(
        "# newdoc id = d\n"
        "# global.Entity = eid-etype-head-other\n"
        "# sent_id = d-s1\n"
        "1\tA\t_\tNOUN\t_\t_\t0\troot\t0:root\tEntity=(e-x-1-)\n"
        "1.1\tpro\t_\tPRON\t_\t_\t_\t_\t1:dep\t_\n"
        "2\tB\t_\tNOUN\t_\t_\t1\tdep\t1:dep\tEntity=(e-x-1-)\n\n",
        encoding="utf-8",
        newline="\n",
    )


def audit(args: argparse.Namespace) -> dict[str, object]:
    repo = args.agent_b_root.resolve()
    scorer = args.scorer.resolve()
    scorer_python = args.scorer_python.resolve()
    score_blob = git_blob(repo, "kod/scripts/score_official.py")
    exporter_blob = git_blob(repo, "kod/scripts/export_adjudication_corefud.py")
    exporter = module_from_blob("agent_b_round9_exporter", exporter_blob)
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "source.conllu"
        write_source(source)
        inspect_script = root / "inspect_udapi.py"
        inspect_script.write_text(
            "import json,sys\n"
            "from udapi.core.document import Document\n"
            "doc=Document(filename=sys.argv[1])\n"
            "print(json.dumps([sorted(str(w.ord) for w in mention.words) "
            "for entity in doc.coref_entities for mention in entity.mentions]))\n",
            encoding="utf-8",
            newline="\n",
        )

        exporter_cases = {}
        cases = {
            "same_cluster_crossing_continuous": [
                [[0, 3]],
                [[1, 4]],
            ],
            "same_cluster_interleaved_discontinuous": [
                [[0, 1], [3, 4]],
                [[1, 2], [4, 5]],
            ],
        }
        for name, segments in cases.items():
            adjudication = root / f"adj-{name}"
            output = root / f"{name}.conllu"
            write_adjudication(adjudication, segments)
            summary = exporter.export_adjudication(source, adjudication, output)
            parsed = run(
                [str(scorer_python), str(inspect_script), str(output)], root
            )
            exporter_cases[name] = {
                "input_segments": segments,
                "export_summary": summary,
                "output_created": output.is_file(),
                "udapi": parsed,
            }

        fixture = root / "one-document.conllu"
        write_self_score_fixture(fixture)
        evaluation = root / "wrong-range.json"
        base = evaluation.with_suffix("")
        for suffix in ("gold.dev.conllu", "pred.dev.conllu"):
            Path(f"{base}.{suffix}").write_bytes(fixture.read_bytes())
        evaluation.write_text(
            json.dumps({
                "checkpoint": "deliberately-missing-synthetic-model.pt",
                "split": "dev",
                "n_documents": 123,
                "threshold": 0.6,
                "task_scope": {
                    "zeros": "gold_nodes_predicted_labels",
                    "doc_range": [60, 183],
                    "syntax": "ud_from_file",
                },
                "export_on_original": {"path": str(fixture), "loss": {}},
                "export_loss": {"pred": {}, "gold": {}, "policies": {}},
            }),
            encoding="utf-8",
            newline="\n",
        )
        score_script = root / "score_official.py"
        score_script.write_bytes(score_blob)
        score_run = run([
            sys.executable,
            str(score_script),
            "--eval",
            str(evaluation),
            "--original-gold",
            str(fixture),
            "--scorer",
            str(scorer),
            "--scorer-python",
            str(scorer_python),
        ], root)
        official = json.loads(
            Path(f"{base}.official.json").read_text(encoding="utf-8")
        )
        range_result = {
            "actual_documents": 1,
            "reported_n_documents": official["n_documents"],
            "reported_doc_ranges": [
                result["task_scope"]["doc_range"]
                for result in official["runs"].values()
            ],
            "child_exit_codes": [
                result["exit"] for result in official["runs"].values()
            ],
            "conll": [result["conll"] for result in official["runs"].values()],
            "wrapper": score_run,
        }

    return {
        "schema_version": "agent-a-round-10-scorer-contract-audit-1.0",
        "agent_b_sha": B_SHA,
        "inputs": {
            "agent_b_score_official_sha256": hashlib.sha256(score_blob).hexdigest(),
            "agent_b_exporter_sha256": hashlib.sha256(exporter_blob).hexdigest(),
            "official_scorer_sha256": hashlib.sha256(scorer.read_bytes()).hexdigest(),
            "scorer_python": str(scorer_python),
        },
        "exporter_representability": exporter_cases,
        "document_range_counterexample": range_result,
        "interpretation": {
            "model_or_checkpoint": "not applicable; synthetic contract fixtures",
            "training_or_inference": "none",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", type=Path, required=True)
    parser.add_argument("--scorer", type=Path, required=True)
    parser.add_argument("--scorer-python", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
