"""
SoSe26 Case Study 14 - Web Application
Company "202" | Market Share, Defect Rate & Engine Penetration Dashboard

This app reuses the EXACT data-loading and analysis logic already written in
Case_Study_14.ipynb
No synthetic / placeholder data is used. If a data file is missing, the affected
section shows a clear warning.

HOW TO RUN:
    streamlit run SoSe26_Case_Study_App_Group_14.py

EXPECTED FOLDER STRUCTURE:
    ./data/Einzelteil/Einzelteil_T01.txt ... T05.csv
    ./data/Komponente/Bestandteile_Komponente_K1BE1.csv (K1DI1, K1BE2, K1DI2)
    ./data/Fahrzeug/Bestandteile_Fahrzeuge_OEM1_Typ11.csv (Typ12)
    ./www/logo.png                         

STATUS / WHAT'S COVERED (see chat for full breakdown):
    - Part import (T01-T05), component + OEM1 import: from notebook 1.1-1.3
    - In_OEM1 flagging: from notebook 1.4
    - Market share + defect stats (Total AND OEM1-only): from notebook get_einzelteile_stats
    - Engine penetration ("every x-th engine ..."): from notebook 3.3 / 3.4
    - NEW in this app (not yet in the notebook): a production-date range filter
      for the Einzelteile pages, and Plotly visualizations for every section.
    - NOT yet possible: a single merged "final dataset" (Step 2 of the case study
      is not finished by the team yet), so this app still works off the same
      intermediate dataframes the notebook produces.
"""

import io
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------------------------------------
# 0. CONFIG
# --------------------------------------------------------------------------------
DATA = Path("data")
CACHE = Path("cache")
LOGO_PATH = Path("www") / "logo.png"

PRIMARY_COLOR = "#ADD8E6"   # light blue (required brand color)
ACCENT_COLOR = "#2C6E82"    # darker blue for chart/text contrast
FONT_NAME = "Source Sans Pro"

PART_NAMES = ["T01", "T02", "T03", "T04", "T05"]
ENGINE_NAMES = ["K1BE1", "K1DI1", "K1BE2", "K1DI2"]

FILES = {
    "t01": ("Einzelteil_T01.txt", b" | | ", b" "),
    "t02": ("Einzelteil_T02.txt", b"  ", b"\t"),
    "t03": ("Einzelteil_T03.txt", b"|", b"\x0b"),
    "t04": ("Einzelteil_T04.csv", b";", b"\n"),
    "t05": ("Einzelteil_T05.csv", b",", b"\n"),
}

ENGINE_FILE_PATHS = [
    DATA / "Komponente" / "Bestandteile_Komponente_K1BE1.csv",
    DATA / "Komponente" / "Bestandteile_Komponente_K1DI1.csv",
    DATA / "Komponente" / "Bestandteile_Komponente_K1BE2.csv",
    DATA / "Komponente" / "Bestandteile_Komponente_K1DI2.csv",
]
OEM1_FILE_PATHS = [
    DATA / "Fahrzeug" / "Bestandteile_Fahrzeuge_OEM1_Typ11.csv",
    DATA / "Fahrzeug" / "Bestandteile_Fahrzeuge_OEM1_Typ12.csv",
]

st.set_page_config(
    page_title="Company 202 | Market & Quality Dashboard",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)


