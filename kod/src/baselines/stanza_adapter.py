"""Optional adapter to the Polish Stanza coreference processor."""

from __future__ import annotations

from collections.abc import Callable


class StanzaPolishAdapter:
    """Load Stanza lazily so the main experiment has no mandatory model download."""

    def __init__(self, pipeline: Callable[[str], object] | None = None) -> None:
        if pipeline is None:
            try:
                import stanza
            except ImportError as error:
                raise RuntimeError(
                    "Stanza is optional. Install stanza and download the Polish coref model first."
                ) from error
            pipeline = stanza.Pipeline("pl", processors="tokenize,coref")
        self.pipeline = pipeline

    def predict(self, text: str) -> list[list[str]]:
        """Return clusters as stable word-position identifiers."""
        document = self.pipeline(text)
        chains = getattr(document, "coref_chains", None)
        if chains is None:
            chains = getattr(document, "coref", None)
        if chains is None:
            raise RuntimeError("The loaded Stanza pipeline exposes no coreference chains.")
        result: list[list[str]] = []
        for chain in chains:
            mentions = []
            for mention in getattr(chain, "mentions", chain):
                sentence = getattr(mention, "sentence", getattr(mention, "sent_id", 0))
                start = getattr(mention, "start_word", getattr(mention, "start", 0))
                end = getattr(mention, "end_word", getattr(mention, "end", start))
                mentions.append(f"{sentence}:{start}-{end}")
            result.append(mentions)
        return result
