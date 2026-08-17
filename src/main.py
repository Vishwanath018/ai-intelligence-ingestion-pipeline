import asyncio
from datetime import datetime, timezone

from src.crawler.async_crawler import AsyncCrawler
from src.extractors.content_extractor import ContentExtractor
from src.freshness.validator import FreshnessValidator
from src.entity_resolution.resolver import EntityResolver
from src.github.star_tracker import GitHubStarTracker


class IntelligencePipeline:

    def __init__(self):
        self.crawler = AsyncCrawler(concurrency=5)
        self.extractor = ContentExtractor()
        self.freshness = FreshnessValidator()
        self.resolver = EntityResolver()
        self.github = GitHubStarTracker()

    async def run(self, urls: list[str]):

        print("Starting ingestion pipeline...")

        # 1. Crawl
        crawl_results = await self.crawler.crawl(urls)

        print(f"Crawled: {len(crawl_results)} URLs")

        records = []

        for result in crawl_results:

            if result.error:
                print(
                    f"[ERROR] {result.url}: "
                    f"{result.error}"
                )
                continue

            # 2. Extract
            extracted = self.extractor.extract(
                result.text
            )

            # 3. Display source information
            record = {
                "source_url": result.url,
                "title": extracted.title,
                "text_length": len(extracted.text),
                "published_date": extracted.published_date,
                "collected_at": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            records.append(record)

        print(
            f"Successfully processed: "
            f"{len(records)} records"
        )

        return records


async def main():

    pipeline = IntelligencePipeline()

    urls = [
        "https://example.com",
        "https://www.python.org",
    ]

    records = await pipeline.run(urls)

    print("\nPipeline results:")

    for record in records:
        print(record)


if __name__ == "__main__":
    asyncio.run(main())
