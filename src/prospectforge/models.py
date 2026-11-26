from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

PERSONAL_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.es",
    "hotmail.com",
    "hotmail.es",
    "outlook.com",
    "live.com",
    "icloud.com",
    "me.com",
    "proton.me",
    "protonmail.com",
    "aol.com",
    "gmx.com",
    "gmx.net",
    "mail.com",
    "yandex.com",
    "zoho.com",
}

EmailType = Literal["work", "personal", "unknown", "none"]
Verdict = Literal["strong", "ok", "weak", "bad"]
Source = Literal["llm", "heuristic"]
ProviderName = Literal["b2bsearch", "olympus", "input"]


def normalize_domain(value: str | None) -> str | None:
    if not value:
        return None
    domain = value.strip().lower()
    domain = re.sub(r"^https?://", "", domain)
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/", 1)[0]
    domain = domain.split("@")[-1]
    return domain or None


def infer_email_type(email: str | None) -> EmailType:
    if not email:
        return "none"
    domain = normalize_domain(email)
    if domain in PERSONAL_EMAIL_DOMAINS:
        return "personal"
    return "work"


def email_domain(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    return normalize_domain(email)


class Lead(BaseModel):
    provider: ProviderName = "input"
    name: str | None = None
    title: str | None = None
    department: str | None = None
    seniority: str | None = None
    email: EmailStr | None = None
    email_type: EmailType = "unknown"
    phone: str | None = None
    company: str | None = None
    company_domain: str | None = None
    company_size: str | None = None
    industry: str | None = None
    country: str | None = None
    city: str | None = None
    linkedin_url: str | None = None
    raw_source: dict[str, Any] = Field(default_factory=dict)

    @field_validator("company_domain")
    @classmethod
    def _normalize_company_domain(cls, value: str | None) -> str | None:
        return normalize_domain(value)

    @field_validator("email_type", mode="before")
    @classmethod
    def _fill_email_type(cls, value: Any) -> Any:
        return value

    def model_post_init(self, __context: Any) -> None:
        if self.email_type == "unknown" and self.email:
            object.__setattr__(self, "email_type", infer_email_type(str(self.email)))

    @property
    def key(self) -> str:
        if self.email:
            return str(self.email).strip().lower()
        basis = f"{(self.name or '').strip().lower()}|{(self.company or '').strip().lower()}"
        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:16]
        return f"lead:{digest}"

    @property
    def display_name(self) -> str:
        return self.name or "there"

    @property
    def first_name(self) -> str:
        if not self.name:
            return "there"
        return self.name.split()[0]


class Qualification(BaseModel):
    lead_key: str
    score: int = Field(ge=0, le=100)
    verdict: Verdict
    reasons: list[str] = Field(default_factory=list)
    source: Source


class Draft(BaseModel):
    lead_key: str
    subject: str
    body: str
    source: Source


class PipelineResult(BaseModel):
    product: str
    icp: str
    provider: str
    leads: list[Lead] = Field(default_factory=list)
    qualifications: list[Qualification] = Field(default_factory=list)
    drafts: list[Draft] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class IcpFilters(BaseModel):
    titles: list[str] = Field(default_factory=list)
    exclude_titles: list[str] = Field(default_factory=list)
    departments: list[str] = Field(default_factory=list)
    seniority: list[str] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    cities: list[str] = Field(default_factory=list)
    industries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    company_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    company_size_min: int | None = None
    company_size_max: int | None = None


def verdict_for_score(score: int) -> Verdict:
    if score >= 70:
        return "strong"
    if score >= 40:
        return "ok"
    if score >= 15:
        return "weak"
    return "bad"
