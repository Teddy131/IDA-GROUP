import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import numpy as np

# Source Sans Pro is now published as Source Sans and ships with Streamlit
FONT_STACK = "Source Sans Pro, Source Sans, sans-serif"

# Use the same font in the charts as in the rest of the app
pio.templates["ida"] = go.layout.Template(layout=dict(font=dict(family=FONT_STACK)))
pio.templates.default = "plotly+ida"

# Page Config
st.set_page_config(page_title="202 Marketing Dashboard", layout="wide")

# Apply the font to the whole page
st.markdown(
    f"<style>html, body, [class*='css'] {{ font-family: {FONT_STACK}; }}</style>",
    unsafe_allow_html=True,
)

# Colors
color_202 = "#ADD8E6"
group_colors = {"202": color_202, "Competition": "#CCCCCC"}
manufacturer_colors = {202: color_202, 201: "#B0C4DE", 203: "#D3D3D3", 204: "#C0C0C0"}

# Axis Labels
labels = {
    "count": "Number of Parts",
    "part_type": "Part Type",
    "group": "Manufacturer",
    "defect_rate_%": "Defect Rate (%)",
    "engine_type": "Engine Type"
}

# Plotting Functions
def plot_bar(df, x, y, title, color=None, colors=group_colors, orientation="v"):
    fig = px.bar(
        df, x=x, y=y, color=color, orientation=orientation, barmode="group",
        title=title, labels=labels, color_discrete_map=colors,
        color_discrete_sequence=[color_202],
    )
    st.plotly_chart(fig, width="stretch")
    return fig


def plot_pie(df, names, title, values=None, colors=group_colors):
    fig = px.pie(
        df, names=names, values=values, color=names, title=title,
        color_discrete_map=colors,
    )
    st.plotly_chart(fig, width="stretch")
    return fig
    
# LOADING DATA AND CACHING
@st.cache_data
def load_data():
    try:
        # Parquet is loading 10x-15x faster during the intial import
        df = pd.read_parquet("SoSe26_Case_Study_finalData_Group_14.parquet")
        
    except Exception:
        # Fallback if parquet isnt installed
        df = pd.read_csv("SoSe26_Case_Study_finalData_Group_14.csv",
                         parse_dates=["production_date"])
        # Bug with pands 3, fixing datatypes for streamlit
        string_cols = df.select_dtypes(include=["string", "object"]).columns
        for col in string_cols:
            df[col] = df[col].astype(object)
    return df

# DATE FILTER
def filter_data_by_date(df):
    """Filter the data based on the selected date range."""
    min_date = df['production_date'].min().date()
    max_date = df['production_date'].max().date()

    date_selection = st.date_input(
        "Select the production date range",
        value=(min_date, max_date),
        # min max cap
        min_value=min_date,
        max_value=max_date,
    )

    # To avoid continuing the calculation without having 2 dates selected
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
    return (
        market_share, penetration_percentage, every_xth,
        parts_202, part_types_202,
        oem1_parts_202, oem1_total, defect_rate
    )

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
    st.header("KPI Overview")

    if df.empty:
        st.info("No data available.")
        return
    
    (market_share, penetration_percentage, every_xth,
     parts_202, part_types_202,
     oem1_parts_202, oem1_total, defect_rate) = calc_overview_metrics(df)
    
    # RENDERING METRICS
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Market share (202)", f"{market_share}%")
    col2.metric("Engine penetration", f"{penetration_percentage}%")
    col3.metric("Defect rate (202)", f"{defect_rate}%")
    
    col4, col5, col6 = st.columns(3)
    col4.metric("Total parts (202)", f"{parts_202:,}")
    col5.metric("Part types (202)", f"{part_types_202}")
    col6.metric("OEM1 volume (202)", f"{oem1_parts_202:,} / {oem1_total:,}")
    
    col7 = st.columns(1)[0]
    col7.metric("Slogan", f"Every {every_xth}th engine")

    # ------------------------------------------------------------------
    # Interpretion of Overview metrics
    # ------------------------------------------------------------------
    competition_df = df[df["manufacturer"] != 202]
    faulty_competition = competition_df[competition_df["faulty"] == 1]
    defect_rate_competition = round(
        len(faulty_competition) / len(competition_df) * 100, 2
    ) if len(competition_df) > 0 else 0

    st.markdown("---")
    st.subheader("What this means")

    st.write(
        f"202 supplies **{market_share}%** of all parts in the selected period, "
        f"appearing in about **1 in every {every_xth} engines** produced."
    )

    diff = round(defect_rate - defect_rate_competition, 2)
    if diff < 0:
        st.write(
            f"Our defect rate (**{defect_rate}%**) is **{abs(diff)} percentage points lower** "
            f"than the competition's (**{defect_rate_competition}%**). 202 parts are relatively more reliable."
        )
    elif diff > 0:
        st.write(
            f"Our defect rate (**{defect_rate}%**) is **{diff} percentage points higher** "
            f"than the competition's (**{defect_rate_competition}%**). A quality gap worth investigating."
        )
    else:
        st.write(
            f"Our defect rate (**{defect_rate}%**) is essentially **on par** with the "
            f"competition's (**{defect_rate_competition}%**)."
        )

