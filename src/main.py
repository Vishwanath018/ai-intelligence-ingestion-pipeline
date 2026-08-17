import asyncio
from datetime import datetime, timezone

from src.crawler.async_crawler import AsyncCrawler
from src.entity_resolution.resolver import EntityResolver
from src.extractors.content_extractor import ContentExtractor
from src.freshness.validator import FreshnessValidator
from src.github.star_tracker import GitHubStarTracker
from src.llm.orchestrator import LLMOrchestrator
from src.storage.json_storage import JSONStorage


class IntelligencePipeline:

    def __init__(self):
        self.crawler = AsyncCrawler(concurrency=5)
        self.extractor = ContentExtractor()
        self.freshness = FreshnessValidator(max_age_hours=24)
        self.resolver = EntityResolver()
        self.github = GitHubStarTracker()
        self.llm = LLMOrchestrator(
            max_chars=12000,
            max_retries=3
        )
        self.storage = JSONStorage(
            output_dir="data/output"
        )

    async def process_source(self, result):

        if result.error:
            print(
                f"[ERROR] {result.url}: "
                f"{result.error}"
            )
            return None

        extracted = self.extractor.extract(
            result.text
        )

        llm_results = await self.llm.extract(
            extracted.text
        )

        record = {
            "source_url": result.url,
            "title": extracted.title,
            "description": extracted.description,
            "text_length": len(extracted.text),
            "published_date": extracted.published_date,
            "collected_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "llm_results": [
                {
                    "provider": response.provider,
                    "success": response.success,
                    "text": response.text,
                    "error": response.error,
                }
                for response in llm_results
            ],
        }

        return record

    async def run(self, urls: list[str]):

        print("Starting ingestion pipeline...")

        crawl_results = await self.crawler.crawl(
            urls
        )

        print(
            f"Crawled: {len(crawl_results)} URLs"
        )

        tasks = [
            self.process_source(result)
            for result in crawl_results
        ]

        processed = await asyncio.gather(
            *tasks
        )

        records = [
            record
            for record in processed
            if record is not None
        ]

        print(
            f"Successfully processed: "
            f"{len(records)} records"
        )

        output_path = self.storage.save(
            "pipeline_results.json",
            records
        )

        print(
            f"Saved output: {output_path}"
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
        print(
            f"\nSource: {record['source_url']}"
        )
        print(
            f"Title: {record['title']}"
        )
        print(
            f"Text length: {record['text_length']}"
        )
        print(
            f"LLM responses: "
            f"{len(record['llm_results'])}"
        )


if __name__ == "__main__":
    asyncio.run(main())