import asyncio
from datetime import datetime, timezone
from urllib.parse import quote

import aiohttp
import feedparser


class ArxivCollector:

    API_URL = "https://export.arxiv.org/api/query"

    def __init__(
        self,
        max_results=1000,
        concurrency=10,
    ):
        self.max_results = max_results
        self.concurrency = concurrency

    async def fetch(self, session, query, start):
        params = (
            f"?search_query={quote(query)}"
            f"&start={start}"
            f"&max_results=100"
            f"&sortBy=submittedDate"
            f"&sortOrder=descending"
        )

        url = self.API_URL + params

        async with session.get(url) as response:
            response.raise_for_status()
            return await response.text()

    def parse(self, content):
        feed = feedparser.parse(content)

        records = []

        for entry in feed.entries:
            github_url = None

            for link in entry.get(
                "links",
                [],
            ):
                href = link.get("href", "")

                if "github.com" in href.lower():
                    github_url = href
                    break

            published = entry.get(
                "published",
                None,
            )

            if published:
                published_date = datetime.fromisoformat(
                    published.replace(
                        "Z",
                        "+00:00",
                    )
                )
            else:
                published_date = None

            records.append(
                {
                    "schemaVersion": "1.0",
                    "recordType": "RESEARCH_PAPER",
                    "source": {
                        "name": "ArXiv",
                        "url": entry.get(
                            "id",
                            "",
                        ),
                    },
                    "content": {
                        "title": entry.get(
                            "title",
                            "",
                        ).strip(),
                        "authors": [
                            author.name
                            for author in entry.get(
                                "authors",
                                [],
                            )
                        ],
                        "paper_url": entry.get(
                            "id",
                            "",
                        ),
                        "github_url": github_url,
                        "github_stars": None,
                        "published_date": published_date,
                    },
                    "collectedAt": datetime.now(
                        timezone.utc
                    ),
                }
            )

        return records

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
                "User-Agent": (
                    "AI-Intelligence-"
                    "Ingestion-Pipeline/1.0"
                )
            },
        ) as session:

            tasks = []

            for start in range(
                0,
                self.max_results,
                100,
            ):
                tasks.append(
                    self.fetch(
                        session,
                        query,
                        start,
                    )
                )

            responses = await asyncio.gather(
                *tasks,
                return_exceptions=True,
            )

        for response in responses:
            if isinstance(response, Exception):
                continue

            records.extend(
                self.parse(response)
            )

        return records[:self.max_results]


async def main():
    collector = ArxivCollector(
        max_results=100
    )

    records = await collector.collect()

    print(
        f"Collected {len(records)} papers"
    )

    if records:
        first = records[0]

        print(
            first["content"]["title"]
        )

        print(
            first["content"]["paper_url"]
        )

        print(
            first["content"]["published_date"]
        )


if __name__ == "__main__":
    asyncio.run(main())