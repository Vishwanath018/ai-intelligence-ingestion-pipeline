import asyncio
import os
import re

import aiohttp
from dotenv import load_dotenv

load_dotenv()


class GitHubStarTracker:

    API_BASE = "https://api.github.com"

    def __init__(
        self,
        token=None,
        timeout_seconds=15,
        max_retries=3,
    ):
        self.token = (
            token
            or os.getenv("GITHUB_TOKEN")
        )

        self.timeout = aiohttp.ClientTimeout(
            total=timeout_seconds
        )

        self.max_retries = max_retries

    @staticmethod
    def parse_repo_url(url):

        if not url:
            return None

        match = re.search(
            r"github\.com/([^/]+)/([^/#?]+)",
            url,
            re.IGNORECASE,
        )

        if not match:
            return None

        owner = match.group(1)

        repo = match.group(2).replace(
            ".git",
            "",
        )

        if repo.lower() in {
            "issues",
            "pulls",
            "releases",
            "actions",
            "wiki",
        }:
            return None

        return owner, repo

    def headers(self):

        headers = {
            "Accept": (
                "application/vnd.github+json"
            ),
            "User-Agent": (
                "AI-Intelligence-"
                "Ingestion-Pipeline/1.0"
            ),
        }

        if self.token:
            headers["Authorization"] = (
                f"Bearer {self.token}"
            )

        return headers

    async def get_stars(
        self,
        repo_url,
    ):

        parsed = self.parse_repo_url(
            repo_url
        )

        if not parsed:
            return None

        owner, repo = parsed

        url = (
            f"{self.API_BASE}/repos/"
            f"{owner}/{repo}"
        )

        for attempt in range(
            self.max_retries
        ):

            try:

                async with aiohttp.ClientSession(
                    timeout=self.timeout,
                ) as session:

                    async with session.get(
                        url,
                        headers=self.headers(),
                    ) as response:

                        if response.status == 200:

                            data = (
                                await response.json()
                            )

                            return data.get(
                                "stargazers_count"
                            )

                        if response.status == 429:

                            if (
                                attempt
                                == self.max_retries - 1
                            ):
                                return None

                            delay = (
                                2 ** attempt
                            )

                            await asyncio.sleep(
                                delay
                            )

                            continue

                        if response.status == 403:

                            return None

                        if response.status == 404:

                            return None

                        if response.status >= 500:

                            if (
                                attempt
                                == self.max_retries - 1
                            ):
                                return None

                            delay = (
                                2 ** attempt
                            )

                            await asyncio.sleep(
                                delay
                            )

                            continue

                        return None

            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
            ):

                if (
                    attempt
                    == self.max_retries - 1
                ):
                    return None

                delay = 2 ** attempt

                await asyncio.sleep(
                    delay
                )

        return None