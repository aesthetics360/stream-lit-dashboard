# pages/1_📊_Dashboard.py
import streamlit as st
from supabase_client import sb

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Dashboard")

client = sb()

# Basic KPIs
prod = client.table("staging_products").select("id,review_status,manufacturer,completeness_score").execute().data or []
assets = client.table("staging_assets").select("id,keep_asset,promoted_to_gl").execute().data or []
alerts = client.table("staging_validation_log").select("id,severity").execute().data or []

total_products = len(prod)
approved = sum(1 for p in prod if p.get("review_status")=="approved")
pending  = sum(1 for p in prod if p.get("review_status")=="pending")
rejected = sum(1 for p in prod if p.get("review_status")=="rejected")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Products", total_products)
col2.metric("Approved", approved)
col3.metric("Pending", pending)
col4.metric("Rejected", rejected)

st.subheader("Manufacturers (Top 10)")
from collections import Counter
mf = Counter([p.get("manufacturer") or "—" for p in prod])
st.table({"Manufacturer": list(mf.keys())[:10], "Count": list(mf.values())[:10]})

st.subheader("Asset Summary")
kept = sum(1 for a in assets if a.get("keep_asset"))
gl = sum(1 for a in assets if a.get("promoted_to_gl"))
c1, c2 = st.columns(2)
c1.metric("Assets (Kept)", kept)
c2.metric("Assets Promoted", gl)

st.subheader("Validation Alerts")
warn = sum(1 for a in alerts if a.get("severity")=="warning")
err  = sum(1 for a in alerts if a.get("severity")=="error")
w1, w2 = st.columns(2)
w1.metric("Warnings", warn)
w2.metric("Errors", err)
