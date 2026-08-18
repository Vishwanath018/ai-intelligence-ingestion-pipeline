import asyncio
import re
from datetime import datetime, timezone
from urllib.parse import quote

import aiohttp
import feedparser

from src.github.repository_discovery import GitHubRepositoryDiscovery
from src.github.star_tracker import GitHubStarTracker
from src.storage.output_manager import OutputManager


class ArxivCollector:

    API_URL = "https://export.arxiv.org/api/query"

    GITHUB_PATTERN = re.compile(
        r"https?://github\.com/[^/\s<>\"']+/[^/\s<>\"']+",
        re.IGNORECASE
    )

    def __init__(
        self,
        max_results=1000,
        enable_github_discovery=True
    ):
        self.max_results = max_results
        self.github = GitHubStarTracker()
        self.discovery = GitHubRepositoryDiscovery()
        self.enable_github_discovery = (
            enable_github_discovery
        )

    async def fetch(
        self,
        session,
        query,
        start,
    ):
        params = (
            f"?search_query={quote(query)}"
            f"&start={start}"
            f"&max_results=100"
            f"&sortBy=submittedDate"
            f"&sortOrder=descending"
        )

        url = self.API_URL + params

        for attempt in range(3):

            try:

                async with session.get(
                    url
                ) as response:

                    if response.status == 429:

                        await asyncio.sleep(
                            2 ** attempt
                        )

                        continue

                    response.raise_for_status()

                    return await response.text()

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ):

                if attempt == 2:
                    return None

                await asyncio.sleep(
                    2 ** attempt
                )

        return None

    def extract_explicit_github_url(
        self,
        entry
    ):

        candidates = []

        for link in entry.get(
            "links",
            []
        ):

            href = link.get(
                "href",
                ""
            )

            if href:
                candidates.append(href)

        candidates.extend([
            entry.get("summary", ""),
            entry.get("comment", ""),
            entry.get("journal_ref", ""),
        ])

        for candidate in candidates:

            matches = (
                self.GITHUB_PATTERN.findall(
                    candidate
                )
            )

            if matches:

                return matches[0].rstrip(
                    ".,);]}"
                )

        return None

    def parse(
        self,
        content
    ):

        feed = feedparser.parse(
            content
        )

        records = []

        for entry in feed.entries:

            published = entry.get(
                "published"
            )

            published_date = None

            if published:

                try:

                    published_date = (
                        datetime.fromisoformat(
                            published.replace(
                                "Z",
                                "+00:00"
                            )
                        )
                    )

                except ValueError:
                    published_date = None

            paper_url = entry.get(
                "id",
                ""
            )

            title = entry.get(
                "title",
                ""
            ).strip()

            authors = [
                author.name
                for author in entry.get(
                    "authors",
                    []
                )
            ]

            if not paper_url:
                continue

            if not title:
                continue

            if published_date is None:
                continue

            github_url = (
                self.extract_explicit_github_url(
                    entry
                )
            )

            records.append(
                {
                    "schemaVersion": "1.0",
                    "recordType": "RESEARCH_PAPER",
                    "source": {
                        "name": "ArXiv",
                        "url": paper_url
                    },
                    "content": {
                        "title": title,
                        "authors": authors,
                        "paper_url": paper_url,
                        "github_url": github_url,
                        "github_stars": None,
                        "published_date": published_date
                    },
                    "collectedAt": datetime.now(
                        timezone.utc
                    )
                }
            )

        return records

    async def discover_github(
        self,
        records
    ):

        semaphore = asyncio.Semaphore(3)

        async def enrich(
            record
        ):

            content = record[
                "content"
            ]

            github_url = content.get(
                "github_url"
            )

            if not github_url:

                if not self.enable_github_discovery:
                    return record

                async with semaphore:

                    try:

                        result = (
                            await self.discovery.discover(
                                content[
                                    "title"
                                ]
                            )
                        )

                        if result:

                            github_url = result.get(
                                "github_url"
                            )

                            if github_url:

                                content[
                                    "github_url"
                                ] = github_url

                                content[
                                    "github_stars"
                                ] = result.get(
                                    "github_stars"
                                )

                                return record

                    except Exception:
                        pass

                return record

            async with semaphore:

                try:

                    stars = await (
                        self.github.get_stars(
                            github_url
                        )
                    )

                    content[
                        "github_stars"
                    ] = stars

                except Exception:
                    content[
                        "github_stars"
                    ] = None

            return record

        return await asyncio.gather(
            *[
                enrich(record)
                for record in records
            ]
        )

    async def collect(
        self,
        query="cat:cs.AI"
    ):

        records = []

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        headers = {
            "User-Agent":
                "AI-Intelligence-Ingestion-Pipeline/1.0"
        }

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers
        ) as session:

            for start in range(
                0,
                self.max_results,
                100
            ):

                end = min(
                    start + 100,
                    self.max_results
                )

                print(
                    f"Fetching papers "
                    f"{start + 1}-{end}"
                )

                content = await self.fetch(
                    session,
                    query,
                    start
                )

                if content:

                    records.extend(
                        self.parse(
                            content
                        )
                    )

                await asyncio.sleep(
                    1
                )

        unique = {}

        for record in records:

            url = record[
                "content"
            ][
                "paper_url"
            ]

            unique[url] = record

        records = list(
            unique.values()
        )[
            :self.max_results
        ]

        print(
            f"Unique papers: "
            f"{len(records)}"
        )

        records = await (
            self.discover_github(
                records
            )
        )

        return records

    def validate(
        self,
        records
    ):

        urls = [
            record[
                "content"
            ][
                "paper_url"
            ]
            for record in records
        ]

        invalid_records = []

        for record in records:

            if (
                record.get(
                    "recordType"
                ) != "RESEARCH_PAPER"
            ):

                invalid_records.append(
                    record
                )

                continue

            content = record.get(
                "content",
                {}
            )

            if not content.get(
                "title"
            ):

                invalid_records.append(
                    record
                )

                continue

            if not content.get(
                "authors"
            ):

                invalid_records.append(
                    record
                )

                continue

            if not content.get(
                "paper_url"
            ):

                invalid_records.append(
                    record
                )

                continue

            if not content.get(
                "published_date"
            ):

                invalid_records.append(
                    record
                )

        github_urls = sum(
            1
            for record in records
            if record[
                "content"
            ].get(
                "github_url"
            )
        )

        github_stars = sum(
            1
            for record in records
            if record[
                "content"
            ].get(
                "github_stars"
            ) is not None
        )

        print(
            "\nVALIDATION"
        )

        print(
            f"Records: {len(records)}"
        )

        print(
            f"Unique paper URLs: "
            f"{len(set(urls))}"
        )

        print(
            f"GitHub URLs: "
            f"{github_urls}"
        )

        print(
            f"GitHub stars collected: "
            f"{github_stars}"
        )

        print(
            f"Invalid records: "
            f"{len(invalid_records)}"
        )

        return (
            len(records) == self.max_results
            and len(set(urls)) == len(urls)
            and len(invalid_records) == 0
        )


async def main():

    print(
        "Starting research paper collection..."
    )

    collector = ArxivCollector(
        max_results=20
    )

    records = await collector.collect(
        query="cat:cs.AI"
    )

    valid = collector.validate(
        records
    )

    print(
        f"\nValidation result: "
        f"{valid}"
    )

    if records:

        github_records = [
            record
            for record in records
            if record[
                "content"
            ].get(
                "github_url"
            )
        ]

        print(
            "\nGitHub-enriched papers:"
        )

        for record in github_records[:10]:

            content = record[
                "content"
            ]

            print(
                "\nTitle:",
                content["title"]
            )

            print(
                "GitHub:",
                content["github_url"]
            )

            print(
                "Stars:",
                content["github_stars"]
            )


if __name__ == "__main__":
    asyncio.run(main())
