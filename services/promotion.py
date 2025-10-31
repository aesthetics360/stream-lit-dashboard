# services/promotion.py
import os
import psycopg2
from datetime import datetime
from supabase import Client

# Assumes your GL (Global Library) is PostgreSQL (Aurora/RDS).
# Provide DSN in GL_PG_DSN in .env like:
# postgresql://user:pass@host:5432/gl_db

def _gl_conn():
    dsn = os.getenv("GL_PG_DSN")
    if not dsn:
        raise RuntimeError("Set GL_PG_DSN in .env for promotion.")
    return psycopg2.connect(dsn)

def promote_product(client: Client, staging_product_id: str, promoted_by: str = "curator"):
    # 1) Fetch staging product & assets
    sp = client.table("staging_products").select("*").eq("id", staging_product_id).single().execute().data
    if not sp:
        return False, "staging product not found"

    if sp.get("review_status") != "approved":
        return False, "product not approved"

    assets = client.table("staging_assets").select("*").eq("staging_product_id", staging_product_id).eq("keep_asset", True).execute().data or []

    # 2) Connect GL and run tx
    conn = _gl_conn()
    conn.autocommit = False
    try:
        cur = conn.cursor()

        # 2a) ensure manufacturer exists (simplified)
        cur.execute("SELECT id FROM manufacturers WHERE name = %s", (sp["manufacturer"],))
        row = cur.fetchone()
        if row:
            mfr_id = row[0]
        else:
            cur.execute("INSERT INTO manufacturers(name) VALUES (%s) RETURNING id", (sp["manufacturer"],))
            mfr_id = cur.fetchone()[0]

        # 2b) (optional) ensure category exists
        category = sp.get("category")
        cat_id = None
        if category:
            cur.execute("SELECT id FROM categories WHERE name = %s", (category,))
            r2 = cur.fetchone()
            if r2:
                cat_id = r2[0]
            else:
                cur.execute("INSERT INTO categories(name) VALUES (%s) RETURNING id", (category,))
                cat_id = cur.fetchone()[0]

        # 2c) insert product
        source_urls = sp.get("source_urls") or []
        source_url = source_urls[0] if source_urls else None

        cur.execute("""
            INSERT INTO products (name, manufacturer_id, category_id, description, source_url)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (sp["product_name"], mfr_id, cat_id, sp.get("description"), source_url))
        gl_product_id = cur.fetchone()[0]

        # 2d) assets
        promoted_count = 0
        for a in assets:
            cur.execute("""
                INSERT INTO document_assets (product_id, manufacturer_id, asset_type, content_category, title, description, url, file_size)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING id
            """, (gl_product_id, mfr_id, a.get("asset_type"), a.get("content_category"),
                  a.get("title"), a.get("description"), a.get("file_url"), a.get("file_size_bytes")))
            new_asset_id = cur.fetchone()[0]
            promoted_count += 1

            # mark staging asset
            client.table("staging_assets").update({
                "promoted_to_gl": True,
                "gl_asset_id": new_asset_id
            }).eq("id", a["id"]).execute()

        # 2e) mark staging product
        client.table("staging_products").update({
            "promoted_to_gl": True,
            "gl_product_id": str(gl_product_id),
            "promoted_at": datetime.utcnow().isoformat()
        }).eq("id", staging_product_id).execute()

        # 2f) log promotion
        client.table("staging_promotion_log").insert({
            "staging_product_id": staging_product_id,
            "gl_product_id": str(gl_product_id),
            "promoted_by": promoted_by,
            "assets_promoted_count": promoted_count,
            "promotion_status": "success"
        }).execute()

        conn.commit()
        return True, f"Promoted product (assets: {promoted_count})"

    except Exception as e:
        conn.rollback()
        # log failure
        client.table("staging_promotion_log").insert({
            "staging_product_id": staging_product_id,
            "promoted_by": promoted_by,
            "promotion_status": "failed",
            "error_message": str(e)
        }).execute()
        return False, f"Promotion failed: {e}"

    finally:
        conn.close()
