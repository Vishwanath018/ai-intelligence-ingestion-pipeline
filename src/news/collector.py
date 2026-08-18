import asyncio
import re
from datetime import datetime, timezone

import aiohttp

from src.storage.output_manager import OutputManager


class NewsCollector:

    BASE_URL = "https://api.gdeltproject.org/api/v2/doc/doc"

    QUERIES = [
        "artificial intelligence",
        "technology",
        "software",
        "data science",
        "machine learning",
        "startups",
        "business",
        "finance",
        "cybersecurity",
        "cloud computing",
        "robotics",
        "science",
        "healthcare",
        "education",
        "electric vehicles",
        "space",
        "semiconductors",
        "renewable energy",
        "economy",
        "innovation",
    ]

    def __init__(self, max_results=1000):
        self.max_results = max_results

    @staticmethod
    def clean_url(url):

        if not url:
            return ""

        url = str(url).strip()

        markdown = re.match(
            r"^\[.*?\]\((https?://[^)]+)\)$",
            url
        )

        if markdown:
            return markdown.group(1)

        if url.startswith("<") and url.endswith(">"):
            url = url[1:-1].strip()

        return url

    @staticmethod
    def clean_text(text):

        if not text:
            return ""

        text = re.sub(
            r"\s+",
            " ",
            str(text)
        )

        return text.strip()

    async def fetch(
        self,
        session,
        query
    ):

        params = {
            "query": query,
            "mode": "artlist",
            "maxrecords": 250,
            "format": "json",
            "timespan": "3months",
            "sort": "datedesc",
        }

        for attempt in range(6):

            try:

                async with session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=90
                ) as response:

                    if response.status == 429:

                        wait_time = 10 * (
                            attempt + 1
                        )

                        print(
                            f"Rate limited. "
                            f"Waiting {wait_time}s..."
                        )

                        await asyncio.sleep(
                            wait_time
                        )

                        continue

                    response.raise_for_status()

                    return await response.json()

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError
            ) as exc:

                if attempt == 5:

                    print(
                        f"Request failed: {exc}"
                    )

                    return None

                wait_time = 5 * (
                    attempt + 1
                )

                print(
                    f"Request error. "
                    f"Retrying in {wait_time}s..."
                )

                await asyncio.sleep(
                    wait_time
                )

        return None

    def parse_article(self, article):

        title = self.clean_text(
            article.get("title", "")
        )

        url = self.clean_url(
            article.get("url", "")
        )

        domain = self.clean_text(
            article.get(
                "domain",
                "GDELT"
            )
        )

        date_value = article.get(
            "seendate",
            ""
        )

        if not title or not url:
            return None

        if not url.startswith(
            ("http://", "https://")
        ):
            return None

        published_date = None

        if date_value:

            try:

                published_date = (
                    datetime.strptime(
                        date_value,
                        "%Y%m%dT%H%M%SZ"
                    ).replace(
                        tzinfo=timezone.utc
                    )
                )

            except ValueError:

                try:

                    published_date = (
                        datetime.strptime(
                            date_value,
                            "%Y%m%dT%H%M%S"
                        ).replace(
                            tzinfo=timezone.utc
                        )
                    )

                except ValueError:
                    pass

        if published_date is None:

            published_date = datetime.now(
                timezone.utc
            )

        text = self.clean_text(
            article.get(
                "snippet",
                ""
            )
        )

        if not text:
            text = title

        return {
            "schemaVersion": "1.0",
            "recordType": "NEWS",
            "source": {
                "name": domain,
                "url": url
            },
            "content": {
                "title": title,
                "date": published_date,
                "text": text,
                "url": url
            },
            "collectedAt": datetime.now(
                timezone.utc
            )
        }

    async def collect(self):

        records = []
        seen_urls = set()

        timeout = aiohttp.ClientTimeout(
            total=90
        )

        headers = {
            "User-Agent":
                "AI-Intelligence-Ingestion-Pipeline/1.0"
        }

        connector = aiohttp.TCPConnector(
            limit=1
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector
        ) as session:

            for query in self.QUERIES:

                if len(records) >= self.max_results:
                    break

                print(
                    f"\nFetching news: {query}"
                )

                data = await self.fetch(
                    session,
                    query
                )

                if data is None:
                    continue

                articles = data.get(
                    "articles",
                    []
                )

                new_count = 0

                for article in articles:

                    record = self.parse_article(
                        article
                    )

                    if record is None:
                        continue

                    url = record[
                        "content"
                    ][
                        "url"
                    ]

                    if url in seen_urls:
                        continue

                    seen_urls.add(url)
                    records.append(record)
                    new_count += 1

                    if len(records) >= self.max_results:
                        break

                print(
                    f"New articles: {new_count}"
                )

                print(
                    f"Total unique news: "
                    f"{len(records)}"
                )

                await asyncio.sleep(8)

        return records[:self.max_results]

    def validate(self, records):

        urls = [
            record[
                "content"
            ][
                "url"
            ]
            for record in records
        ]

        invalid = []

        for record in records:

            content = record.get(
                "content",
                {}
            )

            url = content.get(
                "url",
                ""
            )

            if (
                record.get("recordType")
                != "NEWS"
            ):
                invalid.append(record)
                continue

            if not content.get("title"):
                invalid.append(record)
                continue

            if not content.get("date"):
                invalid.append(record)
                continue

            if not content.get("text"):
                invalid.append(record)
                continue

            if not url.startswith(
                ("http://", "https://")
            ):
                invalid.append(record)
                continue

            if re.match(
                r"^\[.*?\]\(https?://",
                url
            ):
                invalid.append(record)

        print("\nVALIDATION")
        print(f"Records: {len(records)}")
        print(
            f"Unique URLs: {len(set(urls))}"
        )
        print(
            f"Duplicate URLs: "
            f"{len(urls) - len(set(urls))}"
        )
        print(
            f"Invalid records: {len(invalid)}"
        )

        return (
            len(records) == self.max_results
            and len(set(urls)) == len(urls)
            and len(invalid) == 0
        )


async def main():

    print(
        "Starting news collection..."
    )

    collector = NewsCollector(
        max_results=1000
    )

    records = await collector.collect()

    print(
        f"\nFINAL NEWS COUNT: "
        f"{len(records)}"
    )

    if not collector.validate(records):

        print(
            "\nValidation failed."
        )

        return

    output = OutputManager()

    path = output.save_json(
        "news.json",
        records
    )

    print(
        f"\nSaved news to: {path}"
    )

    print("\nFirst record:")
    print(records[0])

    print("\nLast record:")
    print(records[-1])


if __name__ == "__main__":
    asyncio.run(main())