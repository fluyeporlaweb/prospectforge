"""Thin, mockable wrapper around the official apify-client.

This is the ONLY module in prospectforge that imports the `apify_client`
package. Everything else depends on ApifyRunner so tests can replace it.
"""

from __future__ import annotations

from typing import Any

from apify_client import ApifyClient

from .config import require_apify_token
from .errors import ProviderError


def _get(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        return obj.get(key)
    return getattr(obj, key, None)


class ApifyRunner:
    def __init__(self, token: str | None = None) -> None:
        self._token = token

    def run_actor(
        self, actor_id: str, run_input: dict[str, Any], *, max_results: int
    ) -> list[dict[str, Any]]:
        token = self._token or require_apify_token()
        client = ApifyClient(token)
        try:
            run = client.actor(actor_id).call(run_input=run_input)
            dataset_id = _get(run, "defaultDatasetId") or _get(run, "default_dataset_id")
            if not dataset_id:
                raise ProviderError("Apify run finished without a default dataset id.")
            items: list[dict[str, Any]] = []
            for item in client.dataset(dataset_id).iterate_items():
                if isinstance(item, dict):
                    items.append(item)
                else:
                    items.append(dict(item))
                if len(items) >= max_results:
                    break
            return items
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - provider errors must be wrapped
            raise ProviderError(f"Apify actor {actor_id} failed: {exc}") from exc
        finally:
            try:
                client.close()  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 - close is best effort
                pass
