import re
import asyncio

import aiohttp


class GitHubStarTracker:
    API_BASE = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.token = token

    @staticmethod
    def parse_repo_url(url: str) -> tuple[str, str] | None:
        if not url:
            return None

        match = re.search(
            r"github\.com/([^/]+)/([^/#?]+)",
            url,
        )

        if not match:
            return None

        owner = match.group(1)
        repo = match.group(2).removesuffix(".git")

        return owner, repo

    async def get_stars(
        self,
        repo_url: str,
    ) -> int | None:

        parsed = self.parse_repo_url(repo_url)

        if not parsed:
            return None

        owner, repo = parsed

        headers = {
            "Accept": "application/vnd.github+json",
        }

        if self.token:
            headers["Authorization"] = (
                f"Bearer {self.token}"
            )

        url = (
            f"{self.API_BASE}/repos/"
            f"{owner}/{repo}"
        )

        try:
            timeout = aiohttp.ClientTimeout(
                total=15
            )

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.get(
                    url,
                    headers=headers,
                ) as response:

                    if response.status != 200:
                        return None

                    data = await response.json()

                    return data.get("stargazers_count")

        except (
            aiohttp.ClientError,
            asyncio.TimeoutError,
        ):
            return None