import asyncio
from datetime import datetime, timezone
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from src.storage.output_manager import OutputManager


class ProductCollector:

    BASE_URL = "https://findaitool.com/ai-tools"

    def __init__(self, max_results=1000):
        self.max_results = max_results

    async def extract_products(self, page):

        records = []

        cards = page.locator(
            'a[href^="/tool/"]'
        )

        count = await cards.count()

        for i in range(count):

            try:

                card = cards.nth(i)

                href = await card.get_attribute(
                    "href"
                )

                if not href:
                    continue

                source_url = urljoin(
                    self.BASE_URL,
                    href
                )

                name_element = card.locator(
                    "h3"
                )

                if await name_element.count() == 0:
                    continue

                product_name = await name_element.first.inner_text()

                product_name = " ".join(
                    product_name.split()
                )

                if not product_name:
                    continue

                card_text = await card.inner_text()

                pricing_model = None

                lower_text = card_text.lower()

                if "freemium" in lower_text:
                    pricing_model = "Freemium"
                elif "free" in lower_text:
                    pricing_model = "Free"
                elif "paid" in lower_text:
                    pricing_model = "Paid"

                records.append(
                    {
                        "schemaVersion": "1.0",
                        "recordType": "PRODUCT",
                        "source": {
                            "name": "FindAITool",
                            "url": source_url
                        },
                        "content": {
                            "startupName": None,
                            "productName": product_name,
                            "pricingModel": pricing_model
                        },
                        "collectedAt": (
                            datetime.now(
                                timezone.utc
                            ).isoformat()
                        )
                    }
                )

            except Exception:
                continue

        return records

    async def get_tool_urls(self, page):

        return await page.locator(
            'a[href^="/tool/"]'
        ).evaluate_all(
            """
            elements => elements.map(
                element => element.href
            )
            """
        )

    async def click_next(self, page):

        next_locators = [
            page.get_by_role(
                "button",
                name="Next",
                exact=True
            ),
            page.get_by_text(
                "Next",
                exact=True
            )
        ]

        for locator in next_locators:

            try:

                count = await locator.count()

                if count == 0:
                    continue

                next_button = locator.last

                try:

                    if await next_button.is_disabled():
                        return False

                except Exception:
                    pass

                old_urls = set(
                    await self.get_tool_urls(
                        page
                    )
                )

                await next_button.scroll_into_view_if_needed()

                await next_button.click(
                    timeout=10000
                )

                for _ in range(20):

                    await page.wait_for_timeout(
                        500
                    )

                    new_urls = set(
                        await self.get_tool_urls(
                            page
                        )
                    )

                    if new_urls != old_urls:
                        return True

                return False

            except Exception:
                continue

        return False

    async def collect(self):

        records = []
        seen_urls = set()
        visited_page_signatures = set()

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

            await page.wait_for_timeout(
                1500
            )

            page_number = 1

            while len(records) < self.max_results:

                current_urls = set(
                    await self.get_tool_urls(
                        page
                    )
                )

                signature = tuple(
                    sorted(current_urls)
                )

                if signature in visited_page_signatures:

                    print(
                        "Page already visited. "
                        "Stopping."
                    )

                    break

                visited_page_signatures.add(
                    signature
                )

                page_records = (
                    await self.extract_products(
                        page
                    )
                )

                new_records = 0

                for record in page_records:

                    source_url = record[
                        "source"
                    ]["url"]

                    if source_url in seen_urls:
                        continue

                    seen_urls.add(
                        source_url
                    )

                    records.append(
                        record
                    )

                    new_records += 1

                    if (
                        len(records)
                        >= self.max_results
                    ):
                        break

                print(
                    f"Page {page_number}: "
                    f"{new_records} new products"
                )

                print(
                    f"Total unique products: "
                    f"{len(records)}"
                )

                if len(records) >= self.max_results:
                    break

                if not current_urls:

                    print(
                        "No product URLs found."
                    )

                    break

                moved = await self.click_next(
                    page
                )

                if not moved:

                    print(
                        "No new page available."
                    )

                    break

                page_number += 1

            await browser.close()

        return records[:self.max_results]

    def validate(self, records):

        urls = [
            record["source"]["url"]
            for record in records
        ]

        names = [
            record["content"]["productName"]
            for record in records
        ]

        invalid_urls = [
            url
            for url in urls
            if not url.startswith(
                "https://findaitool.com/tool/"
            )
        ]

        duplicate_urls = (
            len(urls) - len(set(urls))
        )

        empty_names = [
            name
            for name in names
            if not name
        ]

        print(
            "\nVALIDATION"
        )

        print(
            f"Records: {len(records)}"
        )

        print(
            f"Unique URLs: {len(set(urls))}"
        )

        print(
            f"Duplicate URLs: {duplicate_urls}"
        )

        print(
            f"Invalid URLs: {len(invalid_urls)}"
        )

        print(
            f"Empty names: {len(empty_names)}"
        )

        return (
            len(records) == self.max_results
            and duplicate_urls == 0
            and len(invalid_urls) == 0
            and len(empty_names) == 0
        )


async def main():

    print(
        "Starting product collection..."
    )

    collector = ProductCollector(
        max_results=1000
    )

    records = await collector.collect()

    valid = collector.validate(
        records
    )

    print(
        f"\nFINAL PRODUCT COUNT: "
        f"{len(records)}"
    )

    if records:

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

    if valid:

        output = OutputManager()

        path = output.save_json(
            "products.json",
            records
        )

        print(
            f"\nSaved products to: {path}"
        )

    else:

        print(
            "\nValidation failed."
        )

        print(
            "products.json was not saved."
        )


if __name__ == "__main__":
    asyncio.run(main())