# --------------------------------------------------------------------------------
# 1. STYLING (light blue theme + Source Sans Pro, explicit text color so it also
#    works correctly if the browser/Streamlit is set to dark mode)
# --------------------------------------------------------------------------------
def inject_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Source+Sans+Pro:wght@400;600;700&display=swap');

        html, body, [class*="css"] {{
            font-family: '{FONT_NAME}', sans-serif;
            color: #1A1A1A;
        }}
        .stApp {{ background-color: #F7FBFD; }}
        section[data-testid="stSidebar"] {{ background-color: {PRIMARY_COLOR}; }}
        div[data-testid="stMetric"] {{
            background-color: white;
            border: 1px solid {PRIMARY_COLOR};
            border-radius: 10px;
            padding: 12px;
        }}
        h1, h2, h3 {{ color: {ACCENT_COLOR}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------------
# 2. DATA LOADING  (ported 1:1 from Case_Study_14.ipynb, wrapped for safety)
# --------------------------------------------------------------------------------
def load_einzelteil(key: str) -> pd.DataFrame:
    """Exact port of the notebook's `load()` helper for one T0x part file."""
    filename, field_sep, row_sep = FILES[key]
    raw = (
        (DATA / "Einzelteil" / filename)
        .read_bytes()
        .replace(field_sep, b"\x01")
        .replace(row_sep, b"\n")
    )
    df = pd.read_csv(io.BytesIO(raw), sep="\x01", na_values=["NA"], dtype=str)

    for col in set(c.removesuffix(".x").removesuffix(".y") for c in df.columns):
        if col + ".x" in df.columns and col + ".y" in df.columns:
            df[col] = df[col + ".x"].combine_first(df[col + ".y"])

    part = key.upper()
    df["Part_ID"] = df.get(f"ID_{part}", df.get("Part_ID"))

    if "Produktionsdatum" not in df.columns and "Produktionsdatum_Origin_01011970" in df.columns:
        df["Produktionsdatum"] = pd.to_datetime("1970-01-01") + pd.to_timedelta(
            df["Produktionsdatum_Origin_01011970"].astype(float), unit="D"
        )

    df["Produktionsdatum"] = pd.to_datetime(df["Produktionsdatum"])
    df["Fehlerhaft_Datum"] = pd.to_datetime(df["Fehlerhaft_Datum"])
    df["Fehlerhaft_Fahrleistung"] = (
        df["Fehlerhaft_Fahrleistung"].str.replace(",", ".", regex=False).astype(float)
    )

    int_cols = ["Herstellernummer", "Werksnummer", "Fehlerhaft"]
    df[int_cols] = df[int_cols].astype("Int64")

    columns = [
        "Part_ID",
        "Herstellernummer",
        "Werksnummer",
        "Produktionsdatum",
        "Fehlerhaft",
        "Fehlerhaft_Datum",
        "Fehlerhaft_Fahrleistung",
    ]
    return df[columns].reset_index(drop=True)


@st.cache_resource
def load_all_einzelteile() -> tuple[dict, list]:
    # cache_resource (not cache_data): returns the SAME object every time instead
    # of a deep copy, which matters a lot for GB-scale dataframes. Since nothing
    # downstream mutates these frames in place (filtering creates new frames),
    # sharing the reference across reruns/pages is safe and much faster.
    cache_path = CACHE / "einzelteile.pkl"
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            return pickle.load(f), []

    st.warning(
        "No cache found under ./cache/einzelteile.pkl — loading raw files directly. "
        "This can take a long time for large files. Run `python prepare_cache.py` once "
        "to speed this up on future runs.",
        icon="⏳",
    )
    dfs, errors = {}, []
    for key in FILES:
        try:
            dfs[key] = load_einzelteil(key)
        except Exception as exc:  # missing file / malformed data
            errors.append(f"{key.upper()}: {exc}")
    return dfs, errors


@st.cache_resource
def load_engine_and_oem() -> tuple[list, "pd.DataFrame | None", list]:
    # cache_resource for the same reason as above.
    cache_path = CACHE / "engine_dfs.pkl"
    if cache_path.exists():
        with open(cache_path, "rb") as f:
            engine_dfs = pickle.load(f)
        return engine_dfs, "cached", []  # sentinel: flags already applied

    engine_dfs, errors = [], []
    for path in ENGINE_FILE_PATHS:
        try:
            df = pd.read_csv(path, sep=";").drop(columns=["Unnamed: 0"], errors="ignore")
            engine_dfs.append(df)
        except Exception as exc:
            errors.append(f"{path.name}: {exc}")

    oem_combined = None
    try:
        oem_parts = []
        for path in OEM1_FILE_PATHS:
            oem_parts.append(
                pd.read_csv(path, sep=";").drop(columns=["Unnamed: 0"], errors="ignore")
            )
        oem_combined = pd.concat(oem_parts, ignore_index=True)
    except Exception as exc:
        errors.append(f"OEM1 vehicle files: {exc}")

    return engine_dfs, oem_combined, errors


def add_oem1_flags(engine_dfs: list, oem_combined, einzelteile: dict) -> set:
    """Ported from notebook 1.4. Mutates engine_dfs / einzelteile in place, returns oem1_part_ids.

    Skipped entirely when data came from the cache (prepare_cache.py already
    applied these flags before pickling).
    """
    if oem_combined == "cached":
        return set()
    if oem_combined is None or not engine_dfs:
        return set()

    oem_motor_ids = oem_combined["ID_Motor"]
    for df in engine_dfs:
        id_col = df.columns[4]
        df["In_OEM1"] = df[id_col].isin(oem_motor_ids).astype(int)

    oem1_part_ids = set()
    for df in engine_dfs:
        oem1_components = df[df["In_OEM1"] == 1]
        part_cols = [c for c in df.columns if c.startswith("ID_T")]
        for col in part_cols:
            oem1_part_ids.update(oem1_components[col].dropna())

    for t_df in einzelteile.values():
        t_df["In_OEM1"] = t_df["Part_ID"].isin(oem1_part_ids).astype(int)

    return oem1_part_ids


# --------------------------------------------------------------------------------
# 3. ANALYSIS  (ported from notebook 1.3 "get_einzelteile_stats" and 3.3/3.4)
# --------------------------------------------------------------------------------
def get_einzelteile_stats(data_list: list, names: list, oem1_only: bool = False) -> pd.DataFrame:
    if oem1_only:
        data_list = [df[df["In_OEM1"] == 1] for df in data_list]

    stats = []
    for name, df in zip(names, data_list):
        total_ids = df["Part_ID"].nunique()
        df_202 = df[df["Herstellernummer"] == 202]
        df_comp = df[df["Herstellernummer"] != 202]

        ids_202 = df_202["Part_ID"].nunique()
        ids_comp = total_ids - ids_202

        faulty_202 = df_202[df_202["Fehlerhaft"] == 1]["Part_ID"].nunique()
        faulty_comp = df_comp[df_comp["Fehlerhaft"] == 1]["Part_ID"].nunique()

        share_202 = round((ids_202 / total_ids * 100), 2) if total_ids else 0.0
        fail_rate_202 = round((faulty_202 / ids_202 * 100), 2) if ids_202 else 0.0
        fail_rate_comp = round((faulty_comp / ids_comp * 100), 2) if ids_comp else 0.0

        stats.append(
            {
                "Part_Type": name,
                "total_unique_part_id": total_ids,
                "unique_part_id_202": ids_202,
                "unique_part_id_competition": ids_comp,
                "relative_part_id_202_%": share_202,
                "faulty_unique_part_id_202": faulty_202,
                "faulty_unique_part_id_competition": faulty_comp,
                "relative_faulty_unique_part_id_202_%": fail_rate_202,
                "relative_faulty_unique_part_id_competition_%": fail_rate_comp,
            }
        )
    return pd.DataFrame(stats)


def filter_mask(df: pd.DataFrame) -> pd.Series:
    mask = pd.Series(False, index=df.index)
    for col in df.columns[0:4]:
        mask = mask | df[col].astype(str).str.contains(r"-202-", na=False)
    return mask


def compute_engine_penetration(engine_dfs: list) -> tuple[list, list, float, float]:
    filtered_engine_dfs = [df[filter_mask(df)] for df in engine_dfs]
    percentages = [
        round(len(filtered_engine_dfs[i]) / len(engine_dfs[i]) * 100, 2) if len(engine_dfs[i]) else np.nan
        for i in range(len(engine_dfs))
    ]
    total_with_202 = sum(len(df) for df in filtered_engine_dfs)
    total_all = sum(len(df) for df in engine_dfs)
    overall_pct = round(total_with_202 / total_all * 100, 2) if total_all else 0.0
    overall_ratio = round(100 / overall_pct, 2) if overall_pct else float("inf")
    return filtered_engine_dfs, percentages, overall_pct, overall_ratio


# --------------------------------------------------------------------------------
# 4. SIDEBAR
# --------------------------------------------------------------------------------
def render_sidebar(einzelteile: dict) -> dict:
    if LOGO_PATH.exists():
        st.sidebar.image(str(LOGO_PATH), width='stretch')
    st.sidebar.title("Filters")

    date_range = None
    if einzelteile:
        all_dates = pd.concat([df["Produktionsdatum"] for df in einzelteile.values()])
        min_date, max_date = all_dates.min(), all_dates.max()
        date_range = st.sidebar.date_input(
            "Production date range (Einzelteile)",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
    else:
        st.sidebar.info("Part data not loaded yet — date filter unavailable.")

    oem1_only = st.sidebar.checkbox("Restrict Market Share / Defect view to OEM1", value=False)
    return {"date_range": date_range, "oem1_only": oem1_only}


def apply_date_filter(einzelteile: dict, date_range) -> dict:
    if not date_range or len(date_range) != 2:
        return einzelteile
    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    return {
        key: df[(df["Produktionsdatum"] >= start) & (df["Produktionsdatum"] <= end)]
        for key, df in einzelteile.items()
    }


@st.cache_data(show_spinner="Computing market share & defect stats...")
def compute_all_stats(start_str: str, end_str: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Cached on the (start, end) date strings only — switching pages without
    changing the date filter hits this cache instantly instead of recomputing
    nunique()/groupby over potentially millions of rows every rerun."""
    einzelteile, _ = load_all_einzelteile()
    filtered = apply_date_filter(einzelteile, (start_str, end_str))
    ordered = [filtered[k] for k in FILES if k in filtered]
    names = PART_NAMES[: len(ordered)]
    stats_total = get_einzelteile_stats(ordered, names, oem1_only=False) if ordered else pd.DataFrame()
    stats_oem1 = get_einzelteile_stats(ordered, names, oem1_only=True) if ordered else pd.DataFrame()
    return stats_total, stats_oem1


@st.cache_data(show_spinner="Computing engine penetration...")
def compute_penetration_cached() -> tuple[list, float, float]:
    """No date filter applies here (component tables have no production date),
    so this only ever needs to run once per app session."""
    engine_dfs, _, _ = load_engine_and_oem()
    if not engine_dfs:
        return [], None, None
    _, percentages, overall_pct, overall_ratio = compute_engine_penetration(engine_dfs)
    return percentages, overall_pct, overall_ratio


# --------------------------------------------------------------------------------
# 5. PAGES
# --------------------------------------------------------------------------------
def page_overview(stats_df: pd.DataFrame, overall_pct, overall_ratio, errors: list) -> None:
    st.title("📊 Company 202 — Overview")
    st.caption("Key figures for marketing: market share, quality, and engine penetration.")

    for err in errors:
        st.warning(f"Missing/unreadable data source: {err}")

    if stats_df.empty:
        st.info("No part data available yet — nothing to summarize.")
        return

    total_parts = stats_df["total_unique_part_id"].sum()
    parts_202 = stats_df["unique_part_id_202"].sum()
    overall_share = round(parts_202 / total_parts * 100, 2) if total_parts else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Overall market share (202)", f"{overall_share}%")
    col2.metric("Engines with 202 parts", f"{overall_pct}%" if overall_pct is not None else "n/a")
    col3.metric(
        "Advertising slogan",
        f"1 in {overall_ratio}" if overall_ratio not in (None, float("inf")) else "n/a",
    )

    st.markdown("---")
    fig = px.bar(
        stats_df,
        x="Part_Type",
        y="relative_part_id_202_%",
        color_discrete_sequence=[ACCENT_COLOR],
        title="Market share of 202 parts by part type",
        labels={"relative_part_id_202_%": "Market share (%)"},
    )
    st.plotly_chart(fig, width='stretch')


def page_market_share(stats_df: pd.DataFrame) -> None:
    st.title("🧩 Market Share Analysis")
    st.write("202 vs. competition, per part type (task 1).")
    if stats_df.empty:
        st.info("No data available.")
        return

    melted = stats_df.melt(
        id_vars="Part_Type",
        value_vars=["unique_part_id_202", "unique_part_id_competition"],
        var_name="Manufacturer",
        value_name="count",
    )
    melted["Manufacturer"] = melted["Manufacturer"].map(
        {"unique_part_id_202": "202", "unique_part_id_competition": "Competition"}
    )
    fig = px.bar(
        melted,
        x="Part_Type",
        y="count",
        color="Manufacturer",
        barmode="group",
        title="Unique parts produced: 202 vs. Competition",
        color_discrete_map={"202": ACCENT_COLOR, "Competition": "#CCCCCC"},
    )
    st.plotly_chart(fig, width='stretch')
    st.dataframe(stats_df, width='stretch')


def page_quality(stats_df_oem1: pd.DataFrame) -> None:
    st.title("🛠️ Quality / Defect Analysis (OEM1)")
    st.write("Relative defect frequency of 202 vs. competition, restricted to OEM1 vehicles (task 2).")
    if stats_df_oem1.empty:
        st.info("No OEM1-flagged data available (check that OEM1 files loaded correctly).")
        return

    melted = stats_df_oem1.melt(
        id_vars="Part_Type",
        value_vars=[
            "relative_faulty_unique_part_id_202_%",
            "relative_faulty_unique_part_id_competition_%",
        ],
        var_name="Manufacturer",
        value_name="Defect_rate_%",
    )
    melted["Manufacturer"] = melted["Manufacturer"].map(
        {
            "relative_faulty_unique_part_id_202_%": "202",
            "relative_faulty_unique_part_id_competition_%": "Competition",
        }
    )
    fig = px.bar(
        melted,
        x="Part_Type",
        y="Defect_rate_%",
        color="Manufacturer",
        barmode="group",
        title="Defect rate by part type (OEM1 vehicles only)",
        color_discrete_map={"202": ACCENT_COLOR, "Competition": "#CCCCCC"},
    )
    st.plotly_chart(fig, width='stretch')
    st.dataframe(stats_df_oem1, width='stretch')


def page_engine_penetration(percentages: list, overall_pct, overall_ratio, errors: list) -> None:
    st.title("⚙️ Engine Penetration")
    st.write('Advertising claim: "In every x-th engine there are parts from 202." (task 3)')

    for err in errors:
        st.warning(f"Missing/unreadable data source: {err}")

    if not percentages:
        st.info("No engine/component data available yet.")
        return

    penetration_df = pd.DataFrame({"Engine_Type": ENGINE_NAMES[: len(percentages)], "Share_%": percentages})
    penetration_df["Every_xth_engine"] = penetration_df["Share_%"].apply(
        lambda p: round(100 / p, 2) if p else float("inf")
    )

    fig = px.bar(
        penetration_df,
        x="Engine_Type",
        y="Share_%",
        color_discrete_sequence=[ACCENT_COLOR],
        title="Share of engines containing 202 parts, by engine type",
        labels={"Share_%": "Engines with 202 parts (%)"},
    )
    st.plotly_chart(fig, width='stretch')
    st.dataframe(penetration_df, width='stretch')

    st.markdown("---")
    st.subheader("Overall (all engine types combined)")
    col1, col2 = st.columns(2)
    col1.metric("Engines containing 202 parts", f"{overall_pct}%")
    col2.metric("Slogan", f"1 in {overall_ratio} engines" if overall_ratio != float("inf") else "n/a")


def page_data_table(einzelteile: dict, engine_dfs: list) -> None:
    st.title("📋 Data Tables")
    st.write("Raw (filtered) tables currently used by the app. A single merged final dataset is not yet available.")

    if einzelteile:
        st.subheader("Einzelteile (parts)")
        selected = st.selectbox("Choose a part table", list(einzelteile.keys()))
        st.dataframe(einzelteile[selected], width='stretch')
        st.download_button(
            f"Download {selected.upper()} as CSV",
            data=einzelteile[selected].to_csv(index=False).encode("utf-8"),
            file_name=f"{selected}_filtered.csv",
            mime="text/csv",
        )
    else:
        st.info("Part data not loaded.")

    if engine_dfs:
        st.subheader("Engine / component tables")
        idx = st.selectbox(
            "Choose an engine table", range(len(engine_dfs)), format_func=lambda i: ENGINE_NAMES[i]
        )
        st.dataframe(engine_dfs[idx], width='stretch')
    else:
        st.info("Engine/component data not loaded.")


# --------------------------------------------------------------------------------
# 6. MAIN
# --------------------------------------------------------------------------------
def main() -> None:
    inject_custom_css()

    einzelteile, part_errors = load_all_einzelteile()
    engine_dfs, oem_combined, engine_errors = load_engine_and_oem()
    add_oem1_flags(engine_dfs, oem_combined, einzelteile)

    filters = render_sidebar(einzelteile)
    date_range = filters["date_range"]
    start_str = str(date_range[0]) if date_range else ""
    end_str = str(date_range[1]) if date_range and len(date_range) == 2 else ""

    stats_total, stats_oem1 = compute_all_stats(start_str, end_str)
    active_stats = stats_oem1 if filters["oem1_only"] else stats_total

    percentages, overall_pct, overall_ratio = compute_penetration_cached()

    einzelteile_filtered = apply_date_filter(einzelteile, date_range)

    page = st.sidebar.radio(
        "Navigate",
        ["Overview", "Market Share", "Quality (OEM1)", "Engine Penetration", "Data Table"],
    )

    if page == "Overview":
        page_overview(active_stats, overall_pct, overall_ratio, part_errors + engine_errors)
    elif page == "Market Share":
        page_market_share(active_stats)
    elif page == "Quality (OEM1)":
        page_quality(stats_oem1)
    elif page == "Engine Penetration":
        page_engine_penetration(percentages, overall_pct, overall_ratio, engine_errors)
    elif page == "Data Table":
        page_data_table(einzelteile_filtered, engine_dfs)


if __name__ == "__main__":
    main()