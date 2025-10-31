# pages/Products.py
import streamlit as st
from supabase_client import sb
from datetime import datetime

st.set_page_config(page_title="Product Browser", layout="wide")
st.title("🧭 Product Browser")

client = sb()

# ── Filters ──────────────────────────────────────────────────────────────────
# Pull all manufacturers (no RPC)
resp = client.table("staging_products").select("manufacturer").execute()
all_mfrs = sorted({(r.get("manufacturer") or "").strip() for r in (resp.data or []) if (r.get("manufacturer") or "").strip()})
manufacturer = st.selectbox("Manufacturer", options=["(All)"] + all_mfrs, index=0)

status = st.selectbox("Review status", options=["(All)", "pending", "in_review", "approved", "rejected"], index=0)
q = st.text_input("Search (name / description contains)")

# ── Query with filters ────────────────────────────────────────────────────────
qrb = client.table("staging_products").select(
    "id, product_name, manufacturer, category, completeness_score, review_status, created_at, updated_at"
).order("updated_at", desc=True)

if manufacturer != "(All)":
    qrb = qrb.eq("manufacturer", manufacturer)
if status != "(All)":
    qrb = qrb.eq("review_status", status)
if q:
    # simple contains on 2 fields
    qrb = qrb.or_(f"product_name.ilike.%{q}%,description.ilike.%{q}%")

data = (qrb.execute().data) or []

# ── Paging ───────────────────────────────────────────────────────────────────
page_size = 20
total = len(data)
page = st.number_input("Page", min_value=1, value=1, step=1)
start, end = (page - 1) * page_size, (page - 1) * page_size + page_size
page_rows = data[start:end]
st.caption(f"Showing {start+1}-{min(end, total)} of {total}")

# ── Render table + selector ──────────────────────────────────────────────────
import pandas as pd
if page_rows:
    df = pd.DataFrame(page_rows)
    df_view = df.rename(columns={
        "product_name": "Product",
        "manufacturer": "Manufacturer",
        "category": "Category",
        "completeness_score": "Score",
        "review_status": "Status",
        "created_at": "Created",
        "updated_at": "Updated",
    })[["Product","Manufacturer","Category","Score","Status","Updated","id"]]
    # show id but keep it at the end
    st.dataframe(df_view, use_container_width=True, hide_index=True)

    chosen_id = st.selectbox(
        "Select a product to open",
        options=["(None)"] + [r["id"] for r in page_rows],
        format_func=lambda v: "(None)" if v == "(None)" else next((r["product_name"] for r in page_rows if r["id"]==v), v)
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Open in Editor", type="primary", disabled=(chosen_id=="(None)")):
            st.session_state["selected_product_id"] = chosen_id
            st.query_params["pid"] = chosen_id       
            st.switch_page("pages/Product_Detail.py")
    with col2:
        if st.button("Refresh"):
            st.rerun()
else:
    st.info("No rows found with current filters.")
