import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

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

# Loading the final data
@st.cache_data
def load_data():
    df = pd.read_csv("final_data_sample.csv", parse_dates=["production_date"])
    return df

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
    st.title("KPI Overview")
    st.caption("Key figures for marketing: market share, quality, and engine penetration.")
    
    
    
    
    
    st.dataframe(data.head())

# MARKET SHARE
with tab_market_share:
    st.title("Market Share")
    st.caption("Shows the market share of different brands.")
    market_share_fig = px.pie(data_frame=data, names='manufacturer', title='Market Share by Brand')
    st.plotly_chart(market_share_fig)
    
# ENGINE PENETRATION
with tab_engine_penetration:
    st.title("Engine Penetration")
    st.caption("Shows the penetration of different engine types.")
    #engine_penetration_fig = px.histogram(data_frame=data, x='engine_type', title='Engine Penetration')
    #st.plotly_chart(engine_penetration_fig)

# QUALITY ANALYSIS
with tab_quality_analysis:
    st.title("Quality Analysis")
    st.caption("Shows the quality metrics of the products.")
    
# DATA TABLE
with tab_data_table:
    st.title("Data Table")
    st.caption("Shows the filtered data used for analysis.")
    st.dataframe(data.head())

# DEBUGGING
with tab_debugging:
    st.title("Debugging")
    st.caption("Debugging information for developers.")
    st.write(data.dtypes)           # Datentypen pruefen
    st.write(data.head())           # Erste Zeilen ansehen
    #st.write(type(data["production_date"]))    # Typ einer Variable pruefen
    st.write(data.shape)            # Anzahl Zeilen/Spalten