@st.fragment
def render_tab_market_share(df):
    st.header("Market Share Analysis")

    if df.empty:
        st.info("No data available.")
        return

    # Calculating Stats
    market_df, manufacturer_df = calc_market_share(df)

    # Grouped Bar Chart
    plot_bar(market_df, x="part_type", y="count", color="group", title="Parts Produced: 202 vs. Competition")

    # INTERPRETATION; Parts Produced bar chart
    pivot = market_df.pivot(index="part_type", columns="group", values="count").fillna(0)
    pivot["share_202_%"] = round(pivot.get("202", 0) / pivot.sum(axis=1) * 100, 2)
    share_by_type = pivot["share_202_%"].reset_index()
    best = share_by_type.loc[share_by_type["share_202_%"].idxmax()]
    worst = share_by_type.loc[share_by_type["share_202_%"].idxmin()]

    st.write(
        f"**Interpretation:** 202 has its strongest position in **{best['part_type']}** "
        f"({best['share_202_%']}% share), and its weakest in **{worst['part_type']}** "
        f"({worst['share_202_%']}% share)."
    )

    # TOTAL PIE Chart
    plot_pie(manufacturer_df, names="manufacturer", values="count",
             title="Market Share by Brand", colors=manufacturer_colors)

    # INTERPRETATION; Market Share by Brand
    brand_share = manufacturer_df.copy()
    brand_share["share_%"] = round(brand_share["count"] / brand_share["count"].sum() * 100, 2)
    brand_share = brand_share.sort_values("share_%", ascending=False).reset_index(drop=True)

    our_share = brand_share.loc[brand_share["manufacturer"] == 202, "share_%"].values[0]
    our_rank = brand_share.index[brand_share["manufacturer"] == 202][0] + 1
    n_manufacturers = len(brand_share)
    competitors = brand_share[brand_share["manufacturer"] != 202]
    largest_competitor = competitors.iloc[0] if not competitors.empty else None

    st.markdown("---")
    if our_rank == 1 and largest_competitor is not None:
        st.write(
            f"**Interpretation:** 202 is the **market leader** with **{our_share}%** of all parts, "
            f"ahead of its closest competitor (manufacturer {int(largest_competitor['manufacturer'])}, "
            f"{largest_competitor['share_%']}%)."
        )
    elif largest_competitor is not None:
        st.write(
            f"**Interpretation:** 202 holds **{our_share}%** of the market, ranking "
            f"**#{our_rank} out of {n_manufacturers}** manufacturers. The market leader is "
            f"manufacturer {int(largest_competitor['manufacturer'])} with {largest_competitor['share_%']}%."
        )

    # DETAIL PIE; per part type (rebuilt from market_df, no df_copy needed)
    selected_part = st.selectbox("Select a part type for detail view", df["part_type"].unique())
    pie_df = market_df[market_df["part_type"] == selected_part][["group", "count"]]

    plot_pie(pie_df, names="group", values="count", title=f"Market Share for {selected_part}", colors=group_colors)

    # INTERPRETATION; Market Share for {selected_part}
    part_total = pie_df["count"].sum()
    part_202 = pie_df.loc[pie_df["group"] == "202", "count"].values
    part_share_202 = round(part_202[0] / part_total * 100, 2) if part_total and len(part_202) else 0.0

    diff = round(part_share_202 - our_share, 2)
    st.markdown("---")
    if diff > 0:
        st.write(
            f"**Interpretation:** For **{selected_part}**, 202 holds **{part_share_202}%** of the market; "
            f"**{diff} points above** its overall average share ({our_share}%). "
            f"This is a relative strength for 202."
        )
    elif diff < 0:
        st.write(
            f"**Interpretation:** For **{selected_part}**, 202 holds **{part_share_202}%** of the market; "
            f"**{abs(diff)} points below** its overall average share ({our_share}%). "
            f"This part type is a relative weak spot for 202."
        )
    else:
        st.write(
            f"**Interpretation:** For **{selected_part}**, 202's share ({part_share_202}%) "
            f"exactly matches its overall average ({our_share}%)."
        )


