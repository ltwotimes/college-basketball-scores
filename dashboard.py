# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
import altair as alt

# ------------------------------------------------------------
# Streamlit Page Setup
# ------------------------------------------------------------
st.set_page_config(
    page_title="🏀 College Basketball Scores Dashboard",
    layout="wide",
)

# ------------------------------------------------------------
# 1️⃣ Load and Cache the Data
# ------------------------------------------------------------
@st.cache_data(ttl=600)
def load_data(csv_path):
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df["margin"] = pd.to_numeric(df["margin"], errors="coerce")
    df["ot"] = df["ot"].astype(bool)
    return df.dropna(subset=["date", "home_team", "away_team"])

CSV_PATH = "C:/Users/lanza/OneDrive/Desktop/college-basketball-scores/scores_clean.csv"

if not os.path.exists(CSV_PATH):
    st.error("❌ scores_clean.csv not found. Run the scraper first.")
    st.stop()

df = load_data(CSV_PATH)

# ------------------------------------------------------------
# 2️⃣ Data Cleanup
# ------------------------------------------------------------
numeric_cols = ["games", "total", "margin", "home", "away"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["total", "margin"], how="any")
df["margin"] = df["margin"].abs().astype(int)

# ------------------------------------------------------------
# 3️⃣ Header and Description
# ------------------------------------------------------------
st.title("🏀 College Basketball Scores Dashboard")
st.markdown(
    """
    Explore 25 years of men's college basketball scores — filter by season, 
    analyze **total-point** and **margin** frequency, and visualize how 
    scoring ranges correspond to game competitiveness.
    """
)

last_updated = datetime.fromtimestamp(os.path.getmtime(CSV_PATH))
st.caption(f"Data updated: {last_updated.strftime('%Y-%m-%d %H:%M:%S')} (local time)")
st.divider()

# ------------------------------------------------------------
# 4️⃣ Sidebar Filters
# ------------------------------------------------------------
with st.sidebar:
    st.header("Filters")
    years = sorted(df["date"].dt.year.unique())
    selected_years = st.multiselect(
        "Select Years",
        options=years,
        default=years,
    )

    min_total = int(df["total"].min())
    max_total = int(df["total"].max())
    total_range = st.slider(
        "Filter by Total Points",
        min_value=min_total,
        max_value=max_total,
        value=(min_total, max_total),
    )

filtered_df = df[
    (df["date"].dt.year.isin(selected_years))
    & (df["total"].between(total_range[0], total_range[1]))
]

# ------------------------------------------------------------
# 🧠 5️⃣ Quick Insights Summary (Collapsible)
# ------------------------------------------------------------
with st.expander("📊 Show / Hide Quick Insights", expanded=True):
    if len(filtered_df) > 0:
        most_common_total = (
            filtered_df["total"].value_counts().idxmax()
            if not filtered_df["total"].empty
            else None
        )
        total_pct = (
            filtered_df["total"].value_counts(normalize=True).max() * 100
            if not filtered_df["total"].empty
            else 0
        )
        most_common_margin = (
            filtered_df["margin"].value_counts().idxmax()
            if not filtered_df["margin"].empty
            else None
        )
        margin_pct = (
            filtered_df["margin"].value_counts(normalize=True).max() * 100
            if not filtered_df["margin"].empty
            else 0
        )

        avg_total = filtered_df["total"].mean()
        avg_margin = filtered_df["margin"].mean()
        total_games = len(filtered_df)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🏆 Most Common Total", f"{int(most_common_total)} pts", f"{total_pct:.2f}% of games")
        col2.metric("🧩 Most Common Margin", f"{int(most_common_margin)} pts", f"{margin_pct:.2f}% of games")
        col3.metric("⚙️ Avg Total", f"{avg_total:.1f}")
        col4.metric("🎮 Games Analyzed", f"{total_games:,}")
    else:
        st.info("No games match the current filters.")

st.divider()

# ------------------------------------------------------------
# 6️⃣ Frequency Tables
# ------------------------------------------------------------
freq_total = (
    filtered_df["total"]
    .value_counts()
    .rename_axis("Total Points")
    .reset_index(name="Games")
)
freq_total["Percent"] = (freq_total["Games"] / len(filtered_df) * 100).round(2)
freq_total = freq_total.sort_values("Percent", ascending=False)[
    ["Games", "Total Points", "Percent"]
]

freq_margin = (
    filtered_df["margin"]
    .value_counts()
    .rename_axis("Margin")
    .reset_index(name="Games")
)
freq_margin["Percent"] = (freq_margin["Games"] / len(filtered_df) * 100).round(2)
freq_margin = freq_margin.sort_values("Percent", ascending=False)[
    ["Games", "Margin", "Percent"]
]

# ------------------------------------------------------------
# 7️⃣ Chart/Table Toggle
# ------------------------------------------------------------
view_option = st.radio(
    "Select View:",
    ["📊 Chart", "📋 Table"],
    horizontal=True,
    key="view_selector",
)

# ------------------------------------------------------------
# 8️⃣ TOTAL POINTS SECTION
# ------------------------------------------------------------
st.subheader("Total Points Frequency (2000–2025)")

if view_option == "📊 Chart":
    chart_total = (
        alt.Chart(freq_total)
        .mark_bar()
        .encode(
            x=alt.X("Total Points:O", sort=None, title="Total Points"),
            y=alt.Y("Games:Q", title="Number of Games"),
            tooltip=[
                alt.Tooltip("Total Points:O"),
                alt.Tooltip("Games:Q"),
                alt.Tooltip("Percent:Q", format=".2f"),
            ],
        )
        .properties(height=520)
        .interactive()
    )
    st.altair_chart(chart_total, use_container_width=True)
