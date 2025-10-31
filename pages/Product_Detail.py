# pages/Product_Detail.py
import streamlit as st
from datetime import datetime, timezone
from supabase_client import sb


st.set_page_config(page_title="Product Editor", layout="wide")
st.title("✏️ Product Editor")

client = sb()



# ---- helpers for pretty diffs ----
def _normalize(v):
    # unify types for comparison (lists, strings, Nones)
    if isinstance(v, list):
        return [str(x).strip() for x in v]
    if v is None:
        return None
    return str(v).strip()

FIELD_LABELS = {
    "product_name": "Product name",
    "manufacturer": "Manufacturer",
    "category": "Category",
    "review_status": "Review status",
    "description": "Description",
    "indications": "Indications",
    "contraindications": "Contraindications",
    "regulatory_status": "Regulatory status",
    "completeness_score": "Completeness score",
    "source_urls": "Source URLs",
}




# --- Resolve the product id ---
pid = st.session_state.get("selected_product_id") or st.query_params.get("pid")
if not pid:
    st.info("No product selected. Pick one below or open from the Products page.")
    rows = (
        client.table("staging_products")
        .select("id, product_name")
        .order("updated_at", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )
    opt = st.selectbox(
        "Select a product",
        options=["(None)"] + [r["id"] for r in rows],
        format_func=lambda v: "(None)" if v == "(None)" else next((r["product_name"] for r in rows if r["id"] == v), v),
    )
    if opt != "(None)":
        st.session_state["selected_product_id"] = opt
        st.query_params["pid"] = opt
        st.rerun()
    st.stop()

# --- Load the product ---
res = client.table("staging_products").select("*").eq("id", pid).single().execute()
prod = res.data
if not prod:
    st.error("Product not found.")
    st.stop()

# --- Editor form ---
with st.form("edit_product", clear_on_submit=False):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Product name", prod.get("product_name") or "")
        mfr = st.text_input("Manufacturer", prod.get("manufacturer") or "")
        cat = st.text_input("Category", prod.get("category") or "")

    with col2:
        status = st.selectbox(
            "Review status",
            options=["pending", "in_review", "approved", "rejected"],
            index=["pending", "in_review", "approved", "rejected"].index(prod.get("review_status", "pending")),
        )
        score = st.number_input(
            "Completeness score",
            value=int(prod.get("completeness_score") or 0),
            min_value=0,
            max_value=200,
        )
        srcs_text = ", ".join(prod.get("source_urls") or [])
        srcs_text = st.text_area("Source URLs (comma-separated)", srcs_text)

    desc = st.text_area("Description", prod.get("description") or "", height=160)
    ind = st.text_area("Indications", prod.get("indications") or "", height=120)
    contra = st.text_area("Contraindications", prod.get("contraindications") or "", height=120)
    reg = st.selectbox(
        "Regulatory status",
        options=["unknown", "fda", "ce", "other"],
        index=["unknown", "fda", "ce", "other"].index(prod.get("regulatory_status") or "unknown"),
    )

    submitted = st.form_submit_button("Save changes", type="primary")

    # if submitted:
    #     source_urls = [s.strip() for s in (srcs_text or "").split(",") if s.strip()]
    #     payload = {
    #         "product_name": name.strip() or None,
    #         "manufacturer": mfr.strip() or None,
    #         "category": cat.strip() or None,
    #         "review_status": status,
    #         "description": (desc or "").strip() or None,
    #         "indications": (ind or "").strip() or None,
    #         "contraindications": (contra or "").strip() or None,
    #         "regulatory_status": reg or "unknown",
    #         "completeness_score": int(score),
    #         "source_urls": source_urls if source_urls else [],
    #         "updated_at": datetime.now(timezone.utc).isoformat(),
    #     }

    #     try:
    #         # 1) Update
    #         upd_res = (
    #             client.table("staging_products")
    #             .update(payload)
    #             .eq("id", pid)
    #             .execute()
    #         )
    #         # Optional: check rows affected
    #         # if getattr(upd_res, "count", None) == 0: ...

    #         # 2) Read back (separate call — no chaining)
    #         _ = (
    #             client.table("staging_products")
    #             .select("*")
    #             .eq("id", pid)
    #             .single()
    #             .execute()
    #         ).data

    #         st.success("Saved ✔")
    #         st.session_state["selected_product_id"] = pid
    #         st.query_params["pid"] = pid
    #         st.rerun()

    #     except Exception as e:
    #         st.error("Save failed.")
    #         st.exception(e)

    if submitted:
        source_urls = [s.strip() for s in (srcs_text or "").split(",") if s.strip()]
        payload = {
            "product_name": name.strip() or None,
            "manufacturer": mfr.strip() or None,
            "category": cat.strip() or None,
            "review_status": status,
            "description": (desc or "").strip() or None,
            "indications": (ind or "").strip() or None,
            "contraindications": (contra or "").strip() or None,
            "regulatory_status": reg or "unknown",
            "completeness_score": int(score),
            "source_urls": source_urls if source_urls else [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # ---- compute diff vs original row (prod) ----
        changed = {}
        for k, v in payload.items():
            old_v = prod.get(k)
            if _normalize(old_v) != _normalize(v):
                changed[k] = {"before": old_v, "after": v}

        if not changed:
            st.info("No changes detected — nothing to save.")
        else:
            try:
                # 1) Update
                client.table("staging_products").update(payload).eq("id", pid).execute()

                # 2) Read back to keep UI fresh
                prod = (
                    client.table("staging_products")
                    .select("*")
                    .eq("id", pid)
                    .single()
                    .execute()
                ).data

                # 3) Human-friendly summary
                changed_labels = [FIELD_LABELS.get(k, k) for k in changed.keys()]
                st.success(f"Saved ✔  Updated: {', '.join(changed_labels)}")

                with st.expander("See details of what changed"):
                    for k, diffv in changed.items():
                        st.write(f"**{FIELD_LABELS.get(k, k)}**")
                        st.write(f"• Before: {diffv['before']}")
                        st.write(f"• After:  {diffv['after']}")
                        st.write("---")

                # keep current selection and refresh the form with new values
                st.session_state["selected_product_id"] = pid
                st.query_params["pid"] = pid
                st.rerun()

            except Exception as e:
                st.error("Save failed.")
                st.exception(e)


        

# --- Assets section ---
st.subheader("Assets")
assets = (
    client.table("staging_assets")
    .select("id, asset_type, content_category, file_url, file_name, keep_asset, description, title")
    .eq("staging_product_id", pid)
    .order("created_at", desc=True)
    .execute()
    .data
    or []
)

if not assets:
    st.caption("No assets linked.")
else:
    for a in assets:
        with st.expander(f"{a.get('file_name') or 'unnamed'}  •  {a.get('asset_type','?')}", expanded=False):
            c1, c2, c3 = st.columns([3, 1, 1])
            with c1:
                st.write(a.get("file_url") or "")
                st.write(a.get("title") or "")
                st.write(a.get("description") or "")
            with c2:
                keep_val = st.checkbox("Keep", value=bool(a.get("keep_asset")), key=f"keep_{a['id']}")
            with c3:
                cat_opts = ["", "regulatory", "clinical", "marketing", "datasheet", "whitepaper", "image", "video"]
                cat_idx = 0 if not a.get("content_category") else cat_opts.index(a.get("content_category"))
                cat_val = st.selectbox("Category", options=cat_opts, index=cat_idx, key=f"cat_{a['id']}")

            if st.button("Save asset", key=f"save_{a['id']}"):
                try:
                    client.table("staging_assets").update(
                        {"keep_asset": keep_val, "content_category": cat_val or None}
                    ).eq("id", a["id"]).execute()
                    st.success("Asset saved.")
                except Exception as e:
                    st.error("Asset save failed.")
                    st.exception(e)

st.divider()
c1, c2, c3 = st.columns(3)
if c1.button("✅ Approve for Global Library", type="primary"):
    client.table("staging_products").update({"review_status": "approved"}).eq("id", pid).execute()
    st.success("Marked as approved.")
    st.rerun()
if c2.button("🕓 Mark In Review"):
    client.table("staging_products").update({"review_status": "in_review"}).eq("id", pid).execute()
    st.rerun()
if c3.button("⛔ Reject"):
    client.table("staging_products").update({"review_status": "rejected"}).eq("id", pid).execute()
    st.rerun()
