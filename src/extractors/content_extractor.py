from dataclasses import dataclass
from bs4 import BeautifulSoup


@dataclass
class ExtractedContent:
    title: str | None
    text: str
    description: str | None
    published_date: str | None


class ContentExtractor:

    def extract(self, html: str) -> ExtractedContent:
        soup = BeautifulSoup(html, "lxml")

        title = None
        if soup.title:
            title = soup.title.get_text(" ", strip=True)

        description = None
        description_tag = soup.find(
            "meta",
            attrs={"name": "description"}
        )

        if description_tag:
            description = description_tag.get("content")

        published_date = self._find_date(soup)

        for element in soup(
            ["script", "style", "noscript", "svg"]
        ):
            element.decompose()

        article = (
            soup.find("article")
            or soup.find("main")
            or soup.body
            or soup
        )

        text = article.get_text(
            separator=" ",
            strip=True
        )

        return ExtractedContent(
            title=title,
            text=text,
            description=description,
            published_date=published_date,
        )

    @staticmethod
    def _find_date(soup: BeautifulSoup) -> str | None:

        date_selectors = [
            ("meta", {"property": "article:published_time"}),
            ("meta", {"property": "og:published_time"}),
            ("meta", {"name": "date"}),
            ("meta", {"name": "publish_date"}),
            ("time", {}),
        ]

        for tag_name, attrs in date_selectors:
            tag = soup.find(tag_name, attrs=attrs)

            if tag:
                value = (
                    tag.get("content")
                    or tag.get("datetime")
                    or tag.get_text(strip=True)
                )

                if value:
                    return value

        return None