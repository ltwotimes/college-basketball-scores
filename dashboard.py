import streamlit as st
import pandas as pd
from datetime import datetime
import numpy as np

# --- PAGE SETUP ---
st.set_page_config(page_title="College Basketball Score Dashboard", layout="wide")

@st.cache_data(ttl=300)
def load_data():
    df = pd.read_csv("scores.csv")
    df["date"] = pd.to_datetime(df["date"])
    df["season"] = np.where(df["date"].dt.month >= 11, df["date"].dt.year, df["date"].dt.year - 1)
    df["era"] = pd.cut(df["season"], bins=[1999, 2009, 2019, 2030],
                       labels=["2000s", "2010s", "2020s"], include_lowest=True)
    return df

df = load_data()
df = df.sample(frac=1.0)  # randomize order to speed up some visuals


# --- SIDEBAR FILTERS ---
st.sidebar.title("🏀 Filters")

season_options = sorted(df["season"].unique(), reverse=True)
selected_seasons = st.sidebar.multiselect("Select Season(s)", season_options, default=season_options)

selected_eras = st.sidebar.multiselect(
    "Select Era(s)",
    df["era"].dropna().unique(),
    default=df["era"].dropna().unique()
)

df_filtered = df[df["season"].isin(selected_seasons) & df["era"].isin(selected_eras)]

st.title("🏀 College Basketball Score Analytics Dashboard")
st.caption(f"Data last updated: {df['date'].max().date()} — {len(df):,} total games")

# ================================
# SCORE FREQUENCY ANALYSIS
# ================================
st.header("📊 Score Totals by Frequency")

freq = df_filtered["total"].value_counts().reset_index()
freq.columns = ["Total", "Games"]
freq["Percent"] = (freq["Games"] / freq["Games"].sum() * 100).round(2)

top_n = st.slider("Show Top N Totals", 5, 100, 20)
freq_top = freq.head(top_n)

col1, col2 = st.columns(2)
with col1:
    st.dataframe(freq_top, use_container_width=True)
with col2:
    st.bar_chart(freq_top.set_index("Total")["Percent"])

st.divider()

# ================================
# OVER/UNDER SIMULATOR
# ================================
st.header("🎯 Over/Under Simulator")

line_value = st.number_input("Enter Game Total Line (e.g., 145.5)", min_value=100.0, max_value=220.0, value=145.5, step=0.5)

over_pct = (df_filtered["total"] > line_value).mean() * 100
under_pct = (df_filtered["total"] < line_value).mean() * 100
push_pct = (df_filtered["total"] == line_value).mean() * 100

col1, col2, col3 = st.columns(3)
col1.metric("Over %", f"{over_pct:.2f}%")
col2.metric("Under %", f"{under_pct:.2f}%")
col3.metric("Push %", f"{push_pct:.2f}%")

st.caption("Calculated using all filtered games in dataset.")

st.divider()

# ================================
# SPREAD / MARGIN ANALYSIS
# ================================
st.header("📈 Spread / Margin Analysis")

margin_freq = df_filtered["margin"].value_counts().reset_index()
margin_freq.columns = ["Margin", "Games"]
margin_freq["Percent"] = (margin_freq["Games"] / margin_freq["Games"].sum() * 100).round(2)
margin_freq_sorted = margin_freq.sort_values("Margin")

col1, col2 = st.columns(2)
with col1:
    st.dataframe(margin_freq_sorted, use_container_width=True)
with col2:
    st.line_chart(margin_freq_sorted.set_index("Margin")["Percent"])

st.caption("Margins represent home team’s score minus away team’s score.")

st.divider()

# ================================
# ERA AND TREND VISUALS
# ================================
st.header("🏆 Scoring Trends Over Time")

trend = df_filtered.groupby("season")["total"].mean().reset_index()
st.line_chart(trend.set_index("season"), use_container_width=True)

st.header("📅 Average Scoring by Era")
era_means = df_filtered.groupby("era")["total"].mean().reset_index()
st.bar_chart(era_means.set_index("era")["total"], use_container_width=True)

st.divider()

# ================================
# EXPORT FEATURE
# ================================
st.header("💾 Export Filtered Data")

csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    label="Download Filtered Dataset (CSV)",
    data=csv,
    file_name=f"cbb_filtered_{datetime.now().date()}.csv",
    mime="text/csv"
)

st.caption("Exports the dataset as currently filtered by season and era.")

# ================================
# AUTO REFRESH
# ================================
st.sidebar.markdown("### 🔄 Auto Refresh")
refresh_rate = st.sidebar.slider("Refresh every (seconds)", 0, 600, 0)
if refresh_rate > 0:
    st.experimental_rerun()

st.sidebar.info("Dashboard updates live from scores.csv after each nightly scrape.")
