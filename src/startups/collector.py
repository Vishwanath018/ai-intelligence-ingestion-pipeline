import asyncio
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from src.storage.output_manager import OutputManager


class StartupCollector:

    BASE_URL = "https://www.ycombinator.com/companies"

    def __init__(self, max_results=1000):
        self.max_results = max_results

    async def collect(self):

        records = []
        seen = set()

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True
            )

            page = await browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 1000
                }
            )

            await page.goto(
                self.BASE_URL,
                wait_until="networkidle",
                timeout=60000
            )

            await page.wait_for_timeout(2000)

            previous_count = 0
            unchanged_rounds = 0

            while len(records) < self.max_results:

                links = page.locator(
                    'a[href^="/companies/"]'
                )

                count = await links.count()

                for i in range(count):

                    link = links.nth(i)

                    try:

                        href = await link.get_attribute(
                            "href"
                        )

                        if not href:
                            continue

                        parsed = urlparse(href)

                        parts = [
                            part
                            for part in parsed.path.split("/")
                            if part
                        ]

                        if (
                            len(parts) != 2
                            or parts[0] != "companies"
                        ):
                            continue

                        company_url = urljoin(
                            self.BASE_URL,
                            href
                        )

                        if company_url in seen:
                            continue

                        name = None

                        selectors = [
                            "h2",
                            "h3",
                            "[class*='company-name']",
                            "[class*='CompanyName']",
                        ]

                        for selector in selectors:

                            element = link.locator(
                                selector
                            )

                            if await element.count():

                                candidate = (
                                    await element.first.inner_text()
                                )

                                candidate = (
                                    " ".join(
                                        candidate.split()
                                    )
                                )

                                if candidate:
                                    name = candidate
                                    break

                        if not name:

                            text = await link.inner_text()

                            lines = [
                                line.strip()
                                for line in text.splitlines()
                                if line.strip()
                            ]

                            if lines:
                                name = lines[0]

                        if not name:
                            continue

                        location_markers = [
                            "San Francisco, CA, USA",
                            "New York City, NY, USA",
                            "Bengaluru, KA, India",
                            "Boston, MA, USA",
                            "Los Angeles, CA, USA",
                            "London, England, United Kingdom",
                            "Seattle, WA, USA",
                            "Austin, TX, USA",
                            "Chicago, IL, USA",
                            "Palo Alto, CA, USA",
                            "Toronto, Ontario, Canada",
                            "Mountain View, CA, USA",
                            "Cambridge, MA, USA",
                            "Redwood City, CA, USA",
                            "Sunnyvale, CA, USA",
                            "San Jose, CA, USA",
                            "Remote",
                        ]

                        for marker in location_markers:

                            if marker in name:

                                name = name.split(
                                    marker,
                                    1
                                )[0].strip()

                                break

                        if not name:
                            continue

                        seen.add(company_url)

                        records.append(
                            {
                                "schemaVersion": "1.0",
                                "recordType": "STARTUP",
                                "source": {
                                    "name": "Y Combinator",
                                    "url": company_url
                                },
                                "content": {
                                    "entityName": name,
                                    "data": {
                                        "employeeCount": None
                                    }
                                },
                                "collectedAt": (
                                    datetime.now(
                                        timezone.utc
                                    ).isoformat()
                                )
                            }
                        )

                        if len(records) >= self.max_results:
                            break

                    except Exception:
                        continue

                print(
                    f"Unique startups collected: "
                    f"{len(records)}"
                )

                if len(records) >= self.max_results:
                    break

                current_count = len(records)

                if current_count == previous_count:
                    unchanged_rounds += 1
                else:
                    unchanged_rounds = 0

                previous_count = current_count

                if unchanged_rounds >= 5:
                    break

                await page.evaluate(
                    """
                    window.scrollTo(
                        0,
                        document.body.scrollHeight
                    );
                    """
                )

                await page.wait_for_timeout(
                    2000
                )

            await browser.close()

        return records[:self.max_results]


async def main():

    print(
        "Starting startup collection..."
    )

    collector = StartupCollector(
        max_results=1000
    )

    records = await collector.collect()

    output = OutputManager()

    path = output.save_json(
        "startups.json",
        records
    )

    print(
        f"\nSaved startups to: {path}"
    )

    print(
        f"FINAL STARTUP COUNT: "
        f"{len(records)}"
    )

    if records:

        print(
            "\nFirst record:"
        )

        print(records[0])

        print(
            "\nLast record:"
        )

        print(records[-1])


if __name__ == "__main__":
    asyncio.run(main())