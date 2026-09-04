#!/usr/bin/env python3
"""Porownywalny benchmark lokalnej inferencji CorPipe i CorefSeg-AE.

Skrypt uruchamia kazdy system jako nowy proces na tych samych pierwszych N
dokumentach Polish-PCC dev. Mierzy pelny czas procesu (wczytanie modelu,
inferencja i zapis), przepustowosc oraz szczytowe uzycie GPU widziane przez
``nvidia-smi``. Pierwsze uruchomienie jest oznaczane jako zimne, kolejne jako
rozgrzane przez cache systemu plikow/modeli.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class RunResult:
    system: str
    repeat: int
    cache_state: str
    command: list[str]
    cwd: str
    exit_code: int
    elapsed_seconds: float
    documents_per_second: float
    tokens_per_second: float
    gpu_baseline_mib: float | None
    gpu_peak_mib: float | None
    gpu_delta_peak_mib: float | None
    gpu_peak_utilization_percent: float | None
    log_path: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare_subset(source: Path, target: Path, limit: int) -> tuple[int, int]:
    """Zapisuje naglowek i pierwsze ``limit`` dokumentow CoNLL-U."""
    lines = source.read_text(encoding="utf-8").splitlines(keepends=True)
    selected: list[str] = []
    documents = 0
    tokens = 0
    include = True
    for line in lines:
        if line.startswith("# newdoc"):
            documents += 1
            include = documents <= limit
            if not include:
                break
        if include:
            selected.append(line)
            if line and line[0].isdigit() and "\t" in line:
                token_id = line.split("\t", 1)[0]
                if token_id.isdigit():
                    tokens += 1
    if documents < limit:
        raise ValueError(f"Zrodlo ma tylko {documents} dokumentow, wymagano {limit}.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("".join(selected), encoding="utf-8")
    return limit, tokens


def gpu_sample() -> tuple[float | None, float | None]:
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=memory.used,utilization.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode != 0:
            return None, None
        memory, utilization = result.stdout.strip().split(",")[:2]
        return float(memory.strip()), float(utilization.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None, None


def execute(
    system: str,
    repeat: int,
    command: list[str],
    cwd: Path,
    log_path: Path,
    documents: int,
    tokens: int,
) -> RunResult:
    baseline_mib, _ = gpu_sample()
    peak_mib = baseline_mib
    peak_utilization: float | None = None
    started = time.perf_counter()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as log:
        log.write("COMMAND: " + subprocess.list2cmdline(command) + "\n")
        log.flush()
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        while process.poll() is None:
            memory, utilization = gpu_sample()
            if memory is not None:
                peak_mib = memory if peak_mib is None else max(peak_mib, memory)
            if utilization is not None:
                peak_utilization = (
                    utilization
                    if peak_utilization is None
                    else max(peak_utilization, utilization)
                )
            time.sleep(0.25)
        exit_code = int(process.returncode)
    elapsed = time.perf_counter() - started
    delta = None
    if peak_mib is not None and baseline_mib is not None:
        delta = max(0.0, peak_mib - baseline_mib)
    return RunResult(
        system=system,
        repeat=repeat,
        cache_state="cold" if repeat == 1 else "warm-os-cache",
        command=command,
        cwd=str(cwd),
        exit_code=exit_code,
        elapsed_seconds=elapsed,
        documents_per_second=documents / elapsed,
        tokens_per_second=tokens / elapsed,
        gpu_baseline_mib=baseline_mib,
        gpu_peak_mib=peak_mib,
        gpu_delta_peak_mib=delta,
        gpu_peak_utilization_percent=peak_utilization,
        log_path=str(log_path),
    )


def summarize(results: list[RunResult]) -> dict[str, dict[str, float | int]]:
    output: dict[str, dict[str, float | int]] = {}
    for system in sorted({item.system for item in results}):
        successful = [item for item in results if item.system == system and item.exit_code == 0]
        if not successful:
            output[system] = {"successful_runs": 0}
            continue
        warm = [item for item in successful if item.repeat > 1] or successful
        output[system] = {
            "successful_runs": len(successful),
            "cold_seconds": successful[0].elapsed_seconds,
            "warm_median_seconds": statistics.median(item.elapsed_seconds for item in warm),
            "warm_median_documents_per_second": statistics.median(
                item.documents_per_second for item in warm
            ),
            "warm_median_tokens_per_second": statistics.median(
                item.tokens_per_second for item in warm
            ),
            "max_gpu_mib": max(
                (item.gpu_peak_mib or 0.0) for item in successful
            ),
        }
    return output


def render_report(payload: dict) -> str:
    lines = [
        "# Benchmark lokalnej inferencji",
        "",
        f"Data UTC: `{payload['created_at']}`",
        f"Dokumenty: **{payload['dataset']['documents']}**, tokeny slowne: "
        f"**{payload['dataset']['tokens']}**.",
        "",
        "Pomiar obejmuje uruchomienie nowego procesu, wczytanie modelu, inferencje "
        "i zapis wyniku. Nie obejmuje zewnetrznej tokenizacji surowego tekstu do "
        "CoNLL-U wymaganej przez CorPipe.",
        "",
        "| System | Udane | Cold [s] | Warm mediana [s] | dok./s | tokeny/s | peak GPU [MiB] |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, values in payload["summary"].items():
        if not values.get("successful_runs"):
            lines.append(f"| {name} | 0 | - | - | - | - | - |")
            continue
        lines.append(
            f"| {name} | {values['successful_runs']} | {values['cold_seconds']:.2f} | "
            f"{values['warm_median_seconds']:.2f} | "
            f"{values['warm_median_documents_per_second']:.2f} | "
            f"{values['warm_median_tokens_per_second']:.1f} | "
            f"{values['max_gpu_mib']:.0f} |"
        )
    lines.extend([
        "",
        "## Surowe przebiegi",
        "",
        "| System | Powtorzenie | Stan cache | Kod | Czas [s] | dok./s | tokeny/s | log |",
        "|---|---:|---|---:|---:|---:|---:|---|",
    ])
    for item in payload["runs"]:
        lines.append(
            f"| {item['system']} | {item['repeat']} | {item['cache_state']} | "
            f"{item['exit_code']} | {item['elapsed_seconds']:.2f} | "
            f"{item['documents_per_second']:.2f} | {item['tokens_per_second']:.1f} | "
            f"`{item['log_path']}` |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corefseg-root", type=Path, required=True)
    parser.add_argument("--documents", type=int, default=60)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--segment", type=int, default=1024)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    mg2_root = Path(__file__).resolve().parents[2]
    mg2_code = mg2_root / "kod"
    corefseg_code = args.corefseg_root.resolve() / "kod"
    output = (args.output or mg2_root / "wyniki" / "benchmark-inference").resolve()
    data_dir = output / "data"
    input_path = data_dir / "pl_pcc-corefud-dev.conllu"
    source = (
        mg2_code
        / "data/raw/corefud-1.4/extracted/CorefUD-1.4-public/data"
        / "CorefUD_Polish-PCC/pl_pcc-corefud-dev.conllu"
    )
    documents, tokens = prepare_subset(source, input_path, args.documents)

    corpipe_checkpoint = mg2_code / "models/corpipe26-onestage-corefud1.4-base-260702"
    variants = {
        "corpipe26-base": {
            "cwd": mg2_code,
            "checkpoint": corpipe_checkpoint / "model.pt",
        },
        "corefseg-unet-long": {
            "cwd": corefseg_code,
            "checkpoint": corefseg_code / "runs/unet_long/best.pt",
        },
        "corefseg-unet-long-dae": {
            "cwd": corefseg_code,
            "checkpoint": corefseg_code / "runs/unet_long_dae/best.pt",
        },
    }
    missing = [str(item["checkpoint"]) for item in variants.values() if not item["checkpoint"].is_file()]
    if missing:
        raise FileNotFoundError("Brak checkpointow:\n" + "\n".join(missing))

    runs: list[RunResult] = []
    for repeat in range(1, args.repeats + 1):
        order = list(variants)
        order = order[repeat - 1 :] + order[: repeat - 1]
        for system in order:
            run_dir = output / "runs" / system / f"repeat-{repeat}"
            if system == "corpipe26-base":
                command = [
                    sys.executable,
                    "vendor/corpipe26/corpipe26_onestage.py",
                    "--load",
                    str(corpipe_checkpoint),
                    "--exp",
                    str(run_dir),
                    "--test",
                    str(input_path),
                    "--batch_size",
                    "1",
                    "--segment",
                    str(args.segment),
                ]
            else:
                suffix = "unet_long_dae" if system.endswith("dae") else "unet_long"
                command = [
                    sys.executable,
                    "evaluate.py",
                    "--config",
                    f"configs/{suffix}.yaml",
                    "--checkpoint",
                    f"runs/{suffix}/best.pt",
                    "--split",
                    "dev",
                    "--data-dir",
                    str(data_dir),
                    "--max-docs",
                    str(documents),
                    "--out",
                    str(run_dir / "evaluation.json"),
                    "--device",
                    "cuda",
                ]
            result = execute(
                system,
                repeat,
                command,
                variants[system]["cwd"],
                run_dir / "process.log",
                documents,
                tokens,
            )
            runs.append(result)
            print(
                f"{system} repeat={repeat} exit={result.exit_code} "
                f"time={result.elapsed_seconds:.2f}s tokens/s={result.tokens_per_second:.1f}",
                flush=True,
            )

    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "dataset": {
            "source": str(source),
            "source_sha256": sha256(source),
            "benchmark_file": str(input_path),
            "benchmark_sha256": sha256(input_path),
            "documents": documents,
            "tokens": tokens,
        },
        "checkpoints": {
            name: {
                "path": str(item["checkpoint"]),
                "bytes": item["checkpoint"].stat().st_size,
                "sha256": sha256(item["checkpoint"]),
            }
            for name, item in variants.items()
        },
        "runs": [asdict(item) for item in runs],
    }
    payload["summary"] = summarize(runs)
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "RAPORT.md").write_text(render_report(payload), encoding="utf-8")
    return 0 if all(item.exit_code == 0 for item in runs) else 1


if __name__ == "__main__":
    raise SystemExit(main())
