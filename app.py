import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Page Config
st.set_page_config(page_title="202 Marketing Dashboard", layout="wide")

#Colors
color_202 = "#ADD8E6"
group_colors = {"202": color_202, "Competition": "#CCCCCC"}
manufacturer_colors = {202: color_202, 201: "#B0C4DE", 203: "#D3D3D3", 204: "#C0C0C0"}
single_color = "#ADD8E6"

#Axis Labels
labels = {
    "count": "Number of Parts",
    "part_type": "Part Type",
    "group": "Manufacturer",
    "defect_rate_%": "Defect Rate (%)",
    "engine_type": "Engine Type"
}

#Plotting Functions
def plot_bar(df, x, y, title, color = None, colors = group_colors, orientation = "v"):
    fig = px.bar (
        df, x = x, y = y, color = color, orientation = orientation, barmode = "group", 
        title = title, labels = labels, color_discrete_map = colors, color_discrete_sequence = [color_202],
    )
    st.plotly_chart(fig, width = "stretch")
    
    return fig

def plot_pie(df, names, title, values = None, colors = group_colors):
    fig = px.pie (
        df, names = names, values = values, color = names, title = title, color_discrete_map = colors
    )
    st.plotly_chart(fig, width = "stretch")

    return fig
    
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
    csv = False
    
    # To swap from csv to parquet import
    if csv == True:
        df = pd.read_csv("additional_files/final_data_group_14.csv", parse_dates=["production_date"])
        string_cols = df.select_dtypes(include=["string", "object"]).columns
        for col in string_cols:
            df[col] = df[col].astype(object)
    else:
        df = pd.read_parquet("additional_files/final_data_group_14.parquet")
        
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

# CALCULATING FUNCTIONS (and caching them)
@st.cache_data
def calc_overview_metrics(df):
    total_parts = len(df)
    parts_202 = len(df[df["manufacturer"] == 202])
    market_share = round(parts_202 / total_parts * 100, 2)
    engines_total = df["engine_id"].nunique()
    engines_with_202 = df[df["manufacturer"] == 202]["engine_id"].nunique()
    penetration_percentage = round(engines_with_202 / engines_total * 100, 2)
    every_xth = round(engines_total / engines_with_202, 2)
    oem1_df = df[df["OEM_type"] == 1]
    oem1_parts_202 = len(oem1_df[oem1_df["manufacturer"] == 202])
    oem1_total = len(oem1_df)
    faulty_202 = df[(df["manufacturer"] == 202) & (df["faulty"] == 1)]
    defect_rate = round(len(faulty_202) / parts_202 * 100, 2) if parts_202 > 0 else 0
    part_types_202 = df[df["manufacturer"] == 202]["part_type"].nunique()
    return market_share, penetration_percentage, every_xth, parts_202, part_types_202, oem1_parts_202, oem1_total, defect_rate

@st.cache_data
def calc_market_share(df):
    group = np.where(df["manufacturer"] == 202, "202", "Competition")
    market_df = df.assign(group=group).groupby(["part_type", "group"]).size().reset_index(name="count")
    manufacturer_df = df.groupby("manufacturer").size().reset_index(name="count")
    return market_df, manufacturer_df

@st.cache_data
def calc_engine_penetration(df):
    from_202 = len(df[df["manufacturer"] == 202])
    total = len(df)
    total_per_type = df.groupby("engine_type")["engine_id"].nunique()
    with_202_per_type = df[df["manufacturer"] == 202].groupby("engine_type")["engine_id"].nunique()
    pen_df = pd.DataFrame({
        "Total Engines": total_per_type,
        "Engines with 202": with_202_per_type
    }).fillna(0)
    pen_df["Penetration %"] = round(pen_df["Engines with 202"] / pen_df["Total Engines"] * 100, 2)
    pen_df["Every x-th"] = round(pen_df["Total Engines"] / pen_df["Engines with 202"], 2).replace(float("inf"), 0)
    pen_df = pen_df.reset_index()
    pen_df["engine_type"] = pen_df["engine_type"].astype(str)
    presence = df.groupby(["engine_type", "part_type"]).size().unstack(fill_value=0)
    presence = (presence > 0).astype(int)
    return from_202, total, pen_df, presence

