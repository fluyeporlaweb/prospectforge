"""prospectforge: discover, qualify and draft B2B outreach locally."""

from .models import Draft, IcpFilters, Lead, PipelineResult, Qualification

__version__ = "0.1.0"

__all__ = [
    "Draft",
    "IcpFilters",
    "Lead",
    "PipelineResult",
    "Qualification",
    "__version__",
]
