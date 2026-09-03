"""Generuje rozdziały i pełny audiobook z pliku audiobook.md przez edge-tts."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import edge_tts


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "audiobook.md"

PRONUNCIATION_RULES = (
    (r"\bCorefSeg-AE\b", "Koref Seg A E"),
    (r"\bCorefUD\b", "Koref U D"),
    (r"\bCoNLL-U\b", "Konel U"),
    (r"\bCoNLL\b", "Konel"),
    (r"\bHerBERT-a\b", "Herberta"),
    (r"\bHerBERT-em\b", "Herbertem"),
    (r"\bHerBERT-owi\b", "Herbertowi"),
    (r"\bHerBERT\b", "Herbert"),
    (r"\bU-Netu\b", "ju netu"),
    (r"\bU-Netem\b", "ju netem"),
    (r"\bU-Netowi\b", "ju netowi"),
    (r"\bU-Net\b", "ju net"),
    (r"\bmention F1\b", "ef jeden wykrywania wzmianek"),
    (r"\bF1\b", "ef jeden"),
    (r"\bDAE\b", "de a e"),
    (r"\bVAE\b", "fał a e"),
    (r"\bGPU\b", "gie pe u"),
    (r"\bNLP\b", "en el pe"),
    (r"\bLLM\b", "el el em"),
    (r"\bPCA\b", "pe ce a"),
    (r"\bEMA\b", "e em a"),
    (r"\bPCC\b", "pe ce ce"),
)


def spoken_text(markdown: str, natural: bool = False) -> str:
    """Usuwa Markdown i opcjonalnie przygotowuje tekst do naturalnej narracji."""
    text = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", markdown)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?m)^#{1,6}\s+", "", text)
    text = re.sub(r"(?m)^[-*]\s+", "", text)
    text = re.sub(r"(?m)^\d+\.\s+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    if natural:
        text = naturalize_text(text)
    return text.strip()


def naturalize_text(text: str) -> str:
    """Poprawia wymowę terminów oraz rytm dłuższych fragmentów technicznych."""
    for pattern, replacement in PRONUNCIATION_RULES:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    symbols = {
        "→": " prowadzi do ",
        "↔": " wtedy i tylko wtedy, gdy ",
        "×": " razy ",
        "≤": " nie więcej niż ",
        "≥": " nie mniej niż ",
        "≈": " około ",
    }
    for symbol, replacement in symbols.items():
        text = text.replace(symbol, replacement)
    text = re.sub(r"(?<=\d)\.(?=\d)", ",", text)
    text = re.sub(r"[ \t]+", " ", text)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    return "\n\n…\n\n".join(paragraphs)


def chapters(markdown: str, natural: bool = False) -> list[tuple[str, str]]:
    """Dzieli tekst według nagłówków drugiego poziomu."""
    parts = re.split(r"(?m)^##\s+", markdown)[1:]
    result: list[tuple[str, str]] = []
    for part in parts:
        title, body = part.split("\n", 1)
        result.append((title.strip(), spoken_text(body, natural=natural)))
    if not result:
        raise ValueError("Brak rozdziałów oznaczonych nagłówkami '##'.")
    return result


def slug(value: str) -> str:
    value = value.lower()
    replacements = str.maketrans("ąćęłńóśźż", "acelnoszz")
    value = value.translate(replacements)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:55] or "rozdzial"


async def save_with_retry(
    text: str,
    output: Path,
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            await edge_tts.Communicate(
                text,
                voice,
                rate=rate,
                pitch=pitch,
                volume=volume,
            ).save(str(output))
            return
        except Exception as error:  # edge-tts zgłasza różne błędy sieciowe
            last_error = error
            if attempt < 3:
                await asyncio.sleep(attempt * 2)
    assert last_error is not None
    raise last_error


def file_record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


async def generate(
    voice: str,
    rate: str,
    pitch: str,
    volume: str,
    reuse_parts: bool,
    natural: bool,
    parts_dir_name: str,
    output_name: str,
    manifest_name: str,
) -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    parsed = chapters(markdown, natural=natural)
    parts_dir = ROOT / parts_dir_name
    parts_dir.mkdir(exist_ok=True)

    outputs: list[Path] = []
    for index, (title, body) in enumerate(parsed, start=1):
        spoken_title = naturalize_text(title) if natural else title
        speech = f"Rozdział {index}. {spoken_title}.\n\n…\n\n{body}\n\n…"
        output = parts_dir / f"{index:02d}-{slug(title)}.mp3"
        if reuse_parts and output.is_file() and output.stat().st_size > 0:
            print(f"[{index}/{len(parsed)}] Ponowne użycie: {title}", flush=True)
        else:
            print(f"[{index}/{len(parsed)}] Synteza: {title}", flush=True)
            await save_with_retry(speech, output, voice, rate, pitch, volume)
        outputs.append(output)

    full_output = ROOT / output_name
    print("[pełny] Łączenie kompletnych rozdziałów", flush=True)
    with full_output.open("wb") as combined:
        for output in outputs:
            combined.write(output.read_bytes())

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.name,
        "voice": voice,
        "rate": rate,
        "pitch": pitch,
        "volume": volume,
        "natural_text_processing": natural,
        "chapters": len(parsed),
        "word_count": len(spoken_text(markdown).split()),
        "files": [file_record(path) for path in [*outputs, full_output]],
    }
    (ROOT / manifest_name).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Gotowe: {full_output}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", default="pl-PL-ZofiaNeural")
    parser.add_argument("--rate", default="-2%")
    parser.add_argument("--pitch", default="+0Hz")
    parser.add_argument("--volume", default="+0%")
    parser.add_argument("--classic", action="store_true", help="Wyłącza poprawki narracyjne.")
    parser.add_argument("--parts-dir", default="czesci-naturalne")
    parser.add_argument("--output", default="audiobook-pelny-naturalny.mp3")
    parser.add_argument("--manifest", default="manifest-naturalny.json")
    parser.add_argument(
        "--reuse-parts",
        action="store_true",
        help="Nie wykonuj ponownej syntezy istniejących rozdziałów.",
    )
    args = parser.parse_args()
    asyncio.run(
        generate(
            args.voice,
            args.rate,
            args.pitch,
            args.volume,
            args.reuse_parts,
            not args.classic,
            args.parts_dir,
            args.output,
            args.manifest,
        )
    )


if __name__ == "__main__":
    main()
