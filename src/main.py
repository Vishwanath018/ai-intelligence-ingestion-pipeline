import asyncio
from datetime import datetime, timezone

from src.crawler.async_crawler import AsyncCrawler
from src.extractors.content_extractor import ContentExtractor
from src.freshness.validator import FreshnessValidator
from src.entity_resolution.resolver import EntityResolver
from src.github.star_tracker import GitHubStarTracker
from src.storage.json_storage import JSONStorage


class IntelligencePipeline:

    def __init__(self):
        self.crawler = AsyncCrawler(concurrency=5)
        self.extractor = ContentExtractor()
        self.freshness = FreshnessValidator()
        self.resolver = EntityResolver()
        self.github = GitHubStarTracker()
        self.storage = JSONStorage()

    async def run(self, urls: list[str]):

        print("Starting ingestion pipeline...")

        # 1. Crawl sources asynchronously
        crawl_results = await self.crawler.crawl(urls)

        print(f"Crawled: {len(crawl_results)} URLs")

        records = []

        # 2. Process every crawled source
        for result in crawl_results:

            if result.error:
                print(
                    f"[ERROR] {result.url}: "
                    f"{result.error}"
                )
                continue

            # 3. Extract content
            extracted = self.extractor.extract(
                result.text
            )

            # 4. Build normalized pipeline record
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

        # 5. Persist results
        output_path = self.storage.save(
            "pipeline_results.json",
            records,
        )

        print(
            f"Saved output: {output_path}"
        )

        return records


async def main():

    pipeline = IntelligencePipeline()

    # Test URLs.
    # These will later be replaced by the
    # actual configured source URLs.
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