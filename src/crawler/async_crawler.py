import asyncio
from dataclasses import dataclass
from typing import Iterable

import aiohttp
from bs4 import BeautifulSoup


@dataclass
class CrawlResult:
    url: str
    status: int
    title: str | None
    text: str
    error: str | None = None


class AsyncCrawler:
    def __init__(
        self,
        concurrency: int = 20,
        timeout_seconds: int = 20,
        max_retries: int = 3,
    ):
        self.concurrency = concurrency
        self.max_retries = max_retries
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self.headers = {
            "User-Agent": (
                "AI-Intelligence-Ingestion-Pipeline/1.0 "
                "(research crawler)"
            )
        }

    async def fetch(
        self,
        session: aiohttp.ClientSession,
        url: str,
    ) -> CrawlResult:

        for attempt in range(self.max_retries):
            try:
                async with session.get(
                    url,
                    allow_redirects=True,
                ) as response:

                    if response.status == 429:
                        delay = (2 ** attempt) + 0.5
                        await asyncio.sleep(delay)
                        continue

                    if response.status >= 400:
                        return CrawlResult(
                            url=url,
                            status=response.status,
                            title=None,
                            text="",
                            error=f"HTTP {response.status}",
                        )

                    html = await response.text(
                        errors="ignore"
                    )

                    soup = BeautifulSoup(
                        html,
                        "lxml",
                    )

                    title = (
                        soup.title.get_text(strip=True)
                        if soup.title
                        else None
                    )

                    for element in soup(
                        ["script", "style", "noscript"]
                    ):
                        element.decompose()

                    text = soup.get_text(
                        separator=" ",
                        strip=True,
                    )

                    return CrawlResult(
                        url=url,
                        status=response.status,
                        title=title,
                        text=text,
                    )

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ) as exc:

                if attempt == self.max_retries - 1:
                    return CrawlResult(
                        url=url,
                        status=0,
                        title=None,
                        text="",
                        error=str(exc),
                    )

                delay = (2 ** attempt) + 0.5
                await asyncio.sleep(delay)

        return CrawlResult(
            url=url,
            status=0,
            title=None,
            text="",
            error="Maximum retries exceeded",
        )

    async def crawl(
        self,
        urls: Iterable[str],
    ) -> list[CrawlResult]:

        semaphore = asyncio.Semaphore(
            self.concurrency
        )

        async with aiohttp.ClientSession(
            timeout=self.timeout,
            headers=self.headers,
        ) as session:

            async def bounded_fetch(url: str):
                async with semaphore:
                    return await self.fetch(
                        session,
                        url,
                    )

            tasks = [
                asyncio.create_task(
                    bounded_fetch(url)
                )
                for url in urls
            ]

            return await asyncio.gather(
                *tasks
            )


async def main():
    crawler = AsyncCrawler(
        concurrency=5
    )

    urls = [
        "https://example.com",
        "https://www.python.org",
    ]

    results = await crawler.crawl(urls)

    for result in results:
        print(
            result.status,
            result.url,
            result.title,
        )


if __name__ == "__main__":
    asyncio.run(main())