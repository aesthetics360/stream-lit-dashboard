# services/validators.py
from supabase import Client

def has_required_fields(prod: dict) -> bool:
    req = ["product_name","manufacturer","description"]
    return all((prod.get(k) not in (None,"")) for k in req)

def broken_assets(client: Client, product_id: str) -> list:
    # Placeholder: you can add a HEAD request validator later
    return []
