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


def spoken_text(markdown: str) -> str:
    """Usuwa elementy Markdown, które nie powinny trafić do syntezatora."""
    text = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", markdown)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    text = re.sub(r"(?m)^#{1,6}\s+", "", text)
    text = re.sub(r"(?m)^[-*]\s+", "", text)
    text = re.sub(r"(?m)^\d+\.\s+", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chapters(markdown: str) -> list[tuple[str, str]]:
    """Dzieli tekst według nagłówków drugiego poziomu."""
    parts = re.split(r"(?m)^##\s+", markdown)[1:]
    result: list[tuple[str, str]] = []
    for part in parts:
        title, body = part.split("\n", 1)
        result.append((title.strip(), spoken_text(body)))
    if not result:
        raise ValueError("Brak rozdziałów oznaczonych nagłówkami '##'.")
    return result


def slug(value: str) -> str:
    value = value.lower()
    replacements = str.maketrans("ąćęłńóśźż", "acelnoszz")
    value = value.translate(replacements)
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:55] or "rozdzial"


async def save_with_retry(text: str, output: Path, voice: str, rate: str) -> None:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            await edge_tts.Communicate(text, voice, rate=rate).save(str(output))
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


async def generate(voice: str, rate: str, reuse_parts: bool) -> None:
    markdown = SOURCE.read_text(encoding="utf-8")
    parsed = chapters(markdown)
    parts_dir = ROOT / "czesci"
    parts_dir.mkdir(exist_ok=True)

    outputs: list[Path] = []
    for index, (title, body) in enumerate(parsed, start=1):
        speech = f"Rozdział {index}. {title}.\n\n{body}"
        output = parts_dir / f"{index:02d}-{slug(title)}.mp3"
        if reuse_parts and output.is_file() and output.stat().st_size > 0:
            print(f"[{index}/{len(parsed)}] Ponowne użycie: {title}", flush=True)
        else:
            print(f"[{index}/{len(parsed)}] Synteza: {title}", flush=True)
            await save_with_retry(speech, output, voice, rate)
        outputs.append(output)

    full_output = ROOT / "audiobook-pelny.mp3"
    print("[pełny] Łączenie kompletnych rozdziałów", flush=True)
    with full_output.open("wb") as combined:
        for output in outputs:
            combined.write(output.read_bytes())

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.name,
        "voice": voice,
        "rate": rate,
        "chapters": len(parsed),
        "word_count": len(spoken_text(markdown).split()),
        "files": [file_record(path) for path in [*outputs, full_output]],
    }
    (ROOT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Gotowe: {full_output}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice", default="pl-PL-MarekNeural")
    parser.add_argument("--rate", default="-5%")
    parser.add_argument(
        "--reuse-parts",
        action="store_true",
        help="Nie wykonuj ponownej syntezy istniejących rozdziałów.",
    )
    args = parser.parse_args()
    asyncio.run(generate(args.voice, args.rate, args.reuse_parts))


if __name__ == "__main__":
    main()
