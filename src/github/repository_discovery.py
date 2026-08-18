import asyncio
import os
import re
from difflib import SequenceMatcher

import aiohttp


class GitHubRepositoryDiscovery:

    API_URL = "https://api.github.com/search/repositories"

    STOP_WORDS = {
        "a", "an", "the", "and", "or", "of", "for", "to",
        "in", "on", "with", "via", "using", "based", "from",
        "by", "large", "scale", "new", "novel", "towards",
        "toward", "learning", "deep", "neural"
    }

    def __init__(
        self,
        token=None,
        timeout_seconds=15,
        min_score=0.35
    ):
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.timeout_seconds = timeout_seconds
        self.min_score = min_score

    def normalize(self, text):
        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text.strip()

    def words(self, text):
        normalized = self.normalize(text)

        return {
            word
            for word in normalized.split()
            if len(word) >= 3
            and word not in self.STOP_WORDS
        }

    def extract_project_terms(self, title):
        normalized = self.normalize(title)

        parts = re.split(
            r"\s*[:\-]\s*",
            normalized,
            maxsplit=1
        )

        if len(parts) > 1:
            first_part = parts[0].strip()

            if 1 <= len(first_part.split()) <= 5:
                return self.words(first_part)

        return set()

    def similarity(
        self,
        paper_title,
        repository
    ):
        title_words = self.words(
            paper_title
        )

        project_terms = (
            self.extract_project_terms(
                paper_title
            )
        )

        repo_name = repository.get(
            "name",
            ""
        )

        repo_full_name = repository.get(
            "full_name",
            ""
        )

        description = repository.get(
            "description",
            ""
        ) or ""

        repo_words = self.words(
            repo_name
        )

        full_name_words = self.words(
            repo_full_name.replace(
                "/",
                " "
            )
        )

        description_words = self.words(
            description
        )

        project_overlap = 0.0

        if project_terms:
            project_overlap = (
                len(
                    project_terms
                    & (
                        repo_words
                        | full_name_words
                    )
                )
                / len(project_terms)
            )

        title_overlap = 0.0

        if title_words:
            title_overlap = (
                len(
                    title_words
                    & (
                        repo_words
                        | full_name_words
                        | description_words
                    )
                )
                / len(title_words)
            )

        description_overlap = 0.0

        if title_words:
            description_overlap = (
                len(
                    title_words
                    & description_words
                )
                / len(title_words)
            )

        name_similarity = SequenceMatcher(
            None,
            self.normalize(paper_title),
            self.normalize(repo_name)
        ).ratio()

        popularity = repository.get(
            "stargazers_count",
            0
        )

        popularity_bonus = min(
            popularity / 100000,
            0.10
        )

        score = (
            project_overlap * 0.50
            + title_overlap * 0.25
            + description_overlap * 0.15
            + name_similarity * 0.10
            + popularity_bonus
        )

        return min(
            score,
            1.0
        )

    async def search(self, title):
        headers = {
            "Accept":
                "application/vnd.github+json",
            "User-Agent":
                "AI-Intelligence-Ingestion-Pipeline/1.0"
        }

        if self.token:
            headers[
                "Authorization"
            ] = f"Bearer {self.token}"

        timeout = aiohttp.ClientTimeout(
            total=self.timeout_seconds
        )

        project_terms = (
            self.extract_project_terms(
                title
            )
        )

        title_words = self.words(
            title
        )

        queries = []

        if project_terms:
            queries.append(
                " ".join(
                    sorted(project_terms)
                )
            )

        queries.append(
            " ".join(
                sorted(
                    list(title_words)[:8]
                )
            )
        )

        repositories = {}

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            for query in queries:

                try:

                    async with session.get(
                        self.API_URL,
                        params={
                            "q": query,
                            "sort": "stars",
                            "order": "desc",
                            "per_page": 20
                        }
                    ) as response:

                        if response.status != 200:
                            continue

                        data = await response.json()

                        for repository in data.get(
                            "items",
                            []
                        ):
                            name = repository.get(
                                "full_name"
                            )

                            if name:
                                repositories[
                                    name
                                ] = repository

                except (
                    aiohttp.ClientError,
                    asyncio.TimeoutError
                ):
                    continue

        return list(
            repositories.values()
        )

    async def discover(self, title):
        repositories = await self.search(
            title
        )

        if not repositories:
            return None

        ranked = []

        for repository in repositories:

            score = self.similarity(
                title,
                repository
            )

            ranked.append(
                (
                    score,
                    repository
                )
            )

        ranked.sort(
            key=lambda item: (
                item[0],
                item[1].get(
                    "stargazers_count",
                    0
                )
            ),
            reverse=True
        )

        best_score, best = ranked[0]

        if best_score < self.min_score:
            return None

        return {
            "github_url": best.get(
                "html_url"
            ),
            "github_stars": best.get(
                "stargazers_count"
            ),
            "repository": best.get(
                "full_name"
            ),
            "score": round(
                best_score,
                4
            )
        }


async def main():

    discovery = (
        GitHubRepositoryDiscovery()
    )

    title = (
        "Whisper: Robust Speech "
        "Recognition via Large-Scale "
        "Weak Supervision"
    )

    result = await discovery.discover(
        title
    )

    print(
        "\nGitHub Discovery Result"
    )

    print("=" * 60)

    print(
        "Paper:",
        title
    )

    print(
        "Result:",
        result
    )


if __name__ == "__main__":
    asyncio.run(main())
