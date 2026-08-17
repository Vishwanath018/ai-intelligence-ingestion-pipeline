import asyncio
import os
import random

from dotenv import load_dotenv

load_dotenv()


class PayloadTooLargeError(Exception):
    pass


class RateLimitError(Exception):
    pass


class LLMResponse:

    def __init__(
        self,
        provider,
        text="",
        success=False,
        error=None,
    ):
        self.provider = provider
        self.text = text
        self.success = success
        self.error = error


class LLMOrchestrator:

    def __init__(
        self,
        max_chars=12000,
        max_retries=3,
    ):
        self.max_chars = max_chars
        self.max_retries = max_retries

        self.gemini_key = os.getenv(
            "GEMINI_API_KEY"
        )

        self.groq_key = os.getenv(
            "GROQ_API_KEY"
        )

        self.deepseek_key = os.getenv(
            "DEEPSEEK_API_KEY"
        )

    def chunk_text(self, text):

        if len(text) <= self.max_chars:
            return [text]

        chunks = []

        for start in range(
            0,
            len(text),
            self.max_chars,
        ):
            chunks.append(
                text[start:start + self.max_chars]
            )

        return chunks

    async def call_provider(
        self,
        provider,
        prompt,
    ):

        if provider == "gemini":
            return await self.call_gemini(
                prompt
            )

        if provider == "groq":
            return await self.call_groq(
                prompt
            )

        if provider == "deepseek":
            return await self.call_deepseek(
                prompt
            )

        raise ValueError(
            f"Unknown provider: {provider}"
        )

    async def call_gemini(
        self,
        prompt,
    ):

        if not self.gemini_key:
            raise RuntimeError(
                "GEMINI_API_KEY not configured"
            )

        from google import genai

        client = genai.Client(
            api_key=self.gemini_key
        )

        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned empty response"
            )

        return response.text

    async def call_groq(
        self,
        prompt,
    ):

        if not self.groq_key:
            raise RuntimeError(
                "GROQ_API_KEY not configured"
            )

        from groq import Groq

        client = Groq(
            api_key=self.groq_key
        )

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0,
        )

        return response.choices[
            0
        ].message.content

    async def call_deepseek(
        self,
        prompt,
    ):

        if not self.deepseek_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY not configured"
            )

        from openai import OpenAI

        client = OpenAI(
            api_key=self.deepseek_key,
            base_url="https://api.deepseek.com",
        )

        response = await asyncio.to_thread(
            client.chat.completions.create,
            model="deepseek-chat",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0,
        )

        return response.choices[
            0
        ].message.content

    async def call_with_retry(
        self,
        provider,
        prompt,
    ):

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

                if (
                    attempt
                    == self.max_retries - 1
                ):
                    return LLMResponse(
                        provider=provider,
                        error=str(exc),
                    )

                delay = (
                    2 ** attempt
                    + random.uniform(
                        0.1,
                        0.5,
                    )
                )

                await asyncio.sleep(
                    delay
                )

            except PayloadTooLargeError as exc:

                return LLMResponse(
                    provider=provider,
                    error=f"413: {exc}",
                )

            except Exception as exc:

                return LLMResponse(
                    provider=provider,
                    error=str(exc),
                )

        return LLMResponse(
            provider=provider,
            error="Provider failed",
        )

    async def extract(
        self,
        text,
        providers=None,
    ):

        if providers is None:
            providers = [
                "gemini",
                "groq",
                "deepseek",
            ]

        chunks = self.chunk_text(text)

        results = []

        for chunk in chunks:

            prompt = f"""
You are an information extraction system.

Extract information ONLY from the supplied source.

Never invent:
- company names
- products
- dates
- authors
- URLs
- employee counts
- pricing
- GitHub repositories
- GitHub stars

Return structured JSON.

SOURCE:
{chunk}
"""

            response = None

            for provider in providers:

                response = await self.call_with_retry(
                    provider,
                    prompt,
                )

                if response.success:
                    break

            if response is not None:
                results.append(response)

        return results