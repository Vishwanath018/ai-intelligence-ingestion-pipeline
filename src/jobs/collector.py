import asyncio
from datetime import datetime, timezone

import aiohttp

from src.storage.output_manager import OutputManager


class JobCollector:

    BASE_URL = "https://www.arbeitnow.com/api/job-board-api"

    def __init__(self, max_results=1000):
        self.max_results = max_results

    async def fetch_page(
        self,
        session,
        page_number
    ):

        url = (
            f"{self.BASE_URL}"
            f"?page={page_number}"
        )

        async with session.get(
            url,
            timeout=60
        ) as response:

            response.raise_for_status()

            return await response.json()

    def detect_role_family(
        self,
        title
    ):

        value = title.lower()

        if (
            "machine learning" in value
            or "ml engineer" in value
            or "ai engineer" in value
            or "artificial intelligence" in value
        ):
            return "AI/ML"

        if (
            "data scientist" in value
            or "data science" in value
        ):
            return "Data Science"

        if "data engineer" in value:
            return "Data Engineering"

        if (
            "software engineer" in value
            or "software developer" in value
            or "backend" in value
            or "frontend" in value
            or "full stack" in value
            or "fullstack" in value
        ):
            return "Software Engineering"

        if (
            "devops" in value
            or "site reliability" in value
            or "sre" in value
        ):
            return "DevOps"

        if (
            "product manager" in value
            or "product management" in value
        ):
            return "Product"

        if (
            "designer" in value
            or "design" in value
        ):
            return "Design"

        if "marketing" in value:
            return "Marketing"

        if "sales" in value:
            return "Sales"

        if (
            "security" in value
            or "cybersecurity" in value
        ):
            return "Security"

        if (
            "qa" in value
            or "quality assurance" in value
            or "tester" in value
        ):
            return "Quality Assurance"

        return "Other"

    def parse_job(
        self,
        job
    ):

        if not isinstance(
            job,
            dict
        ):
            return None

        title = job.get(
            "title"
        )

        company = job.get(
            "company_name"
        )

        url = job.get(
            "url"
        )

        created_at = job.get(
            "created_at"
        )

        if not title:
            return None

        if not company:
            return None

        if not url:
            return None

        if not created_at:
            job_date = datetime.now(
                timezone.utc
            )
        else:

            try:

                job_date = datetime.fromtimestamp(
                    int(created_at),
                    tz=timezone.utc
                )

            except Exception:

                try:

                    job_date = datetime.fromisoformat(
                        str(created_at).replace(
                            "Z",
                            "+00:00"
                        )
                    )

                except Exception:

                    job_date = datetime.now(
                        timezone.utc
                    )

        remote = job.get(
            "remote"
        )

        if isinstance(
            remote,
            bool
        ):

            is_remote = remote

        else:

            description = str(
                job.get(
                    "description",
                    ""
                )
            ).lower()

            is_remote = (
                "remote" in description
                or "remote" in title.lower()
            )

        return {
            "schemaVersion": "1.0",
            "recordType": "JOB",
            "source": {
                "name": "Arbeitnow",
                "url": url
            },
            "content": {
                "company": company,
                "date": job_date,
                "is_remote": is_remote,
                "role_family": (
                    self.detect_role_family(
                        title
                    )
                )
            },
            "collectedAt": datetime.now(
                timezone.utc
            )
        }

    async def collect(self):

        records = []
        seen_urls = set()

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

            page_number = 1

            while (
                len(records)
                < self.max_results
            ):

                print(
                    f"Fetching jobs page "
                    f"{page_number}"
                )

                try:

                    data = await self.fetch_page(
                        session,
                        page_number
                    )

                except Exception as exc:

                    print(
                        f"Failed page "
                        f"{page_number}: "
                        f"{exc}"
                    )

                    break

                jobs = data.get(
                    "data",
                    []
                )

                if not jobs:

                    print(
                        "No more jobs returned."
                    )

                    break

                new_count = 0

                for job in jobs:

                    record = self.parse_job(
                        job
                    )

                    if record is None:
                        continue

                    url = record[
                        "source"
                    ][
                        "url"
                    ]

                    if url in seen_urls:
                        continue

                    seen_urls.add(
                        url
                    )

                    records.append(
                        record
                    )

                    new_count += 1

                    if (
                        len(records)
                        >= self.max_results
                    ):
                        break

                print(
                    f"New jobs: "
                    f"{new_count}"
                )

                print(
                    f"Total unique jobs: "
                    f"{len(records)}"
                )

                if new_count == 0:
                    break

                page_number += 1

                await asyncio.sleep(
                    1
                )

        return records[
            :self.max_results
        ]

    def validate(
        self,
        records
    ):

        urls = [
            record[
                "source"
            ][
                "url"
            ]
            for record in records
        ]

        invalid = []

        for record in records:

            if record.get(
                "recordType"
            ) != "JOB":

                invalid.append(
                    record
                )

                continue

            content = record.get(
                "content",
                {}
            )

            if not content.get(
                "company"
            ):

                invalid.append(
                    record
                )

                continue

            if not content.get(
                "date"
            ):

                invalid.append(
                    record
                )

                continue

            if not isinstance(
                content.get(
                    "is_remote"
                ),
                bool
            ):

                invalid.append(
                    record
                )

                continue

            if not content.get(
                "role_family"
            ):

                invalid.append(
                    record
                )

        print(
            "\nVALIDATION"
        )

        print(
            f"Records: {len(records)}"
        )

        print(
            f"Unique URLs: "
            f"{len(set(urls))}"
        )

        print(
            f"Duplicate URLs: "
            f"{len(urls) - len(set(urls))}"
        )

        print(
            f"Invalid records: "
            f"{len(invalid)}"
        )

        return (
            len(records) == self.max_results
            and len(set(urls)) == len(urls)
            and len(invalid) == 0
        )


async def main():

    print(
        "Starting job collection..."
    )

    collector = JobCollector(
        max_results=1000
    )

    records = await collector.collect()

    print(
        f"\nFINAL JOB COUNT: "
        f"{len(records)}"
    )

    if not collector.validate(
        records
    ):

        print(
            "\nValidation failed."
        )

        return

    output = OutputManager()

    path = output.save_json(
        "jobs.json",
        records
    )

    print(
        f"\nSaved jobs to: {path}"
    )

    print(
        "\nFirst record:"
    )

    print(
        records[0]
    )

    print(
        "\nLast record:"
    )

    print(
        records[-1]
    )


if __name__ == "__main__":
    asyncio.run(main())