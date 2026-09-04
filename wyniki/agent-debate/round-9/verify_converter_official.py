"""Sprawdź poprawiony eksporter na ręcznym goldzie i oficjalnym scorerze CorefUD."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY / "kod"))

from scripts.export_adjudication_corefud import export_adjudication  # noqa: E402


SOURCE = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tAla\t_\tPROPN\t_\t_\t2\tnsubj\t_\t_
2\tma\t_\tVERB\t_\t_\t0\troot\t_\t_
3\tkota\t_\tNOUN\t_\t_\t2\tobj\t_\t_
4\tw\t_\tADP\t_\t_\t5\tcase\t_\t_
5\tdomu\t_\tNOUN\t_\t_\t2\tobl\t_\t_

"""

EXPECTED = """# newdoc id = d1
# global.Entity = eid-etype-head-other
# sent_id = d1-s1
1\tAla\t_\tPROPN\t_\t_\t2\tnsubj\t_\tEntity=(d1_gold_person-x-1-)
2\tma\t_\tVERB\t_\t_\t0\troot\t_\tEntity=(d1_gold_person-x-2-
3\tkota\t_\tNOUN\t_\t_\t2\tobj\t_\tEntity=d1_gold_person)(d1_gold_object[1/2]-x-2-)
4\tw\t_\tADP\t_\t_\t5\tcase\t_\t_
5\tdomu\t_\tNOUN\t_\t_\t2\tobl\t_\tEntity=(d1_gold_object[2/2]-x-2-)

"""


def _ids_sha256(ids: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-b-root", type=Path, required=True)
    args = parser.parse_args()
    scorer_python = args.agent_b_root / "kod/ext/venv-corpipe/Scripts/python.exe"
    scorer = args.agent_b_root / "kod/ext/corefud-scorer/corefud-scorer.py"

    candidate_ids = ["d1#1", "d1#2", "d1#3", "d1#4"]
    records = [
        {
            "id": "d1#1",
            "doc": "d1",
            "status": "shared",
            "char_segments": [[0, 3]],
            "gold_span": True,
            "gold_cluster": "person",
            "gold_head": 1,
        },
        {
            "id": "d1#2",
            "doc": "d1",
            "status": "only_v2",
            "char_segments": [[3, 5]],
            "gold_span": False,
        },
        {
            "id": "d1#3",
            "doc": "d1",
            "status": "only_corpipe",
            "char_segments": [[5, 9]],
            "gold_span": [[3, 9]],
            "gold_cluster": "person",
            "gold_head": 2,
        },
        {
            "id": "d1#full-review",
            "doc": "d1",
            "status": "full_document_review",
            "gold_mentions": [],
        },
        {
            "id": "d1#4",
            "doc": "d1",
            "status": "only_v2",
            "char_segments": [[5, 9], [10, 14]],
            "gold_span": True,
            "gold_cluster": "object",
            "gold_head": 2,
        },
        {
            "id": "d1#manifest",
            "doc": "d1",
            "status": "adjudication_manifest",
            "candidate_count": len(candidate_ids),
            "candidate_ids_sha256": _ids_sha256(candidate_ids),
            "random_window_count": 0,
            "random_window_ids_sha256": _ids_sha256([]),
        },
    ]

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        source = root / "source.conllu"
        adjudication = root / "adjudication"
        actual = root / "actual.conllu"
        expected = root / "expected.conllu"
        adjudication.mkdir()
        source.write_text(SOURCE, encoding="utf-8", newline="\n")
        (adjudication / "d1.jsonl").write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
            encoding="utf-8",
            newline="\n",
        )
        expected.write_text(EXPECTED, encoding="utf-8", newline="\n")
        summary = export_adjudication(source, adjudication, actual)
        byte_identical = actual.read_bytes() == expected.read_bytes()

        inspector = root / "inspect_udapi.py"
        inspector.write_text(
            "from udapi.core.document import Document\n"
            "import json, sys\n"
            "document = Document(filename=sys.argv[1])\n"
            "mentions = []\n"
            "for entity in document.coref_entities:\n"
            "    for mention in entity.mentions:\n"
            "        mentions.append([str(word.ord) for word in mention.words])\n"
            "print(json.dumps(sorted(mentions)))\n",
            encoding="utf-8",
            newline="\n",
        )
        inspected = subprocess.run(
            [str(scorer_python), str(inspector), str(actual)],
            text=True,
            capture_output=True,
            check=False,
        )
        udapi_mentions = json.loads(inspected.stdout) if inspected.returncode == 0 else None
        expected_mentions = sorted([["1"], ["2", "3"], ["3", "5"]])

        scores: dict[str, dict[str, object]] = {}
        invocations = {
            "head": ["-a", "head"],
            "exact": ["-x"],
        }
        for name, switches in invocations.items():
            command = [
                str(scorer_python),
                str(scorer),
                *switches,
                "--",
                str(expected),
                str(actual),
            ]
            completed = subprocess.run(command, text=True, capture_output=True, check=False)
            scores[name] = {
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }

    result = {
        "summary": summary,
        "actual_equals_independently_written_expected": byte_identical,
        "udapi_mention_word_orders": udapi_mentions,
        "expected_mention_word_orders": expected_mentions,
        "udapi_inspection_exit_code": inspected.returncode,
        "udapi_inspection_stderr": inspected.stderr,
        "scores": scores,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    success = byte_identical and udapi_mentions == expected_mentions and all(
        score["exit_code"] == 0
        and "CoNLL score: 100.00" in str(score["stdout"])
        and not score["stderr"]
        for score in scores.values()
    )
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
