import json
from pathlib import Path
from typing import Any


class JSONStorage:
    def __init__(self, output_dir: str = "data/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def save(
        self,
        filename: str,
        records: list[dict[str, Any]],
    ) -> Path:

        path = self.output_dir / filename

        with path.open(
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                records,
                file,
                indent=2,
                ensure_ascii=False,
            )

        return path