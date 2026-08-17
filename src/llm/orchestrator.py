import asyncio
import random
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class LLMResponse:
    provider: str
    text: str
    success: bool
    error: str | None = None


class PayloadTooLargeError(Exception):
    pass


class RateLimitError(Exception):
    pass


class LLMOrchestrator:

    def __init__(
        self,
        max_chars: int = 12000,
        max_retries: int = 3,
    ):
        self.max_chars = max_chars
        self.max_retries = max_retries

    def chunk_text(
        self,
        text: str,
    ) -> list[str]:

        if len(text) <= self.max_chars:
            return [text]

        chunks = []

        for start in range(
            0,
            len(text),
            self.max_chars,
        ):
            chunk = text[
                start:start + self.max_chars
            ]
            chunks.append(chunk)

        return chunks

    async def call_provider(
        self,
        provider: str,
        prompt: str,
    ) -> str:

        # Provider integration is intentionally isolated.
        # API calls will be added through provider adapters.
        raise NotImplementedError(
            f"{provider} adapter not configured"
        )

    async def call_with_retry(
        self,
        provider: str,
        prompt: str,
    ) -> LLMResponse:

        for attempt in range(
            self.max_retries
        ):
            try:

                result = await self.call_provider(
                    provider,
                    prompt,
                )

                return LLMResponse(
                    provider=provider,
                    text=result,
                    success=True,
                )

            except RateLimitError as exc:

                if attempt == self.max_retries - 1:
                    return LLMResponse(
                        provider=provider,
                        text="",
                        success=False,
                        error=str(exc),
                    )

                delay = (
                    2 ** attempt
                    + random.uniform(0.1, 0.5)
                )

                await asyncio.sleep(delay)

            except PayloadTooLargeError as exc:

                return LLMResponse(
                    provider=provider,
                    text="",
                    success=False,
                    error=f"413: {exc}",
                )

            except Exception as exc:

                return LLMResponse(
                    provider=provider,
                    text="",
                    success=False,
                    error=str(exc),
                )

        return LLMResponse(
            provider=provider,
            text="",
            success=False,
            error="Provider failed",
        )

    async def extract(
        self,
        text: str,
        providers: list[str] | None = None,
    ) -> list[LLMResponse]:

        if providers is None:
            providers = [
                "gemini",
                "groq",
                "openai",
            ]

        chunks = self.chunk_text(text)
        results = []

        for chunk in chunks:

            prompt = (
                "Extract structured information "
                "from the following source text. "
                "Do not invent information.\n\n"
                + chunk
            )

            response = None

            for provider in providers:

                response = await self.call_with_retry(
                    provider,
                    prompt,
                )

                if response.success:
                    break

            if response:
                results.append(response)

        return results