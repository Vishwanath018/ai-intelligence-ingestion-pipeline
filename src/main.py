import argparse
import asyncio
import time

from src.jobs.collector import JobCollector
from src.news.collector import NewsCollector
from src.products.collector import ProductCollector
from src.research.arxiv_collector import ArxivCollector
from src.startups.collector import StartupCollector
from src.storage.output_manager import OutputManager
from src.entity_resolution.resolver import EntityResolver


class IntelligenceIngestionPipeline:

    def __init__(self, max_results):
        self.max_results = max_results
        self.output = OutputManager()
        self.entity_resolver = EntityResolver()
        self.results = {}
        self.status = {}
        self.entity_mappings = []

    async def run_source(
        self,
        name,
        collector_factory,
        validator=True
    ):
        print("\n" + "=" * 60)
        print(f"SOURCE - {name.upper()}")
        print("=" * 60)

        try:
            collector = collector_factory()
            records = await collector.collect()

            if (
                validator
                and hasattr(collector, "validate")
            ):
                valid = collector.validate(records)
            else:
                valid = True

            self.results[name] = records

            self.status[name] = (
                "SUCCESS"
                if valid
                else "VALIDATION_FAILED"
            )

            print(
                f"{name.title()} records collected: "
                f"{len(records)}"
            )

            return records

        except Exception as exc:

            self.results[name] = []
            self.status[name] = f"FAILED: {exc}"

            print(
                f"{name.title()} failed: {exc}"
            )

            return []

    async def run_news(self):

        print("\n" + "=" * 60)
        print("SOURCE - NEWS")
        print("=" * 60)

        try:

            collector = NewsCollector(
                max_results=self.max_results
            )

            records = await asyncio.wait_for(
                collector.collect(),
                timeout=60
            )

            valid = (
                collector.validate(records)
                if hasattr(collector, "validate")
                else True
            )

            self.results["news"] = (
                records if valid else []
            )

            self.status["news"] = (
                "SUCCESS"
                if valid
                else "VALIDATION_FAILED"
            )

            print(
                f"News records collected: "
                f"{len(records)}"
            )

            return records

        except asyncio.TimeoutError:

            self.results["news"] = []
            self.status["news"] = "TIMEOUT"

            print(
                "News source timed out."
            )

            return []

        except Exception as exc:

            self.results["news"] = []
            self.status["news"] = (
                f"FAILED: {exc}"
            )

            print(
                f"News source unavailable: {exc}"
            )

            return []

    def extract_live_startups(self):

        names = []

        for record in self.results.get(
            "startups",
            []
        ):

            content = record.get(
                "content",
                {}
            )

            name = content.get(
                "entityName"
            )

            if name:
                names.append(name)

        return list(dict.fromkeys(names))

    def register_live_entities(self):

        print("\n" + "=" * 70)
        print("LIVE ENTITY REGISTRATION")
        print("=" * 70)

        startups = (
            self.extract_live_startups()
        )

        self.entity_resolver.register_entities(
            startups
        )

        print(
            f"Live canonical entities: "
            f"{len(startups)}"
        )

        for name in startups:
            print(
                f"  + {name}"
            )

        return startups

    def extract_entity_candidates(self):

        candidates = []

        for record in self.results.get(
            "startups",
            []
        ):

            content = record.get(
                "content",
                {}
            )

            name = content.get(
                "entityName"
            )

            if name:

                candidates.append({
                    "raw_name": name,
                    "entity_type": "STARTUP",
                    "source_url": str(
                        record[
                            "source"
                        ][
                            "url"
                        ]
                    )
                })

        for record in self.results.get(
            "products",
            []
        ):

            content = record.get(
                "content",
                {}
            )

            startup_name = content.get(
                "startupName"
            )

            if startup_name:

                candidates.append({
                    "raw_name": startup_name,
                    "entity_type": "STARTUP",
                    "source_url": str(
                        record[
                            "source"
                        ][
                            "url"
                        ]
                    )
                })

        for record in self.results.get(
            "jobs",
            []
        ):

            content = record.get(
                "content",
                {}
            )

            company = content.get(
                "company"
            )

            if company:

                candidates.append({
                    "raw_name": company,
                    "entity_type": "STARTUP",
                    "source_url": str(
                        record[
                            "source"
                        ][
                            "url"
                        ]
                    )
                })

        return candidates

    def resolve_entities(self):

        print("\n" + "=" * 70)
        print("ENTITY RESOLUTION")
        print("=" * 70)

        candidates = (
            self.extract_entity_candidates()
        )

        if not candidates:

            print(
                "No entity candidates found."
            )

            self.entity_mappings = []

            return []

        mappings = []
        seen = set()

        for candidate in candidates:

            raw_name = candidate[
                "raw_name"
            ]

            entity_type = candidate[
                "entity_type"
            ]

            key = (
                raw_name.lower(),
                entity_type
            )

            if key in seen:
                continue

            seen.add(key)

            result = (
                self.entity_resolver.resolve(
                    raw_name
                )
            )

            mappings.append({
                "raw_name": result.raw_name,
                "canonical_name": (
                    result.canonical_name
                ),
                "entity_type": entity_type,
                "confidence": result.confidence,
                "source_url": (
                    candidate["source_url"]
                ),
                "matched": result.matched
            })

        self.entity_mappings = mappings

        print(
            f"Entity candidates: "
            f"{len(candidates)}"
        )

        print(
            f"Unique entities resolved: "
            f"{len(mappings)}"
        )

        print("\nRESOLUTION RESULTS")
        print("-" * 70)

        for mapping in mappings:

            print(
                f"{mapping['raw_name']}"
                f" -> "
                f"{mapping['canonical_name']}"
                f" | "
                f"{mapping['confidence']:.2f}"
                f" | "
                f"{mapping['entity_type']}"
            )

        matched_count = sum(
            1
            for mapping in mappings
            if mapping["matched"]
        )

        print("-" * 70)

        print(
            f"Matched canonical entities: "
            f"{matched_count}"
        )

        print(
            f"Unmatched entities: "
            f"{len(mappings) - matched_count}"
        )

        return mappings

    def save_outputs(self):

        print("\n" + "=" * 70)
        print("PERSISTING PIPELINE OUTPUT")
        print("=" * 70)

        paths = self.output.save_all(
            startups=self.results.get(
                "startups",
                []
            ),
            products=self.results.get(
                "products",
                []
            ),
            research_papers=self.results.get(
                "research",
                []
            ),
            jobs=self.results.get(
                "jobs",
                []
            ),
            news=self.results.get(
                "news",
                []
            ),
            entity_mapping=self.entity_mappings
        )

        for name, path in paths.items():

            print(
                f"{name}: {path}"
            )

        unified_records = []

        for source_name in [
            "startups",
            "products",
            "research",
            "jobs",
            "news"
        ]:

            unified_records.extend(
                self.results.get(
                    source_name,
                    []
                )
            )

        print(
            f"Unified records saved: "
            f"{len(unified_records)}"
        )

        return paths

    async def run(self):

        started = time.time()

        print("\n")
        print("=" * 70)
        print(
            "AI INTELLIGENCE INGESTION PIPELINE"
        )
        print("=" * 70)

        print(
            f"Collection target per source: "
            f"{self.max_results}"
        )

        print(
            "Mode: REAL-TIME DATA INGESTION"
        )

        print("=" * 70)

        await self.run_source(
            "startups",
            lambda: StartupCollector(
                max_results=self.max_results
            )
        )

        await self.run_source(
            "products",
            lambda: ProductCollector(
                max_results=self.max_results
            )
        )

        await self.run_source(
            "research",
            lambda: ArxivCollector(
                max_results=self.max_results
            )
        )

        await self.run_source(
            "jobs",
            lambda: JobCollector(
                max_results=self.max_results
            )
        )

        await self.run_news()

        self.register_live_entities()

        self.resolve_entities()

        self.save_outputs()

        print("\n" + "=" * 70)
        print("PIPELINE SUMMARY")
        print("=" * 70)

        total = 0

        for name in [
            "startups",
            "products",
            "research",
            "jobs",
            "news"
        ]:

            records = self.results.get(
                name,
                []
            )

            status = self.status.get(
                name,
                "NOT_RUN"
            )

            print(
                f"{name.title():15}"
                f"{len(records):5} "
                f"{status}"
            )

            total += len(records)

        print("-" * 70)

        print(
            f"TOTAL RECORDS: {total}"
        )

        print(
            f"ENTITY MAPPINGS: "
            f"{len(self.entity_mappings)}"
        )

        elapsed = time.time() - started

        print(
            f"RUNTIME: "
            f"{elapsed:.2f} seconds"
        )

        failed = [
            name
            for name, status
            in self.status.items()
            if status != "SUCCESS"
        ]

        if failed:

            print(
                "\nPipeline completed with "
                "source warnings:"
            )

            for name in failed:

                print(
                    f" - {name}: "
                    f"{self.status[name]}"
                )

        else:

            print(
                "\nPipeline completed successfully."
            )

        print("=" * 70)

        return self.results


def parse_args():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=[
            "live",
            "full"
        ],
        default="live"
    )

    return parser.parse_args()


async def main():

    args = parse_args()

    max_results = (
        5
        if args.mode == "live"
        else 1000
    )

    pipeline = IntelligenceIngestionPipeline(
        max_results=max_results
    )

    await pipeline.run()


if __name__ == "__main__":

    asyncio.run(main())
