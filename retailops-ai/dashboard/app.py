"""Streamlit operational application: live KPIs + human-reviewed exception workflow."""
import os
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="RetailOps AI", page_icon="📊", layout="wide")
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
API_KEY = os.getenv("API_KEY", "")
TIMEOUT = 12


@st.cache_data(ttl=25, show_spinner=False)
def api_get(path: str, region: str | None = None, status: str | None = None):
    params = {}
    if region and region != "All regions":
        params["region"] = region
    if status and status != "All":
        params["status"] = status
    response = requests.get(f"{API_BASE}{path}", params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def api_write(path: str, data: dict | None = None, method: str = "PATCH", region: str | None = None):
    params = {"region": region} if region and region != "All regions" else {}
    response = requests.request(
        method, f"{API_BASE}{path}", params=params,
        headers={"X-API-Key": API_KEY}, json=data, timeout=25,
    )
    if not response.ok:
        try:
            message = response.json().get("detail", response.text)
        except ValueError:
            message = response.text
        raise ValueError(f"API returned {response.status_code}: {message}")
    return response.json()


st.title("RetailOps AI")
st.caption("Multi-site operational intelligence · Fictional retail dataset · Human-supervised issue management")
with st.sidebar:
    st.header("Filters & tools")
    region = st.selectbox("Region", ["All regions", "Germany", "France", "Netherlands"])
    if st.button("Refresh data"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.info("Automatic issue detection uses reproducible rules. Optional LLM insights are explicitly triggered, not run on every page load.")

try:
    report = api_get("/api/metrics", region)
    issues = api_get("/api/issues", region)
    insight = api_get("/api/insights", region)
except requests.RequestException as exc:
    st.error(f"Could not reach backend at {API_BASE}. Start the API first. ({exc})")
    st.stop()

summary = report["summary"]
tab1, tab2, tab3 = st.tabs(["📈 Dashboard", "🛠 Issue review", "🧠 Evidence-based insights"])

with tab1:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Revenue (EUR)", f"€{summary['revenue_eur']:,.0f}")
    col2.metric("Inventory accuracy", f"{summary['inventory_accuracy_pct']:.1f}%" if summary["inventory_accuracy_pct"] is not None else "N/A")
    col3.metric("On-time deliveries", f"{summary['on_time_delivery_pct']:.1f}%" if summary["on_time_delivery_pct"] is not None else "N/A")
    col4.metric("Active exceptions", summary["active_issues"])
    col5.metric("Stores", summary["stores_tracked"])
    left, right = st.columns(2)
    df = pd.DataFrame(report["by_store"])
    daily = pd.DataFrame(report["daily_sales"])
    with left:
        st.subheader("Sales trend")
        if not daily.empty:
            fig = px.line(daily, x="date", y="revenue_eur", markers=True,
                          labels={"date": "Day", "revenue_eur": "Revenue (EUR)"})
            st.plotly_chart(fig, use_container_width=True)
    with right:
        st.subheader("Exceptions by store")
        if not df.empty:
            fig = px.bar(df.sort_values("active_issues"), x="active_issues", y="store_name",
                         color="region", orientation="h", labels={"active_issues": "Active issues", "store_name": "Store"})
            st.plotly_chart(fig, use_container_width=True)
    st.subheader("Operational drilldown")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    with st.expander("Metric definitions"):
        for key, definition in report["definitions"].items():
            st.write(f"**{key}:** {definition}")

with tab2:
    st.subheader("Exception review queue")
    st.write("Issues are detected automatically but can only be resolved through a documented, authenticated human workflow.")
    status_filter = st.selectbox("Status filter", ["All", "OPEN", "IN_REVIEW", "RESOLVED", "DISMISSED"])
    filtered = [issue for issue in issues if status_filter == "All" or issue["status"] == status_filter]
    if filtered:
        shown = pd.DataFrame(filtered)[["id", "store_name", "kind", "severity", "status", "description"]]
        st.dataframe(shown, use_container_width=True, hide_index=True)
        labels = {f"{i['store_name']} · {i['kind']} · {i['id'][:8]}": i for i in filtered}
        selected_label = st.selectbox("Select issue to review", list(labels))
        selected = labels[selected_label]
        st.info(selected["description"])
        allowed = {"OPEN": ["IN_REVIEW", "DISMISSED"],
                   "IN_REVIEW": ["RESOLVED", "DISMISSED"],
                   "RESOLVED": [], "DISMISSED": []}[selected["status"]]
        if allowed:
            with st.form("issue_update"):
                next_status = st.selectbox("Next status", allowed)
                actor = st.text_input("Reviewer name / team ID", placeholder="e.g. regional-ops-reviewer")
                note = st.text_area("Review evidence / resolution note (min 10 characters)")
                submitted = st.form_submit_button("Save reviewed decision")
                if submitted:
                    if not API_KEY:
                        st.error("Configure API_KEY to enable status changes.")
                    else:
                        try:
                            result = api_write(f"/api/issues/{selected['id']}",
                                               {"status": next_status, "actor": actor, "note": note})
                            st.success(f"Updated issue to {result['status']}; audit event recorded")
                            st.cache_data.clear()
                        except (ValueError, requests.RequestException) as exc:
                            st.error(str(exc))
        else:
            st.caption("This issue is in a terminal state and cannot be changed.")
        if st.checkbox("Show audit events for selected issue"):
            if API_KEY:
                try:
                    r = requests.get(f"{API_BASE}/api/issues/{selected['id']}/audit",
                                     headers={"X-API-Key": API_KEY}, timeout=TIMEOUT)
                    r.raise_for_status()
                    st.dataframe(pd.DataFrame(r.json()), use_container_width=True)
                except requests.RequestException as exc:
                    st.error(str(exc))
            else:
                st.warning("API_KEY required for viewing audit events.")
    else:
        st.success("No issues found for this filter.")

with tab3:
    st.subheader("Rule-based operational insight")
    st.write(f"**{insight['headline']}**")
    st.write(insight["summary"])
    for rec in insight["recommendations"]:
        st.write(f"• {rec}")
    st.divider()
    st.subheader("Optional AI-generated management narrative")
    st.caption("Requires OPENAI_API_KEY on the API server. A model call happens only when this button is clicked and may incur API charges.")
    if st.button("Generate an AI summary"):
        if not API_KEY:
            st.error("Configure API_KEY first.")
        else:
            try:
                generated = api_write("/api/insights/ai", method="POST", region=region)
                st.write(f"**{generated['headline']}**")
                st.write(generated["summary"])
                for rec in generated["recommendations"]:
                    st.write(f"• {rec}")
                st.warning(generated["caution"])
            except (ValueError, requests.RequestException) as exc:
                st.error(str(exc))
