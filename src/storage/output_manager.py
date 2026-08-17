import json
from pathlib import Path


class OutputManager:

    def __init__(self, output_dir="data/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True
        )

    def save_json(self, filename, records):
        path = self.output_dir / filename

        with path.open(
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                records,
                file,
                indent=2,
                ensure_ascii=False,
                default=str
            )

        return path

    def save_all(
        self,
        startups,
        products,
        research_papers,
        jobs,
        news,
        entity_mapping
    ):
        return {
            "startups": self.save_json(
                "startups.json",
                startups
            ),
            "products": self.save_json(
                "products.json",
                products
            ),
            "research_papers": self.save_json(
                "research_papers.json",
                research_papers
            ),
            "jobs": self.save_json(
                "jobs.json",
                jobs
            ),
            "news": self.save_json(
                "news.json",
                news
            ),
            "entity_mapping": self.save_json(
                "entity_mapping_log.json",
                entity_mapping
            )
        }