@st.cache_data
def calc_quality_stats(df):
    oem1_df = df[df["OEM_type"] == 1].copy()
    oem1_df["group"] = np.where(oem1_df["manufacturer"] == 202, "202", "Competition")
    defect_stats = oem1_df.groupby(["part_type", "group"]).agg(
        total=("faulty", "count"),
        faulty=("faulty", "sum")
    ).reset_index()
    defect_stats["defect_rate_%"] = round(defect_stats["faulty"] / defect_stats["total"] * 100, 2)
    return oem1_df, defect_stats


# RENDERING FUNCTIONS
def render_tab_overview(df):
    t = time.time()
    st.header("Company 202 -- KPI Overview")

    if df.empty:
        st.info("No data available.")
        return
    
    market_share, penetration_percentage, every_xth, parts_202, part_types_202, oem1_parts_202, oem1_total, defect_rate = calc_overview_metrics(df)
    
    # RENDERING METRICS
    col1, col2, col3 = st.columns(3)
    col1.metric("Market share (202)", f"{market_share}%")
    col2.metric("Engine penetration", f"{penetration_percentage}%")
    col3.metric("Slogan", f"In every {every_xth}th engine")
    
    col4, col5, col6, col7 = st.columns(4)
    col4.metric("Total parts (202)", f"{parts_202:,}")
    col5.metric("Part types (202)", f"{part_types_202}")
    col6.metric("OEM1 volume (202)", f"{oem1_parts_202:,} / {oem1_total:,}")
    col7.metric("Defect rate (202)", f"{defect_rate}%")
    st.write(f"overview total: {time.time() - t:.2f}s")

@st.fragment
def render_tab_market_share(df):
    t = time.time()
    st.header("Market Share Analysis")

    if df.empty:
        st.info("No data available.")
        return
    
    # Calculating Stats
    market_df, manufacturer_df = calc_market_share(df)
    
    # Grouped Bar Chart
    plot_bar(market_df, x="part_type", y="count", color="group", title="Parts Produced: 202 vs. Competition")
    
    # TOTAL PIE Chart
    plot_pie(manufacturer_df, names="manufacturer", values="count", title="Market Share by Brand", colors=manufacturer_colors)
    
    # Pie Chart
    #selected_part = st.selectbox("Select a part type for detail view", df["part_type"].unique())
    #part_df = df_copy[df_copy["part_type"] == selected_part]
    #pie_df = part_df.groupby("group").size().reset_index(name="count")
    
    #plot_pie(pie_df, names = "group", values = "count", title = f"Market Share for {selected_part}", colors = group_colors)
    st.write(f"market share total: {time.time() - t:.2f}s")
        
def render_tab_engine_penetration(df):
    t = time.time()
    st.header("Engine Penetration")
    
    if df.empty:
            st.info("No data available.")
            return
    
    # STATS
    from_202, total, pen_df, presence = calc_engine_penetration(df)
    
    # SLOGAN
    total_engines = pen_df["Total Engines"].sum()
    total_with_202 = pen_df["Engines with 202"].sum()
    every_x = round(total_engines / total_with_202, 2)
    st.info(f"In every {every_x}th engine there are parts from 202")
    
    # TOTAL PIE CHART
    share_df = pd.DataFrame({
        "group": ["202", "Competition"],
        "count": [from_202, total - from_202]
    })
    
    plot_pie(share_df, names = "group", values = "count", title = "Overall Part Share in All Engines")
    
    
    # HORIZONTAL BAR CHART
    plot_bar(pen_df, x = "Penetration %", y = "engine_type", orientation = "h", title = "Share of Engines Containing 202 Parts")
    
    # PRESENCE HEATMAP
    fig_heat = px.imshow(
        presence, title="Part Presence by Engine Type",
        labels=dict(x="Part Type", y="Engine Type", color="Present"),
        color_continuous_scale=["#FFFFFF", "#ADD8E6"]
    )
    st.plotly_chart(fig_heat, width="stretch")
    
    # TABLE
    st.dataframe(pen_df)
    st.write(f"engine penetration total: {time.time() - t:.2f}s")