def render_tab_engine_penetration(df):
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
    
    plot_pie(share_df, names="group", values="count", title="Overall Part Share in All Engines")

    # INTERPRETATION; Overall Part Share
    overall_share_pct = round(from_202 / total * 100, 2) if total else 0.0
    st.write(
        f"**Interpretation:** Across all tracked engines, 202 parts make up **{overall_share_pct}%** "
        f"of everything installed; consistent with the overall 1-in-{every_x} engine penetration figure above."
    )

    # HORIZONTAL BAR CHART
    plot_bar(pen_df, x="Penetration %", y="engine_type", orientation="h", title="Share of Engines Containing 202 Parts")

    # INTERPRETATION; Penetration by engine type
    best_engine = pen_df.loc[pen_df["Penetration %"].idxmax()]
    worst_engine = pen_df.loc[pen_df["Penetration %"].idxmin()]
    spread = round(float(best_engine["Penetration %"]) - float(worst_engine["Penetration %"]), 2) # type: ignore

    st.write(
        f"**Interpretation:** 202 parts are most common in **{best_engine['engine_type']}** engines "
        f"(**{best_engine['Penetration %']}%** penetration, roughly 1 in {best_engine['Every x-th']}), "
        f"and least common in **{worst_engine['engine_type']}** "
        f"(**{worst_engine['Penetration %']}%**, roughly 1 in {worst_engine['Every x-th']})."
    )
    if spread > 20:
        st.write(
            f"This is a **{spread}-point gap** between engine types; worth investigating why "
            f"202's presence varies so much across engine platforms."
        )
    
    # PRESENCE HEATMAP
    fig_heat = px.imshow(
        presence, title="Part Presence by Engine Type",
        labels=dict(x="Part Type", y="Engine Type", color="Present"),
        color_continuous_scale=["#FFFFFF", "#ADD8E6"]
    )
    st.plotly_chart(fig_heat, width="stretch")

    # INTERPRETATION; Presence heatmap
    part_coverage = presence.sum(axis=0)  # how many engine types each part type appears in
    n_engine_types = presence.shape[0]
    universal_parts = part_coverage[part_coverage == n_engine_types].index.tolist()
    exclusive_parts = part_coverage[part_coverage == 1].index.tolist()

    st.markdown("---")
    if universal_parts:
        st.write(
            f"**Interpretation:** part type(s) **{', '.join(universal_parts)}** are installed across "
            f"**all {n_engine_types} tracked engine types**; a shared/standard component."
        )
    if exclusive_parts:
        st.write(
            f"Part type(s) **{', '.join(exclusive_parts)}** appear in **only one** engine type; "
            f"these are platform-specific components rather than standard parts."
        )
    if not universal_parts and not exclusive_parts:
        st.write(
            "**Interpretation:** part usage is mixed across engine types, with no single part "
            "used everywhere or restricted to just one platform."
        )
    
    # TABLE
    st.dataframe(pen_df)

