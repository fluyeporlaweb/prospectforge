class ProspectforgeError(Exception):
    """Base error for all prospectforge failures."""


class ConfigError(ProspectforgeError):
    """Invalid or missing configuration."""


class CapExceededError(ConfigError):
    """A requested result count is outside the allowed range."""


class ProviderError(ProspectforgeError):
    """An upstream lead provider failed or returned unusable data."""


class LLMParseError(ProspectforgeError):
    """The LLM returned output that could not be parsed as the expected JSON."""