else:
    st.markdown(
        """
        <style>
            [data-testid="stDataFrame"] table {
                font-size: 1.05rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(
        freq_total.style.background_gradient(
            subset=["Percent"], cmap="Greens"
        ).format({"Percent": "{:.2f}%"}),
        hide_index=True,
        height=580,
        use_container_width=True,
    )

st.divider()

# ------------------------------------------------------------
# 9️⃣ MARGIN SECTION
# ------------------------------------------------------------
st.subheader("Margin Frequency (2000–2025)")

if view_option == "📊 Chart":
    chart_margin = (
        alt.Chart(freq_margin)
        .mark_bar()
        .encode(
            x=alt.X("Margin:O", sort=None, title="Margin (Points)"),
            y=alt.Y("Games:Q", title="Number of Games"),
            tooltip=[
                alt.Tooltip("Margin:O"),
                alt.Tooltip("Games:Q"),
                alt.Tooltip("Percent:Q", format=".2f"),
            ],
        )
        .properties(height=520)
        .interactive()
    )
    st.altair_chart(chart_margin, use_container_width=True)
else:
    st.markdown(
        """
        <style>
            [data-testid="stDataFrame"] table {
                font-size: 1.05rem !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(
        freq_margin.style.background_gradient(
            subset=["Percent"], cmap="Blues"
        ).format({"Percent": "{:.2f}%"}),
        hide_index=True,
        height=580,
        use_container_width=True,
    )

st.divider()

# ------------------------------------------------------------
# 🔟 TOTAL vs MARGIN CORRELATION (Dual-Axis)
# ------------------------------------------------------------
st.subheader("Total Points vs. Margin Relationship (2000–2025)")

avg_margin_per_total = (
    filtered_df.groupby("total")["margin"].agg(["mean", "count"]).reset_index()
)
avg_margin_per_total.rename(
    columns={"total": "Total Points", "mean": "Avg Margin", "count": "Games"},
    inplace=True,
)
avg_margin_per_total = avg_margin_per_total[avg_margin_per_total["Games"] >= 10]

base = alt.Chart(avg_margin_per_total).encode(x=alt.X("Total Points:O", title="Total Points"))

bar = base.mark_bar(color="#5DADE2").encode(
    y=alt.Y("Games:Q", title="Number of Games"),
    tooltip=[
        alt.Tooltip("Total Points:O"),
        alt.Tooltip("Games:Q"),
        alt.Tooltip("Avg Margin:Q", format=".2f"),
    ],
)

line = base.mark_line(color="#27AE60", strokeWidth=2).encode(
    y=alt.Y("Avg Margin:Q", title="Average Margin (Points)", axis=alt.Axis(titleColor="#27AE60")),
)

chart = alt.layer(bar, line).resolve_scale(y="independent").properties(height=440)
st.altair_chart(chart, use_container_width=True)

st.divider()

# ------------------------------------------------------------
# 11️⃣ HEATMAP — Totals vs Margins Frequency
# ------------------------------------------------------------
st.subheader("Total Points vs. Margin Heatmap (Game Frequency)")

heat_df = (
    filtered_df.groupby(["total", "margin"])
    .size()
    .reset_index(name="Games")
    .query("Games >= 2")
)

heatmap = (
    alt.Chart(heat_df)
    .mark_rect()
    .encode(
        x=alt.X("total:O", title="Total Points"),
        y=alt.Y("margin:O", title="Margin (Points)"),
        color=alt.Color("Games:Q", scale=alt.Scale(scheme="inferno"), title="Games"),
        tooltip=[
            alt.Tooltip("total:O", title="Total Points"),
            alt.Tooltip("margin:O", title="Margin"),
            alt.Tooltip("Games:Q", title="Games"),
        ],
    )
    .properties(height=520)
    .interactive()
)
st.altair_chart(heatmap, use_container_width=True)

st.divider()

# ------------------------------------------------------------
# 12️⃣ SCORING TREND OVER TIME (Fixed)
# ------------------------------------------------------------
st.subheader("Scoring Trends Over Time (2000–2025)")

trend_df = (
    df.groupby(df["date"].dt.year)[["total", "margin"]]
    .mean()
    .reset_index()
    .rename(columns={"date": "Year", "total": "Avg Total", "margin": "Avg Margin"})
)

trend_chart = (
    alt.Chart(trend_df)
    .transform_fold(
        ["Avg Total", "Avg Margin"], as_=["Metric", "Value"]
    )
    .mark_line(point=True)
    .encode(
        x=alt.X("Year:O", title="Season"),
        y=alt.Y("Value:Q", title="Average Points / Margin"),
        color=alt.Color("Metric:N", scale=alt.Scale(scheme="set1"), title="Metric"),
        tooltip=[
            alt.Tooltip("Year:O", title="Season"),
            alt.Tooltip("Metric:N", title="Type"),
            alt.Tooltip("Value:Q", format=".2f", title="Value"),
        ],
    )
    .properties(height=460)
    .interactive()
)
st.altair_chart(trend_chart, use_container_width=True)

st.divider()

# ------------------------------------------------------------
# 13️⃣ Summary Metrics (Footer)
# ------------------------------------------------------------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Games in View", f"{len(filtered_df):,}")
col2.metric("Average Total", f"{filtered_df['total'].mean():.1f}")
col3.metric("Average Margin", f"{filtered_df['margin'].mean():.1f}")
col4.metric("OT Games", f"{filtered_df['ot'].sum():,}")

st.divider()

# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------
st.caption(
    "Data source: Sports-Reference.com | Automatically updated nightly via scraper pipeline."
)
