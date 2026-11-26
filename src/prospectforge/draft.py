from __future__ import annotations

from .errors import LLMParseError, ProviderError
from .llm import LLMClient
from .models import Draft, Lead, Qualification

DRAFT_MARKER = "Draft only - review before any use."


def _short_product(product: str, limit: int = 25) -> str:
    words = product.strip().split()
    if len(words) <= limit:
        return product.strip()
    return " ".join(words[:limit]).rstrip(".,;") + "..."


def heuristic_draft(
    lead: Lead,
    qualification: Qualification,
    product: str,
) -> Draft:
    first_name = lead.first_name or "there"
    company = lead.company or "your team"
    subject = f"Quick idea for {company}"
    if len(subject.split()) > 8:
        subject = "Quick idea for your team"

    detail_parts: list[str] = []
    if lead.title:
        detail_parts.append(f"you are {lead.title} at {company}")
    elif lead.industry:
        detail_parts.append(f"{company} works in {lead.industry}")
    else:
        detail_parts.append(f"I came across {company}")

    detail = detail_parts[0]
    matched = ""
    for reason in qualification.reasons:
        if reason.startswith("Matched ICP keywords:"):
            matched = reason.split(":", 1)[1].strip().rstrip(".")
            break

    body_lines = [
        f"Hi {first_name},",
        "",
        f"I noticed {detail}. {_short_product(product)} is built for teams facing this "
        "kind of problem, so I thought it could be relevant.",
    ]
    if matched:
        body_lines.append(f"Your profile matched on {matched}, which is why I am reaching out.")
    body_lines.extend(
        [
            "Would you be open to a short call next week, or simply replying to this email "
            "if that is easier?",
            "",
            "Best,",
            "",
            DRAFT_MARKER,
        ]
    )
    return Draft(
        lead_key=lead.key,
        subject=subject,
        body="\n".join(body_lines),
        source="heuristic",
    )


class HeuristicDrafter:
    def draft(self, lead: Lead, qualification: Qualification, product: str) -> Draft:
        return heuristic_draft(lead, qualification, product)


class LLMDrafter:
    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def draft(self, lead: Lead, qualification: Qualification, product: str) -> Draft:
        try:
            return self._client.draft(lead, qualification, product)
        except (LLMParseError, ProviderError):
            return heuristic_draft(lead, qualification, product)


def build_drafter(client: LLMClient | None) -> HeuristicDrafter | LLMDrafter:
    if client is None:
        return HeuristicDrafter()
    return LLMDrafter(client)