@st.fragment
def render_tab_quality_analysis(df):
    st.title("Quality and Defect Analysis")
    st.caption("Shows the quality metrics of the products, for OEM1 vehicles only")
    if df.empty:
        st.info("No data available.")
        return
    
    # CALCULATING STATS
    oem1_df, defect_stats = calc_quality_stats(df)
    
    # GROUPED BARPLOT
    plot_bar(defect_stats, x="part_type", y="defect_rate_%", color="group",
             title="Defect Rate: 202 vs. Competition (OEM1 Only)")

    # INTERPRETATION; per part type
    st.write("**Interpretation, per part type (OEM1 vehicles):**")
    better_count, worse_count = 0, 0
    for pt in defect_stats["part_type"].unique():
        row_202 = defect_stats[(defect_stats["part_type"] == pt) & (defect_stats["group"] == "202")]
        row_comp = defect_stats[(defect_stats["part_type"] == pt) & (defect_stats["group"] == "Competition")]
        if row_202.empty or row_comp.empty:
            continue
        r202 = row_202["defect_rate_%"].values[0]
        rcomp = row_comp["defect_rate_%"].values[0]
        diff = round(r202 - rcomp, 2)
        if diff < 0:
            verdict = f"**{abs(diff)} points lower than**"
            better_count += 1
        elif diff > 0:
            verdict = f"**{diff} points higher than**"
            worse_count += 1
        else:
            verdict = "**equal to**"
        st.write(f"- **{pt}**: our rate ({r202}%) is {verdict} the competition's ({rcomp}%).")

    st.markdown("---")
    if better_count > worse_count:
        st.write(
            f"**Overall:** 202 has a **lower defect rate** than the competition in "
            f"{better_count} out of {better_count + worse_count} part types; a generally favorable quality position."
        )
    elif worse_count > better_count:
        st.write(
            f"**Overall:** 202 has a **higher defect rate** than the competition in "
            f"{worse_count} out of {better_count + worse_count} part types; this is a quality concern worth addressing."
        )
    else:
        st.write("**Overall:** 202's quality position is mixed, roughly balanced between better and worse part types.")
    
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

    # INTERPRETATION; trend
    trend_pivot = trend_agg.pivot(index="month", columns="group", values="defect_rate_%").sort_index()
    st.markdown("---")
    if "202" in trend_pivot.columns and "Competition" in trend_pivot.columns and len(trend_pivot) >= 2:
        first_gap = round(trend_pivot["202"].iloc[0] - trend_pivot["Competition"].iloc[0], 2)
        last_gap = round(trend_pivot["202"].iloc[-1] - trend_pivot["Competition"].iloc[-1], 2)
        latest_month = trend_pivot.index[-1]
        latest_202 = trend_pivot["202"].iloc[-1]
        latest_comp = trend_pivot["Competition"].iloc[-1]

        st.write(
            f"**Interpretation:** in the most recent month with data ({latest_month}), "
            f"202's defect rate for **{selected_part}** was **{latest_202}%** vs. "
            f"**{latest_comp}%** for the competition."
        )

        if abs(last_gap) < abs(first_gap):
            st.write(
                f"The gap between 202 and the competition has **narrowed** over time "
                f"(from {first_gap} to {last_gap} percentage points)."
            )
        elif abs(last_gap) > abs(first_gap):
            st.write(
                f"The gap between 202 and the competition has **widened** over time "
                f"(from {first_gap} to {last_gap} percentage points)."
            )
        else:
            st.write("The gap between 202 and the competition has stayed roughly stable over time.")
    else:
        st.write("Not enough data across months to comment on the trend for this part type.")


@st.fragment
def render_tab_data_table(df):
    st.header("Final Dataset")

    if df.empty:
        st.info("No data available.")
        return

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

    st.write(f"{len(table_df):,} of {len(df):,} rows match the current filters")

    if table_df.empty:
        st.info("No rows match the current filters.")
        return

    # Limiting rows, adding pagination to avoid performance issues
    MAX_ROWS = 100
    total_pages = (len(table_df) - 1) // MAX_ROWS + 1

    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1)

    start = (page - 1) * MAX_ROWS
    st.caption(f"Page {page:,} of {total_pages:,}")
    st.dataframe(table_df.iloc[start:start + MAX_ROWS], width="stretch")
    
if __name__ == "__main__":

    data = load_data()

    with st.sidebar:
        st.image("www/logo.png")
        st.title("Production Data Dashboard")
        st.write("Marketing Analysis in our 202 company")
        
        data = filter_data_by_date(data)
        
        st.write("Case Study Group 14 - SoSe 2026")
        
        st.write("**Authors:**")
        st.write("- Ibrahim Gezer | 413044")
        st.write("- Cagatay Kulakac | 412636")
        st.write("- Fehmi Cem Yilmaz | 476211")
        st.write("- Erol Saka | 484257")
        st.write("- Leila Elkamel | 492215")

    # Create tabs for different sections of the dashboard
    tab_overview, tab_market_share, tab_engine_penetration, tab_quality_analysis, tab_data_table = st.tabs([
        "Overview", "Market share", "Engine penetration", "Quality analysis", "Data table"])


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
