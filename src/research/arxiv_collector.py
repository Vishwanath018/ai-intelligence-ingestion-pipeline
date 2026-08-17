import asyncio
from datetime import datetime, timezone
from urllib.parse import quote

import aiohttp
import feedparser

from src.github.star_tracker import GitHubStarTracker


class ArxivCollector:

    API_URL = "https://export.arxiv.org/api/query"

    def __init__(
        self,
        max_results=1000,
    ):
        self.max_results = max_results
        self.github = GitHubStarTracker()

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

    def parse(self, content):

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

            github_url = None

            for link in entry.get(
                "links",
                []
            ):
                href = link.get(
                    "href",
                    ""
                )

                if "github.com" in href.lower():
                    github_url = href
                    break

            record = {
                "schemaVersion": "1.0",
                "recordType": "RESEARCH_PAPER",
                "source": {
                    "name": "ArXiv",
                    "url": entry.get(
                        "id",
                        ""
                    )
                },
                "content": {
                    "title": entry.get(
                        "title",
                        ""
                    ).strip(),
                    "authors": [
                        author.name
                        for author in entry.get(
                            "authors",
                            []
                        )
                    ],
                    "paper_url": entry.get(
                        "id",
                        ""
                    ),
                    "github_url": github_url,
                    "github_stars": None,
                    "published_date": published_date,
                },
                "collectedAt": datetime.now(
                    timezone.utc
                )
            }

            records.append(record)

        return records

    async def enrich_github_stars(
        self,
        records,
    ):

        semaphore = asyncio.Semaphore(5)

        async def enrich(record):

            github_url = record[
                "content"
            ]["github_url"]

            if not github_url:
                return record

            async with semaphore:

                stars = await (
                    self.github.get_stars(
                        github_url
                    )
                )

                record[
                    "content"
                ]["github_stars"] = stars

            return record

        return await asyncio.gather(
            *[
                enrich(record)
                for record in records
            ]
        )

    async def collect(
        self,
        query="cat:cs.AI",
    ):

        records = []

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers={
                "User-Agent":
                    "AI-Intelligence-"
                    "Ingestion-Pipeline/1.0"
            }
        ) as session:

            for start in range(
                0,
                self.max_results,
                100
            ):

                print(
                    f"Fetching papers "
                    f"{start + 1}-"
                    f"{min(start + 100, self.max_results)}"
                )

                content = await self.fetch(
                    session,
                    query,
                    start,
                )

                if content:
                    records.extend(
                        self.parse(content)
                    )

                await asyncio.sleep(1)

        unique = {}

        for record in records:

            url = record[
                "content"
            ]["paper_url"]

            unique[url] = record

        records = list(
            unique.values()
        )[:self.max_results]

        print(
            f"Unique papers: {len(records)}"
        )

        records = await (
            self.enrich_github_stars(
                records
            )
        )

        return records


async def main():

    collector = ArxivCollector(
        max_results=1000
    )

    records = await collector.collect()

    print(
        f"Collected {len(records)} research papers"
    )

    if records:

        print(
            records[0]
        )


if __name__ == "__main__":
    asyncio.run(main())