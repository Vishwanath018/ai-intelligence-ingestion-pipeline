from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Source(BaseModel):
    name: str
    url: HttpUrl


class BaseRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schemaVersion: str = "1.0"
    recordType: str
    source: Source
    collectedAt: datetime


class StartupContent(BaseModel):
    entityName: str
    employeeCount: int | None = None


class StartupRecord(BaseRecord):
    recordType: Literal["STARTUP"] = "STARTUP"
    content: StartupContent


class ProductContent(BaseModel):
    startupName: str
    pricingModel: Literal["FREE", "FREEMIUM", "PAID", "ENTERPRISE"]


class ProductRecord(BaseRecord):
    recordType: Literal["PRODUCT"] = "PRODUCT"
    content: ProductContent


class ResearchPaperContent(BaseModel):
    title: str
    authors: list[str]
    paper_url: HttpUrl
    github_url: HttpUrl | None = None
    github_stars: int | None = None
    published_date: datetime


class ResearchPaperRecord(BaseRecord):
    recordType: Literal["RESEARCH_PAPER"] = "RESEARCH_PAPER"
    content: ResearchPaperContent


class JobContent(BaseModel):
    company: str
    date: datetime
    is_remote: bool
    role_family: str


class JobRecord(BaseRecord):
    recordType: Literal["JOB"] = "JOB"
    content: JobContent


class NewsContent(BaseModel):
    title: str
    date: datetime
    text: str
    url: HttpUrl


class NewsRecord(BaseRecord):
    recordType: Literal["NEWS"] = "NEWS"
    content: NewsContent


class EntityMapping(BaseModel):
    raw_name: str
    canonical_name: str
    entity_type: Literal["STARTUP", "PRODUCT"]
    confidence: float = Field(ge=0.0, le=1.0)
    source_url: HttpUrl