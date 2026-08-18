import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz


@dataclass
class ResolutionResult:
    raw_name: str
    canonical_name: str
    confidence: float
    matched: bool


class EntityResolver:

    def __init__(
        self,
        seed_entities: dict[str, list[str]] | None = None,
        threshold: int = 94,
        ambiguity_margin: int = 5,
    ):

        self.threshold = threshold
        self.ambiguity_margin = ambiguity_margin

        self.seed_entities = seed_entities or {
            "OpenAI": [
                "openai",
                "open ai",
                "openai inc",
                "openai, inc.",
            ],
            "Google DeepMind": [
                "google deepmind",
                "deepmind",
                "google-deepmind",
            ],
            "Anthropic": [
                "anthropic",
                "anthropic ai",
                "anthropic pbc",
            ],
            "Meta AI": [
                "meta ai",
                "meta artificial intelligence",
                "facebook ai",
            ],
            "Microsoft": [
                "microsoft",
                "microsoft corporation",
                "msft",
            ],
        }

    @staticmethod
    def normalize(value: str) -> str:

        if not value:
            return ""

        value = unicodedata.normalize(
            "NFKD",
            value,
        )

        value = value.lower()

        value = re.sub(
            r"[^\w\s]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    @staticmethod
    def compact(value: str) -> str:
        return re.sub(
            r"[^a-z0-9]",
            "",
            EntityResolver.normalize(value),
        )

    def register_entity(
        self,
        canonical_name: str,
        aliases: list[str] | None = None,
    ):

        if not canonical_name:
            return

        canonical_name = canonical_name.strip()

        if not canonical_name:
            return

        if canonical_name not in self.seed_entities:

            self.seed_entities[
                canonical_name
            ] = []

        aliases = aliases or []

        existing = self.seed_entities[
            canonical_name
        ]

        for alias in aliases:

            if not alias:
                continue

            alias = alias.strip()

            if (
                alias
                and alias != canonical_name
                and alias not in existing
            ):
                existing.append(alias)

    def register_entities(
        self,
        entities: list[str],
    ):

        for entity in entities:

            self.register_entity(
                entity
            )

    def resolve(
        self,
        raw_name: str,
    ) -> ResolutionResult:

        if not raw_name:

            return ResolutionResult(
                raw_name=raw_name,
                canonical_name=raw_name,
                confidence=0.0,
                matched=False,
            )

        normalized = self.normalize(
            raw_name
        )

        if not normalized:

            return ResolutionResult(
                raw_name=raw_name,
                canonical_name=raw_name,
                confidence=0.0,
                matched=False,
            )

        raw_compact = self.compact(
            raw_name
        )

        candidates = []

        for canonical, aliases in (
            self.seed_entities.items()
        ):

            for candidate in [
                canonical,
                *aliases,
            ]:

                candidate_normalized = (
                    self.normalize(candidate)
                )

                if not candidate_normalized:
                    continue

                candidates.append(
                    (
                        canonical,
                        candidate_normalized,
                    )
                )

                # Rule 1:
                # Exact normalized match.
                if (
                    normalized
                    == candidate_normalized
                ):

                    return ResolutionResult(
                        raw_name=raw_name,
                        canonical_name=canonical,
                        confidence=1.0,
                        matched=True,
                    )

                # Rule 2:
                # Exact compact match.
                candidate_compact = (
                    self.compact(candidate)
                )

                if (
                    len(raw_compact) >= 6
                    and raw_compact
                    == candidate_compact
                ):

                    return ResolutionResult(
                        raw_name=raw_name,
                        canonical_name=canonical,
                        confidence=1.0,
                        matched=True,
                    )

        # Rule 3:
        # Conservative fuzzy matching.
        scored = []

        for canonical, candidate in candidates:

            score = fuzz.ratio(
                normalized,
                candidate,
            )

            scored.append(
                (
                    score,
                    canonical,
                    candidate,
                )
            )

        if not scored:

            return ResolutionResult(
                raw_name=raw_name,
                canonical_name=raw_name,
                confidence=0.0,
                matched=False,
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        best_score, best_name, _ = scored[0]

        second_score = (
            scored[1][0]
            if len(scored) > 1
            else 0
        )

        margin = (
            best_score
            - second_score
        )

        # Very short names are dangerous for
        # fuzzy matching.
        if len(normalized) < 5:

            return ResolutionResult(
                raw_name=raw_name,
                canonical_name=raw_name,
                confidence=best_score / 100,
                matched=False,
            )

        # Require both a high score and a
        # sufficiently clear winning margin.
        if (
            best_score >= self.threshold
            and margin >= self.ambiguity_margin
        ):

            return ResolutionResult(
                raw_name=raw_name,
                canonical_name=best_name,
                confidence=best_score / 100,
                matched=True,
            )

        # Rule 4:
        # Do not make an unsafe mapping.
        return ResolutionResult(
            raw_name=raw_name,
            canonical_name=raw_name,
            confidence=best_score / 100,
            matched=False,
        )
