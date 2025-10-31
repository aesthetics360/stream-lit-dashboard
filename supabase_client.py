import os
from functools import lru_cache
from typing import Any, Dict

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# ---- STRICT: Service-role only ----
_SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
_SR_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

if not _SUPABASE_URL or not _SR_KEY:
    raise RuntimeError(
        "Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY in .env. "
        "This app is configured to use ONLY the service-role key."
    )

@lru_cache(maxsize=1)
def sb() -> Client:
    """Singleton Supabase client using the service-role key (bypasses RLS)."""
    return create_client(_SUPABASE_URL, _SR_KEY)

# ----------------- helpers -----------------

def _to_array(v):
    if v is None:
        return None
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        parts = [p.strip() for p in v.split(",") if p.strip()]
        return parts
    return v

def update_staging_product(product_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a staging_products row by id.
    - Coerces commas->arrays for source_urls, source_page_ids, active_ingredients
    - Converts empty strings to NULL
    - Bumps updated_at from client (ISO) to avoid extra SQL deps
    - Propagates errors so Streamlit shows them
    """
    from datetime import datetime, timezone

    client = sb()

    payload = dict(fields)

    # Coerce arrays from text areas
    for k in ("source_urls", "source_page_ids", "active_ingredients"):
        if k in payload:
            payload[k] = _to_array(payload[k])

    # Empty strings -> None
    for k, v in list(payload.items()):
        if isinstance(v, str) and v.strip() == "":
            payload[k] = None

    payload["updated_at"] = datetime.now(timezone.utc).isoformat()

    res = (
        client.table("staging_products")
        .update(payload)
        .eq("id", product_id)
        .execute()
    )

    if not getattr(res, "data", None):
        raise RuntimeError("Update returned no data. Check payload types or table RLS.")

    return res.data[0]