@st.fragment
def render_tab_quality_analysis(df):
    t = time.time()
    st.title("Quality and Defect Analysis")
    st.caption("Shows the quality metrics of the products, for OEM1 vehicles only")
    if df.empty:
        st.info("No data available.")
        return
    
    # CALCULATING STATS
    oem1_df, defect_stats = calc_quality_stats(df)
    
    st.write("Debug Table",defect_stats)
    
    # GROUPED BARPLOT
    plot_bar(defect_stats, x = "part_type", y = "defect_rate_%", color = "group", title = "Defect Rate: 202 vs. Competition (OEM1 Only)")
    
    # LINE CHART (OVER TIME)
    selected_part = st.selectbox("Select part for trend view", oem1_df["part_type"].unique(), key="quality_part")
    trend_df = oem1_df[oem1_df["part_type"] == selected_part].copy()
    trend_df["month"] = trend_df["production_date"].dt.to_period("M").astype(str)

    trend_agg = trend_df.groupby(["month", "group"]).agg(
        total=("faulty", "count"),
        faulty=("faulty", "sum")
    ).reset_index()
    trend_agg["defect_rate_%"] = round(trend_agg["faulty"] / trend_agg["total"] * 100, 2)

    fig_line = px.line(
        trend_agg,
        x="month", y="defect_rate_%", color="group",
        title=f"Defect Rate Trend for {selected_part} (OEM1)",
        labels={"defect_rate_%": "Defect Rate (%)", "month": "Month", "group": "Manufacturer"},
        color_discrete_map={"202": "#ADD8E6", "Competition": "#CCCCCC"}
    )
    fig_line.update_xaxes(type="category")
    st.plotly_chart(fig_line, width="stretch")
    st.write(f"quality analysis total: {time.time() - t:.2f}s")

@st.fragment  
def render_tab_data_table(df):
    t = time.time()
    st.header("Final Dataset")

    # SELECTION FILTERS
    col1, col2, col3 = st.columns(3)
    with col1:
        select_parts = st.multiselect("Part type", df["part_type"].unique(), default=df["part_type"].unique())
    with col2:
        select_engines = st.multiselect("Engine type", df["engine_type"].unique(), default=df["engine_type"].unique())
    with col3:
        select_oem = st.multiselect("OEM", df["OEM_type"].unique(), default=df["OEM_type"].unique())

    table_df = df[
        (df["part_type"].isin(select_parts)) &
        (df["engine_type"].isin(select_engines)) &
        (df["OEM_type"].isin(select_oem))
    ]

    st.write(f"Showing {len(table_df):,} of {len(df):,} rows")
    st.dataframe(table_df, width="stretch")
    st.write(f"data table total: {time.time() - t:.2f}s")
    
def render_tab_debugging(df):
    t = time.time()
    st.title("Debugging")
    st.caption("Debugging information for developers.")
    st.write(df.dtypes.astype(str))
    st.write(df.head())           # Erste Zeilen ansehen
    st.write(df.shape)            # Anzahl Zeilen/Spalten
    st.write(f"debugging total: {time.time() - t:.2f}s")

if __name__ == "__main__":
    import time

    t = time.time()
    data = load_data()
    st.sidebar.write(f"load: {time.time() - t:.2f}s")

    with st.sidebar:
        st.image("www/logo.png")
        st.title("Production Data Dashboard")
        st.write("Marketing Analysis in our 202 company")
        t = time.time()
        data = filter_data_by_date(data)
        st.write(f"filter: {time.time() - t:.2f}s")


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
        render_tab_quality_analysis(data)
        
    # DATA TABLE
    with tab_data_table:
        render_tab_data_table(data)

    # DEBUGGING
    with tab_debugging:
        render_tab_debugging(data)