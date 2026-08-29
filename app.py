import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import io

# Page Config
st.set_page_config(page_title="202 Marketing Dashboard", layout="wide")

# CSS Injection
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');
html, body, [class*="css"] {
    font-family: 'Source Sans Pro', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# LOADING DATA AND CACHING
@st.cache_data
def load_data():
    df = pd.read_csv("final_data_sample.csv", parse_dates=["production_date"])
    return df

# DATE FILTER
def filter_data_by_date(df):
    """Filter the data based on the selected date range."""
    min_date = df['production_date'].min().date()
    max_date = df['production_date'].max().date()

    date_selection = st.date_input(
        "Select the production date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_selection) != 2:
        st.stop()

    start, end = date_selection
    return df[df['production_date'].dt.date.between(start, end)]

# RENDERING FUNCTIONS
def render_tab_overview(df):
    st.header("Company 202 -- KPI Overview")

    if df.empty:
        st.info("No data available.")
        return
    
    # CALCULATING METRICS
    total_parts = len(df)
    parts_202 = len(df[df["manufacturer"] == 202])
    market_share = round(parts_202/total_parts * 100, 2)
    engines_total = df["engine_id"].nunique()
    engines_with_202 = df[df["manufacturer"] == 202]["engine_id"].nunique()
    penetration_percentage = round(engines_with_202 / engines_total * 100, 2)
    every_xth = round(engines_total / engines_with_202, 2)
    
    # RENDERING METRICS
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total parts (202)", f"{parts_202:,}")
    col2.metric("Market share (202)", f"{market_share}%")
    col3.metric("Engine penetration", f"{penetration_percentage}%")
    col4.metric("Slogan", f"Every {every_xth}th engine")
    
def render_tab_market_share(df):
    st.header("Market Share Analysis")

    if df.empty:
        st.info("No data available.")
        return
    
    # Grouped Bar Chart
    df_copy = df.copy()
    df_copy["group"] = df_copy["manufacturer"].apply(lambda x: "202" if x == 202 else "Competition")
    market_df = df_copy.groupby(["part_type", "group"]).size().reset_index(name="count")
    
    bar_chart = px.bar(
        market_df,
        x="part_type", y="count", color="group",
        barmode="group",
        title="Parts Produced: 202 vs. Competition",
        labels={"count": "Number of Parts", "part_type": "Part Type", "group": "Manufacturer"},
        color_discrete_map={"202": "#ADD8E6", "Competition": "#CCCCCC"}
    )
    st.plotly_chart(bar_chart, use_container_width=True)

    
    # TOTAL PIE Chart
    market_share_fig = px.pie(data_frame=data, names='manufacturer', title='Market Share by Brand')
    st.plotly_chart(market_share_fig)
    
    # Pie Chart
    selected_part = st.selectbox("Select a part type for detail view", df["part_type"].unique())
    part_df = df_copy[df_copy["part_type"] == selected_part]
    pie_df = part_df.groupby("group").size().reset_index(name="count")

    fig_pie = px.pie(
        pie_df, values="count", names="group",
        title=f"Market Share for {selected_part}",
        color_discrete_map={"202": "#ADD8E6", "Competition": "#CCCCCC"}
    )
    st.plotly_chart(fig_pie, use_container_width=True)
        
def render_tab_engine_penetration(df):
    st.title("Engine Penetration")
    st.caption("Shows the penetration of different engine types.")
    #engine_penetration_fig = px.histogram(data_frame=data, x='engine_type', title='Engine Penetration')
    #st.plotly_chart(engine_penetration_fig)
    
def render_quality_analysis(df):
    st.title("Quality Analysis")
    st.caption("Shows the quality metrics of the products.")
    
def render_tab_data_table(df):
    st.title("Data Table")
    st.caption("Shows the filtered data used for analysis.")
    st.dataframe(data.head())
    
def render_tab_debugging(df):
    st.title("Debugging")
    st.caption("Debugging information for developers.")
    st.write(data.dtypes)           # Datentypen pruefen
    st.write(data.head())           # Erste Zeilen ansehen
    #st.write(type(data["production_date"]))    # Typ einer Variable pruefen
    st.write(data.shape)            # Anzahl Zeilen/Spalten


# Loading the data
data = load_data()

# SIDEBAR
with st.sidebar:
    st.image("www/logo.png")
    st.title("Production Data Dashboard")
    st.write("Marketing Analysis in our 202 company")
    # Filter data by date range
    data = filter_data_by_date(data)


# Create tabs for different sections of the dashboard
tab_overview, tab_market_share, tab_engine_penetration, tab_quality_analysis, tab_data_table, tab_debugging = st.tabs([
    "Overview", "Market share", "Engine penetration", "Quality analysis", "Data table", "Debugging"])


# OVERVIEW
with tab_overview:
    render_tab_overview(data)

# MARKET SHARE
with tab_market_share:
    render_tab_market_share(data)
    
# ENGINE PENETRATION
with tab_engine_penetration:
    render_tab_engine_penetration(data)

# QUALITY ANALYSIS
with tab_quality_analysis:
    render_quality_analysis(data)
    
# DATA TABLE
with tab_data_table:
    render_tab_data_table(data)

# DEBUGGING
with tab_debugging:
    render_tab_debugging(data)


