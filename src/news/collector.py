import asyncio
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote, urlparse

import aiohttp
from bs4 import BeautifulSoup


class NewsCollector:

    GDELT_URL = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
    )

    RSS_FEEDS = [
        (
            "Google News AI",
            "https://news.google.com/rss/search?"
            "q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en",
        ),
        (
            "Google News Technology",
            "https://news.google.com/rss/search?"
            "q=technology&hl=en-US&gl=US&ceid=US:en",
        ),
        (
            "Google News Machine Learning",
            "https://news.google.com/rss/search?"
            "q=machine+learning&hl=en-US&gl=US&ceid=US:en",
        ),
        (
            "Google News Startups",
            "https://news.google.com/rss/search?"
            "q=AI+startups&hl=en-US&gl=US&ceid=US:en",
        ),
        (
            "Google News Cybersecurity",
            "https://news.google.com/rss/search?"
            "q=cybersecurity&hl=en-US&gl=US&ceid=US:en",
        ),
    ]

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
    ]

    def __init__(
        self,
        max_results=1000,
        request_timeout=8,
        max_retries=1,
    ):
        self.max_results = max_results
        self.request_timeout = request_timeout
        self.max_retries = max_retries

    @staticmethod
    def clean_url(url):

        if not url:
            return ""

        url = str(url).strip()

        match = re.match(
            r"\[.*?\]\((https?://[^)]+)\)",
            url,
        )

        if match:
            url = match.group(1)

        url = url.strip(
            " \t\r\n<>\"'.,);]}"
        )

        if not url.startswith(
            ("http://", "https://")
        ):
            return ""

        parsed = urlparse(url)

        if not parsed.netloc:
            return ""

        return url

    @staticmethod
    def clean_text(text):

        if not text:
            return ""

        text = BeautifulSoup(
            str(text),
            "html.parser",
        ).get_text(
            separator=" ",
            strip=True,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    @staticmethod
    def parse_date(value):

        if not value:
            return datetime.now(
                timezone.utc
            )

        value = str(value).strip()

        try:

            if re.fullmatch(
                r"\d{14}",
                value,
            ):
                return datetime.strptime(
                    value,
                    "%Y%m%d%H%M%S",
                ).replace(
                    tzinfo=timezone.utc
                )

        except ValueError:
            pass

        try:

            parsed = parsedate_to_datetime(
                value
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        except (
            ValueError,
            TypeError,
        ):
            pass

        try:

            parsed = datetime.fromisoformat(
                value.replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        except ValueError:

            return datetime.now(
                timezone.utc
            )

    async def fetch_gdelt(
        self,
        session,
        query,
    ):

        encoded_query = quote(query)

        url = (
            f"{self.GDELT_URL}"
            f"?query={encoded_query}"
            f"&mode=artlist"
            f"&maxrecords=250"
            f"&format=json"
            f"&timespan=3months"
            f"&sort=datedesc"
        )

        try:

            async with session.get(
                url
            ) as response:

                if response.status == 200:

                    return await response.json()

                if response.status == 429:

                    print(
                        "GDELT rate limited."
                    )

                    return None

                print(
                    f"GDELT returned "
                    f"HTTP {response.status}"
                )

                return None

        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
        ) as exc:

            print(
                f"GDELT unavailable: "
                f"{type(exc).__name__}"
            )

            return None

    def parse_gdelt_article(
        self,
        article,
    ):

        url = self.clean_url(
            article.get("url")
        )

        title = self.clean_text(
            article.get("title")
        )

        if not url or not title:
            return None

        domain = (
            article.get("domain")
            or urlparse(url).netloc
        )

        return {
            "schemaVersion": "1.0",
            "recordType": "NEWS",
            "source": {
                "name": self.clean_text(
                    domain
                ),
                "url": url,
            },
            "content": {
                "title": title,
                "date": self.parse_date(
                    article.get("seendate")
                    or article.get("published")
                ),
                "text": self.clean_text(
                    article.get("snippet")
                    or title
                ),
                "url": url,
            },
            "collectedAt": datetime.now(
                timezone.utc
            ),
        }

    async def try_gdelt(
        self,
        records,
    ):

        timeout = aiohttp.ClientTimeout(
            total=self.request_timeout
        )

        headers = {
            "User-Agent":
                "AI-Intelligence-Ingestion-Pipeline/1.0"
        }

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
        ) as session:

            for query in self.QUERIES:

                print(
                    f"\nGDELT query: {query}"
                )

                data = await self.fetch_gdelt(
                    session,
                    query,
                )

                if data is None:

                    print(
                        "GDELT failed. "
                        "Switching immediately "
                        "to RSS fallback."
                    )

                    return False

                articles = data.get(
                    "articles",
                    []
                )

                for article in articles:

                    record = (
                        self.parse_gdelt_article(
                            article
                        )
                    )

                    if not record:
                        continue

                    url = record[
                        "content"
                    ][
                        "url"
                    ]

                    records[url] = record

                    if (
                        len(records)
                        >= self.max_results
                    ):
                        return True

        return True

    def parse_rss_item(
        self,
        item,
        feed_name,
    ):

        title_element = item.find(
            "title"
        )

        if title_element is None:
            return None

        title = self.clean_text(
            title_element.get_text()
        )

        if not title:
            return None

        link_element = item.find(
            "link"
        )

        url = ""

        if link_element:

            url = self.clean_url(
                link_element.get_text(
                    strip=True
                )
            )

            if not url:

                url = self.clean_url(
                    link_element.get(
                        "href",
                        ""
                    )
                )

        if not url:
            return None

        description_element = (
            item.find("description")
        )

        description = ""

        if description_element:

            description = self.clean_text(
                description_element.get_text()
            )

        pub_element = (
            item.find("pubDate")
            or item.find("published")
            or item.find("updated")
        )

        date_value = (
            pub_element.get_text(
                strip=True
            )
            if pub_element
            else None
        )

        return {
            "schemaVersion": "1.0",
            "recordType": "NEWS",
            "source": {
                "name": (
                    urlparse(url).netloc
                    or feed_name
                ),
                "url": url,
            },
            "content": {
                "title": title,
                "date": self.parse_date(
                    date_value
                ),
                "text": (
                    description
                    or title
                ),
                "url": url,
            },
            "collectedAt": datetime.now(
                timezone.utc
            ),
        }

    async def fetch_rss(
        self,
        session,
        feed_name,
        feed_url,
    ):

        try:

            async with session.get(
                feed_url,
                allow_redirects=True,
            ) as response:

                if response.status != 200:

                    print(
                        f"{feed_name}: "
                        f"HTTP {response.status}"
                    )

                    return []

                xml = await response.text(
                    errors="ignore"
                )

                soup = BeautifulSoup(
                    xml,
                    "xml",
                )

                items = soup.find_all(
                    "item"
                )

                records = []

                for item in items:

                    record = (
                        self.parse_rss_item(
                            item,
                            feed_name,
                        )
                    )

                    if record:

                        records.append(
                            record
                        )

                return records

        except (
            asyncio.TimeoutError,
            aiohttp.ClientError,
        ) as exc:

            print(
                f"{feed_name}: "
                f"{type(exc).__name__}"
            )

            return []

    async def collect_rss(
        self,
        records,
    ):

        print(
            "\n"
            + "=" * 60
        )

        print(
            "RSS FALLBACK - REAL-TIME NEWS"
        )

        print(
            "=" * 60
        )

        timeout = aiohttp.ClientTimeout(
            total=10
        )

        headers = {
            "User-Agent":
                "AI-Intelligence-Ingestion-Pipeline/1.0"
        }

        async with aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
        ) as session:

            tasks = [
                self.fetch_rss(
                    session,
                    name,
                    url,
                )
                for name, url
                in self.RSS_FEEDS
            ]

            results = await asyncio.gather(
                *tasks
            )

        for feed_records in results:

            for record in feed_records:

                url = record[
                    "content"
                ][
                    "url"
                ]

                if url not in records:

                    records[url] = record

                if (
                    len(records)
                    >= self.max_results
                ):
                    break

            if (
                len(records)
                >= self.max_results
            ):
                break

        print(
            f"RSS unique records: "
            f"{len(records)}"
        )

        return records

    async def collect(self):

        print(
            "Starting news collection..."
        )

        records = {}

        gdelt_success = (
            await self.try_gdelt(
                records
            )
        )

        if not gdelt_success:

            records = (
                await self.collect_rss(
                    records
                )
            )

        records = list(
            records.values()
        )[
            :self.max_results
        ]

        print(
            "\nFINAL NEWS COUNT: "
            f"{len(records)}"
        )

        return records

    def validate(
        self,
        records,
    ):

        urls = []
        invalid = 0

        for record in records:

            if record.get(
                "recordType"
            ) != "NEWS":

                invalid += 1
                continue

            content = record.get(
                "content",
                {}
            )

            url = self.clean_url(
                content.get("url")
            )

            title = self.clean_text(
                content.get("title")
            )

            if not url or not title:

                invalid += 1
                continue

            urls.append(url)

        duplicates = (
            len(urls)
            - len(set(urls))
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
            f"{duplicates}"
        )

        print(
            f"Invalid records: "
            f"{invalid}"
        )

        return (
            len(records) > 0
            and duplicates == 0
            and invalid == 0
        )


async def main():

    collector = NewsCollector(
        max_results=20
    )

    records = await collector.collect()

    valid = collector.validate(
        records
    )

    print(
        f"\nValidation result: "
        f"{valid}"
    )


if __name__ == "__main__":

    asyncio.run(main())
