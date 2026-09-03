"""Download versioned legal and coreference data with provenance metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


USER_AGENT = "mg2-coreference-research/1.0"


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.casefold() in {"script", "style", "noscript"}:
            self.ignored_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() in {"script", "style", "noscript"} and self.ignored_depth:
            self.ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.ignored_depth:
            return
        text = data.strip()
        if text:
            self.parts.append(text)


def _request(url: str, timeout: int = 60) -> bytes:
    """Fetch one HTTPS resource with a research-specific user agent."""
    if urlparse(url).scheme != "https":
        raise ValueError(f"Only HTTPS URLs are accepted: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Download failed for {url}: {exc}") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_manifest(output: Path, records: list[dict[str, object]]) -> None:
    manifest = {"created_at": datetime.now(UTC).isoformat(), "records": records}
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def download_corefud(args: argparse.Namespace) -> int:
    """Download an explicitly selected CorefUD archive and record its hash."""
    if not args.url:
        print(
            "CorefUD requires an explicit release URL. Verify the release and license, "
            "then run: python scripts/pobierz_dane.py corefud --url HTTPS_URL "
            "--output data/raw/corefud",
            file=sys.stderr,
        )
        return 2
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    data = _request(args.url, args.timeout)
    name = Path(urlparse(args.url).path).name or "corefud-download.bin"
    target = output / name
    target.write_bytes(data)
    digest = _sha256(data)
    if args.sha256 and digest.lower() != args.sha256.lower():
        target.unlink(missing_ok=True)
        raise RuntimeError(
            f"SHA-256 mismatch: expected {args.sha256.lower()}, got {digest.lower()}"
        )
    _write_manifest(
        output,
        [{
            "source": "corefud", "url": args.url, "file": target.name,
            "bytes": len(data), "sha256": digest,
            "license_check": "required before conversion",
        }],
    )
    print(f"Saved {target} ({len(data)} bytes, sha256={digest})")
    return 0


def _html_to_text(data: bytes) -> str:
    parser = _TextExtractor()
    parser.feed(data.decode("utf-8", errors="replace"))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(parser.parts))


def download_eli(args: argparse.Namespace) -> int:
    """Download a bounded sample of Polish official acts from the Sejm ELI API."""
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    list_url = f"https://api.sejm.gov.pl/eli/acts/DU/{args.year}"
    payload = json.loads(_request(list_url, args.timeout).decode("utf-8"))
    if isinstance(payload, dict):
        acts = payload.get("items") or payload.get("acts") or payload.get("results") or []
    elif isinstance(payload, list):
        acts = payload
    else:
        acts = []
    if not acts:
        raise RuntimeError(f"ELI response has no recognizable act list: {list_url}")

    records: list[dict[str, object]] = []
    for item in acts[: args.limit]:
        if not isinstance(item, dict):
            continue
        number = item.get("pos") or item.get("position") or item.get("num")
        if number is None:
            continue
        act_id = f"DU-{args.year}-{number}"
        text_url = f"https://api.sejm.gov.pl/eli/acts/DU/{args.year}/{number}/text.html"
        raw = _request(text_url, args.timeout)
        target = output / f"{act_id}.txt"
        target.write_text(_html_to_text(raw), encoding="utf-8")
        meta_target = output / f"{act_id}.metadata.json"
        meta_target.write_text(
            json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        records.append({
            "source": "eli", "url": text_url, "file": target.name,
            "metadata_file": meta_target.name, "bytes": target.stat().st_size,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "license_basis": "official document; verify art. 4 and PII policy",
        })
    if not records:
        raise RuntimeError("ELI list was downloaded, but no records had a position number")
    _write_manifest(output, records)
    print(f"Saved {len(records)} ELI acts in {output}")
    return 0


def explain_juddges(args: argparse.Namespace) -> int:
    """Stop before the 43 GB download and print a reproducible manual procedure."""
    del args
    print(
        "JuDDGES-pl is large and must be frozen deliberately. Review CC BY 4.0 and "
        "the privacy card at https://huggingface.co/datasets/JuDDGES/juddges-pl, "
        "then run huggingface-cli download --repo-type dataset JuDDGES/juddges-pl "
        "--local-dir DATA_DIR. Save the resolved revision and file hashes in "
        "DATA_DIR/manifest.json. Automatic bulk download is disabled.",
        file=sys.stderr,
    )
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="source", required=True)
    corefud = subparsers.add_parser("corefud")
    corefud.add_argument("--url")
    corefud.add_argument("--sha256")
    corefud.add_argument("--output", type=Path, default=Path("data/raw/corefud"))
    corefud.add_argument("--timeout", type=int, default=60)
    corefud.set_defaults(func=download_corefud)
    eli = subparsers.add_parser("eli")
    eli.add_argument("--year", type=int, required=True)
    eli.add_argument("--limit", type=int, default=10)
    eli.add_argument("--output", type=Path, default=Path("data/raw/eli"))
    eli.add_argument("--timeout", type=int, default=60)
    eli.set_defaults(func=download_eli)
    juddges = subparsers.add_parser("juddges")
    juddges.set_defaults(func=explain_juddges)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if getattr(args, "limit", 1) < 1:
        raise ValueError("--limit must be positive")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
