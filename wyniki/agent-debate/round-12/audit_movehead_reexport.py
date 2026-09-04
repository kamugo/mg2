"""Pinned PCC head-only re-export audit; never inference or model selection.

Required arguments: --repo-b, --scorer, --python, --output-dir. The output directory
must be empty and outside both repositories. The chosen Python must provide Udapi
0.5.2 with the pinned sources below. Input predictions and gold are read from Git
objects, never from B's working tree. Temporary CoNLL-U files are removed at exit;
only an aggregate verification.json remains, without document IDs or source text.

Both MoveHead keep_head_if_possible settings are compared before scoring. False
is the explicit prediction policy; if True differs, the audit fails rather than
selecting a policy using test scores. All changes are restricted to numeric Entity
head fields. Historical export losses are reported separately from this operation.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import hashlib
import importlib
import importlib.metadata
import json
import logging
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

B_SHA = "4c2e45ba06a4ef152cddd04204896e39851d6192"
SCORER_REVISION = "4fd7b0e0c661aeeff88bc60c19ef507b84d1b590"
SCORER_HASH = "418dde1a0ae44538b78383bfe522d06d7db793ddb7e23d01416eae61d53b1f1c"
GOLD_PATH = "kod/runs/dev61_183_original.conllu"
GOLD_HASH = "2f0d62c7612b6cdcca23bc00aefe3e623963d62947f42534e88da33f423c0bba"
BASE = "kod/runs/reinf_r7/frozen61_183/"
MODELS = {
    "v2_seed42": ("span", "6cd3916b16824bd62a4d6d3868917a81e71925b3568ee7330bc79c606ea18204"),
    "v2_seed1": ("span_s1", "bbdcb2fcd03d3896c4b4fa7e7a11e7aa6562e119c2109067e93454196bd36131"),
    "v2_seed2": ("span_s2", "9e5a86aa7252223187806e0f28d7594b9f4bf3028a5148b4250672556056a142"),
    "v1_seed42": ("r5", "7b45683570dc2bf9461708de7b1bcc0d03a99e3bf5de1123618f87697d5d98b7"),
}
UDAPI_HASHES = {
    "udapi.core.document": "ab106995d4f2060ac54ea948bd6a0effa26dcf0a8fd4c31639bb57d1f1254063",
    "udapi.block.corefud.movehead": "0bd50896d39dcc4ef472c0414ab150cf6e587af88e0159c4b146c748409449e1",
    "udapi.core.node": "f333b417b33336b503320935d99a4b8dda319f7069ebfd566f2a72e2bd696493",
    "udapi.core.coref": "5a5913ed271404ec1ef9335551922ed1a42c500edb7834ea74887371e41fe5f7",
    "udapi.block.read.conllu": "ff640d0f174d67572dbf8dc20a253f4860439cda55264ce03cd5c338eee2a8bb",
}
EVENT = re.compile(r"\(([^()]+)-x-(\d+)-(\))?|([^()]+)\)")
HEAD_FIELD = re.compile(rb"(\([^()\r\n|]+-x-)\d+(-)")


class AuditError(ValueError):
    """A required invariant failed; messages intentionally omit corpus content."""


def require(condition, message):
    if not condition:
        raise AuditError(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def verify_hash(data, expected, label):
    require(sha256(data) == expected, f"Pinned hash mismatch: {label}")


def git_blob(repo, path):
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f"{B_SHA}:{path}"], capture_output=True
    )
    require(result.returncode == 0, "Required pinned Git object is unavailable")
    return result.stdout


def load_backend():
    require(importlib.metadata.version("udapi") == "0.5.2", "Udapi 0.5.2 is required")
    for name, expected in UDAPI_HASHES.items():
        module = importlib.import_module(name)
        verify_hash(Path(module.__file__).read_bytes(), expected, name)
    document = importlib.import_module("udapi.core.document").Document
    movehead = importlib.import_module("udapi.block.corefud.movehead").MoveHead
    return document, movehead


@contextmanager
def aggregate_warnings():
    class Recorder(logging.Handler):
        def __init__(self):
            super().__init__()
            self.counts = Counter()

        def emit(self, record):
            self.counts[record.levelname] += 1

    recorder = Recorder()
    logger = logging.getLogger()
    old_handlers, old_level = logger.handlers[:], logger.level
    logger.handlers, logger.level = [recorder], logging.WARNING
    try:
        yield recorder.counts
    finally:
        logger.handlers, logger.level = old_handlers, old_level


def syntax_signature(raw):
    """Internal comparison only: IDs, all original UD fields, non-coreference MISC."""
    document = sentence = None
    signature = []
    for line in raw.decode("utf-8-sig").splitlines():
        if line.startswith("# newdoc"):
            document, sentence = line, None
        elif line.startswith("# sent_id"):
            sentence = line
        if not line or line.startswith("#"):
            continue
        columns = line.split("\t")
        require(len(columns) == 10, "Input must have ten columns")
        misc = "|".join(
            item for item in columns[9].split("|")
            if not item.startswith(("Entity=", "Bridge=", "SplitAnte="))
        )
        signature.append((document, sentence, tuple(columns[:9]), misc or "_"))
    return signature


def opening_slots(raw):
    """Map continuous mention identities to exact character offsets of head digits."""
    result, stacks = {}, defaultdict(list)
    document, token, absolute = -1, 0, 0
    for line in raw.decode("utf-8").splitlines(keepends=True):
        if line.startswith("# newdoc"):
            require(not any(stacks.values()), "Unfinished mention at document boundary")
            document, token = document + 1, 0
        if not line.strip() or line.startswith("#"):
            absolute += len(line)
            continue
        columns = line.rstrip("\r\n").split("\t")
        require(len(columns) == 10 and document >= 0, "Invalid token row or document boundary")
        if "-" in columns[0]:
            absolute += len(line)
            continue
        misc_offset, cursor = sum(len(c) + 1 for c in columns[:9]), 0
        for item in columns[9].split("|"):
            if item.startswith("Entity="):
                value, consumed = item[7:], 0
                for event in EVENT.finditer(value):
                    require(event.start() == consumed, "Unparsed Entity content")
                    consumed = event.end()
                    if event.group(1):
                        entity = event.group(1)
                        require("[" not in entity, "This pinned audit expects continuous predictions")
                        offset = absolute + misc_offset + cursor + 7
                        slot = (offset + event.start(2), offset + event.end(2), int(event.group(2)))
                        if event.group(3):
                            key = (document, entity, token, token)
                        else:
                            stacks[document, entity].append((token, slot))
                            continue
                    else:
                        entity = event.group(4)
                        require(bool(stacks[document, entity]), "Unmatched Entity closing")
                        start, slot = stacks[document, entity].pop()
                        key = (document, entity, start, token)
                    require(key not in result, "Ambiguous duplicate mention identity")
                    result[key] = slot
                require(consumed == len(value), "Unparsed Entity suffix")
            cursor += len(item) + 1
        token, absolute = token + 1, absolute + len(line)
    require(not any(stacks.values()), "Unfinished Entity annotation")
    return result


def parsed_mentions(path, document_class):
    document = document_class()
    document.from_conllu_string(path.read_text(encoding="utf-8-sig"))
    indices, document_index, token_index = {}, -1, 0
    for tree in document.trees:
        if tree.newdoc:
            document_index, token_index = document_index + 1, 0
        for node in tree.descendants_and_empty:
            indices[node] = (document_index, token_index)
            token_index += 1
    result = {}
    for entity in document.coref_entities:
        for mention in entity.mentions:
            positions = [indices[node] for node in mention.words]
            require(bool(positions) and len({d for d, _ in positions}) == 1,
                    "Empty or cross-document mention")
            tokens = [i for _, i in positions]
            require(tokens == list(range(tokens[0], tokens[-1] + 1)),
                    "Unexpected discontinuous prediction")
            key = (positions[0][0], entity.eid, tokens[0], tokens[-1])
            require(key not in result, "Duplicate parsed mention identity")
            result[key] = mention
    return result


def transform_heads(raw, working_dir, backend):
    document_class, movehead_class = backend
    before, after = working_dir / "transform-before.conllu", working_dir / "transform-after.conllu"
    before.write_bytes(raw)
    slots = opening_slots(raw)
    mentions = parsed_mentions(before, document_class)
    require(set(mentions) == set(slots), "Mention-to-Entity mapping is not bijective")
    engines = [movehead_class(keep_head_if_possible=value) for value in (True, False)]
    edits, expected, categories, transitions = [], {}, Counter(), Counter()
    changed = {"true": 0, "false": 0}
    disagreements = old_zeros = new_zeros = 0
    for key, mention in mentions.items():
        words, old_head = list(mention.words), mention.head
        start, end, serialized = slots[key]
        require(words.index(old_head) + 1 == serialized, "Parsed and serialized heads disagree")
        selections = (
            [(old_head, "single-word")] * 2 if len(words) == 1
            else [engine.find_head(mention) for engine in engines]
        )
        require(all(head in words and category != "cycle" for head, category in selections),
                "Unresolved head mapping or cycle fallback")
        for name, (head, _) in zip(("true", "false"), selections):
            changed[name] += int(head is not old_head)
        disagreements += int(selections[0][0] is not selections[1][0])
        selected, category = selections[1]
        index = words.index(selected) + 1
        expected[key] = index
        old_zeros += int(old_head.is_empty())
        new_zeros += int(selected.is_empty())
        if selected is not old_head:
            edits.append((start, end, str(index)))
            categories[category] += 1
            transitions[("zero" if old_head.is_empty() else "surface") + "->"
                        + ("zero" if selected.is_empty() else "surface")] += 1
    require(disagreements == 0,
            "MoveHead True/False policies disagree; no scoring or policy selection performed")
    text = raw.decode("utf-8")
    for start, end, value in sorted(edits, reverse=True):
        text = text[:start] + value + text[end:]
    modified = text.encode("utf-8")
    require(HEAD_FIELD.sub(rb"\1HEAD\2", raw) == HEAD_FIELD.sub(rb"\1HEAD\2", modified),
            "Non-head bytes changed")
    after.write_bytes(modified)
    resulting = parsed_mentions(after, document_class)
    require(set(resulting) == set(mentions), "Spans or cluster memberships changed")
    for key, mention in resulting.items():
        require(list(mention.words).index(mention.head) + 1 == expected[key],
                "Reparsed head differs from requested head")
    return modified, {
        "mentions_before": len(mentions), "mentions_after": len(resulting),
        "changed_mention_heads": len(edits), "changed_Entity_head_fields": len(edits),
        "old_zero_mentions": old_zeros, "new_zero_mentions": new_zeros,
        "zero_class_changes": sum(n for k, n in transitions.items() if k in ("zero->surface", "surface->zero")),
        "changed_categories": dict(categories), "head_type_transitions": dict(transitions),
        "policy_comparison": {"changed_keep_true": changed["true"], "changed_keep_false": changed["false"],
                              "different_selected_heads": disagreements, "chosen_policy": "false"},
        "losses": {"mentions_removed": 0, "clusters_removed": 0, "spans_changed": 0,
                   "non_head_bytes_changed": 0},
        "mention_Entity_mapping_bijective": True,
    }


def score(python, scorer, gold, prediction, mode, cwd):
    mode_args = ["-a", "head"] if mode == "head" else ["-x"]
    argv = [str(python), str(scorer), *mode_args, "--", str(gold), str(prediction)]
    started = time.perf_counter()
    result = subprocess.run(argv, cwd=cwd, capture_output=True)
    stdout = result.stdout.decode("utf-8", errors="replace")
    conll = re.search(r"CoNLL score:\s*([0-9.]+)", stdout)
    metrics = {}
    for name in ("muc", "bcub", "ceafe", "lea"):
        match = re.search(r"^" + name + r"\s*\n.*?F1:\s*([0-9.]+)", stdout, re.M | re.S)
        metrics[name] = float(match.group(1)) if match else None
    return {
        "argv": argv, "cwd": str(cwd), "exit_code": result.returncode,
        "conll": float(conll.group(1)) if conll else None, "metrics": metrics,
        "elapsed_seconds": time.perf_counter() - started,
        "stdout_sha256": sha256(result.stdout), "stdout_bytes": len(result.stdout),
        "stderr_sha256": sha256(result.stderr), "stderr_bytes": len(result.stderr),
        "already_indexed_warnings": (result.stdout + result.stderr).count(b"already indexed"),
        "raw_diagnostic_text_omitted": True,
    }


def prepare_output(output_dir, repo_b):
    output_dir, repo_b = output_dir.resolve(), repo_b.resolve()
    author_repo = Path(__file__).resolve().parents[3]
    require(not output_dir.is_relative_to(repo_b) and not output_dir.is_relative_to(author_repo),
            "Output must be outside both repositories")
    require(not output_dir.exists() or (output_dir.is_dir() and not any(output_dir.iterdir())),
            "Output directory must be new or empty")
    output_dir.mkdir(parents=True, exist_ok=True)


def audit(args):
    repo, scorer, python = args.repo_b.resolve(), args.scorer.resolve(), args.python.resolve()
    prepare_output(args.output_dir, repo)
    verify_hash(scorer.read_bytes(), SCORER_HASH, "official scorer")
    revision = subprocess.run(["git", "-C", str(scorer.parent), "rev-parse", "HEAD"], capture_output=True)
    require(revision.returncode == 0 and revision.stdout.decode().strip() == SCORER_REVISION,
            "Unexpected scorer Git revision")
    clean = subprocess.run(["git", "-C", str(scorer.parent), "diff", "--quiet", "HEAD", "--"], capture_output=True)
    require(clean.returncode == 0, "Scorer tracked files have local changes")
    backend = load_backend()
    report = {
        "schema_version": "agent-a-round-12-head-only-audit-1.0", "b_sha": B_SHA,
        "scope": "head-only re-export/sanitization; no reinference, training or model selection",
        "python": sys.version, "scorer_revision": SCORER_REVISION, "scorer_sha256": SCORER_HASH,
        "udapi_version": "0.5.2", "udapi_source_hashes": UDAPI_HASHES,
        "audit_script_sha256": sha256(Path(__file__).read_bytes()),
        "gold_git_path": GOLD_PATH, "gold_sha256": GOLD_HASH,
        "gold_transform_losses": {"mentions_removed": 0, "clusters_removed": 0, "heads_changed": 0},
        "models": {}, "scoring": {}, "gold_heads_used": False,
        "raw_text_or_document_ids_in_report": False,
    }
    with aggregate_warnings() as warnings, tempfile.TemporaryDirectory(prefix="head-audit-", dir=args.output_dir) as tmp:
        working = Path(tmp)
        raw_gold = git_blob(repo, GOLD_PATH)
        verify_hash(raw_gold, GOLD_HASH, "original gold")
        gold = working / "gold.conllu"
        gold.write_bytes(raw_gold)
        original_syntax, tasks = syntax_signature(raw_gold), []
        for label, (name, expected_hash) in MODELS.items():
            raw = git_blob(repo, BASE + name + ".pred_on_original.dev.conllu")
            verify_hash(raw, expected_hash, label)
            require(syntax_signature(raw) == original_syntax, "Original syntax/token/ID alignment failed")
            modified, result = transform_heads(raw, working, backend)
            before, after = working / (label + ".before.conllu"), working / (label + ".after.conllu")
            before.write_bytes(raw)
            after.write_bytes(modified)
            evaluation = json.loads(git_blob(repo, BASE + name + ".json"))
            official = json.loads(git_blob(repo, BASE + name + ".official.json"))
            result.update({
                "prediction_git_path": BASE + name + ".pred_on_original.dev.conllu",
                "before_sha256": sha256(raw), "after_sha256": sha256(modified),
                "checkpoint": evaluation["checkpoint"],
                "checkpoint_sha256_from_committed_report": official["checkpoint_sha256"],
                "historical_original_export_loss": evaluation.get("export_on_original", {}).get("loss"),
                "original_syntax_alignment": True,
            })
            report["models"][label] = result
            for stage, path in (("before", before), ("after", after)):
                for mode in ("head", "exact"):
                    tasks.append((f"{label}/{stage}/{mode}", path, mode))
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = {pool.submit(score, python, scorer, gold, path, mode, working): key
                       for key, path, mode in tasks}
            for future in as_completed(pending):
                report["scoring"][pending[future]] = future.result()
        report["logging_counts"] = dict(warnings)
    report["temporary_conllu_files_removed"] = True
    report["all_scorer_runs_succeeded"] = all(
        r["exit_code"] == 0 and r["conll"] is not None and all(v is not None for v in r["metrics"].values())
        for r in report["scoring"].values()
    )
    report["exact_scores_invariant"] = all(
        report["scoring"][label + "/before/exact"]["conll"]
        == report["scoring"][label + "/after/exact"]["conll"] for label in MODELS
    )
    report["exit_code"] = 0 if report["all_scorer_runs_succeeded"] and report["exact_scores_invariant"] else 1
    target = args.output_dir / "verification.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"verification": str(target), "exit_code": report["exit_code"]}))
    return report["exit_code"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-b", type=Path, required=True)
    parser.add_argument("--scorer", type=Path, required=True)
    parser.add_argument("--python", "--scorer-python", dest="python", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.python.resolve() != Path(sys.executable).resolve():
        return subprocess.run([str(args.python.resolve()), str(Path(__file__).resolve()), *sys.argv[1:]]).returncode
    try:
        return audit(args)
    except Exception as exc:
        # Do not expose corpus snippets or document IDs from third-party exceptions.
        message = str(exc) if isinstance(exc, AuditError) else "Audit failed before a verified result"
        print(json.dumps({"exit_code": 1, "error_type": type(exc).__name__, "error": message}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
