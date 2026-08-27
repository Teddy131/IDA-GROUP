"""
SoSe26 Case Study 14 - Web App (vereinfachte Fassung)
Firma "202" | Marktanteil, Fehlerquote & Motor-Durchdringung

Starten:
    streamlit run app_simple.py

Ordnerstruktur:
    ./data/Einzelteil/Einzelteil_T01.txt ... T05.csv
    ./data/Komponente/Bestandteile_Komponente_K1BE1.csv (K1DI1, K1BE2, K1DI2)
    ./data/Fahrzeug/Bestandteile_Fahrzeuge_OEM1_Typ11.csv (Typ12)
    ./www/logo.png
"""

import io
import os

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------------
# Einstellungen
# ------------------------------------------------------------------
blue = "#2C6E82"          # dunkles blau für die Balken von Firma 202
grey = "#CCCCCC"          # grau für die Konkurrenz

teile = ["T01", "T02", "T03", "T04", "T05"]
motoren = ["K1BE1", "K1DI1", "K1BE2", "K1DI2"]

# Die Rohdateien haben kaputte Trennzeichen. Pro Datei:
# (Dateiname, Trennzeichen zwischen Spalten, Trennzeichen zwischen Zeilen)
files = {
    "T01": ("Einzelteil_T01.txt", b" | | ", b" "),
    "T02": ("Einzelteil_T02.txt", b"  ", b"\t"),
    "T03": ("Einzelteil_T03.txt", b"|", b"\x0b"),
    "T04": ("Einzelteil_T04.csv", b";", b"\n"),
    "T05": ("Einzelteil_T05.csv", b",", b"\n"),
}

# Manche Dateien haben Spalten doppelt, als "...x" und "...y".
double_cols = [
    "Produktionsdatum",
    "Herstellernummer",
    "Werksnummer",
    "Fehlerhaft",
    "Fehlerhaft_Datum",
    "Fehlerhaft_Fahrleistung",
]

st.set_page_config(page_title="Firma 202 | Dashboard", page_icon=":wrench:", layout="wide")


# ------------------------------------------------------------------
# Daten einlesen
# ------------------------------------------------------------------
def load_einzelteil(teil):
    """Liest eine Einzelteil-Datei ein und gibt ein sauberes DataFrame zurück."""
    file_name, splitter, split_rows = files[teil]

    # Die kaputten Trennzeichen durch normale ersetzen, dann einlesen.
    raw_data = open(f"data/Einzelteil/{file_name}", "rb").read()
    raw_data = raw_data.replace(splitter, b"\x01").replace(split_rows, b"\n")
    df = pd.read_csv(io.BytesIO(raw_data), sep="\x01", na_values=["NA"], dtype=str)

    # Doppelte Spalten zusammenführen: nimm den Wert aus ".x",
    # und wenn der leer ist, den aus ".y".
    for col in ["ID_" + teil] + double_cols:
        if col + ".x" in df.columns:
            df[col] = df[col + ".x"].fillna(df[col + ".y"])

    df["Part_ID"] = df["ID_" + teil]

    # T03 und T04 haben kein Datum, sondern die Anzahl Tage seit dem 01.01.1970.
    if "Produktionsdatum" not in df.columns:
        days = df["Produktionsdatum_Origin_01011970"].astype(float)
        df["Produktionsdatum"] = pd.to_datetime("1970-01-01") + pd.to_timedelta(days, unit="D")

    # Spalten in die richtigen Datentypen umwandeln
    df["Produktionsdatum"] = pd.to_datetime(df["Produktionsdatum"])
    df["Fehlerhaft_Datum"] = pd.to_datetime(df["Fehlerhaft_Datum"])
    df["Fehlerhaft_Fahrleistung"] = df["Fehlerhaft_Fahrleistung"].str.replace(",", ".").astype(float)
    df["Herstellernummer"] = df["Herstellernummer"].astype("Int64")
    df["Werksnummer"] = df["Werksnummer"].astype("Int64")
    df["Fehlerhaft"] = df["Fehlerhaft"].astype("Int64")

    cols = ["Part_ID", "Herstellernummer", "Werksnummer", "Produktionsdatum", "Fehlerhaft",
            "Fehlerhaft_Datum", "Fehlerhaft_Fahrleistung"]
    return df[cols]


@st.cache_data(show_spinner="Daten werden geladen, das dauert beim ersten Mal ein paar Minuten ...")
def load_data():
    """lädt alle Dateien und markiert, welche Teile in OEM1-Fahrzeugen stecken.

    @st.cache_data sorgt dafür, dass das nur einmal passiert und nicht bei
    jedem Klick in der App neu.
    """
    # 1) Einzelteile
    einzelteile = {}
    for teil in teile:
        einzelteile[teil] = load_einzelteil(teil)

    # 2) Komponenten (Motoren)
    komponenten = []
    for motor in motoren:
        df = pd.read_csv(f"data/Komponente/Bestandteile_Komponente_{motor}.csv", sep=";")
        df = df.drop(columns="Unnamed: 0")
        komponenten.append(df)

    # 3) Fahrzeuge von OEM1 (beide Typen untereinander hängen)
    typ11 = pd.read_csv("data/Fahrzeug/Bestandteile_Fahrzeuge_OEM1_Typ11.csv", sep=";")
    typ12 = pd.read_csv("data/Fahrzeug/Bestandteile_Fahrzeuge_OEM1_Typ12.csv", sep=";")
    oem1 = pd.concat([typ11, typ12])

    # 4) Markieren: steckt dieser Motor in einem OEM1-Fahrzeug?
    #    Die Motor-ID ist immer die letzte Spalte der Komponenten-Tabelle.
    for df in komponenten:
        motor_col = df.columns[-1]
        df["In_OEM1"] = df[motor_col].isin(oem1["ID_Motor"]).astype(int)

    # 5) Alle Einzelteil-IDs sammeln, die in einem OEM1-Motor verbaut sind
    oem1_teil_ids = set()
    for df in komponenten:
        nur_oem1 = df[df["In_OEM1"] == 1]
        for col in df.columns[0:4]:      # die ersten vier Spalten sind ID_T...
            oem1_teil_ids.update(nur_oem1[col].dropna())

    # 6) Dieselbe Markierung bei den Einzelteilen setzen
    for df in einzelteile.values():
        df["In_OEM1"] = df["Part_ID"].isin(oem1_teil_ids).astype(int)

    return einzelteile, komponenten


# ------------------------------------------------------------------
# Auswertung
# ------------------------------------------------------------------
def calc_stats(einzelteile, nur_oem1=False):
    """Marktanteil und Fehlerquote von Firma 202 je Teiletyp."""
    rows = []
    for teil, df in einzelteile.items():
        if nur_oem1:
            df = df[df["In_OEM1"] == 1]

        df_202 = df[df["Herstellernummer"] == 202]
        df_competitor = df[df["Herstellernummer"] != 202]

        count_all = df["Part_ID"].nunique()
        count_202 = df_202["Part_ID"].nunique()
        count_competitor = df_competitor["Part_ID"].nunique()

        defekt_202 = df_202[df_202["Fehlerhaft"] == 1]["Part_ID"].nunique()
        defekt_competitor = df_competitor[df_competitor["Fehlerhaft"] == 1]["Part_ID"].nunique()

        rows.append({
            "Teil": teil,
            "Teile gesamt": count_all,
            "Teile 202": count_202,
            "Teile Konkurrenz": count_competitor,
            "Marktanteil 202 (%)": round(count_202 / count_all * 100, 2),
            "Fehlerquote 202 (%)": round(defekt_202 / count_202 * 100, 2),
            "Fehlerquote Konkurrenz (%)": round(defekt_competitor / count_competitor * 100, 2),
        })
    return pd.DataFrame(rows)


def calc_useage(komponenten):
    """Anteil der Motoren, in denen mindestens ein Teil von 202 steckt."""
    rows = []
    for motor, df in zip(motoren, komponenten):
        split_cols = df.columns[0:4]
        # enthält eine der vier Teile-IDs die Herstellernummer 202?
        has_202 = df[split_cols].apply(lambda s: s.str.contains("-202-")).any(axis=1)

        rows.append({
            "Motor": motor,
            "Motoren gesamt": len(df),
            "Motoren mit 202": has_202.sum(),
            "Anteil mit 202 (%)": round(has_202.mean() * 100, 2),
        })

    result = pd.DataFrame(rows)
    result["Jeder wievielte Motor"] = round(100 / result["Anteil mit 202 (%)"], 2)
    return result


# ------------------------------------------------------------------
# App
# ------------------------------------------------------------------
einzelteile, komponenten = load_data()

# --- Seitenleiste ---
# Logo nur anzeigen, wenn es die Datei auch wirklich gibt.
if os.path.exists("www/logo.png"):
    st.sidebar.image("www/logo.png", width="stretch")
st.sidebar.title("Filter")

all_data = pd.concat([df["Produktionsdatum"] for df in einzelteile.values()])
von, bis = st.sidebar.date_input(
    "Produktionszeitraum",
    value=(all_data.min(), all_data.max()),
    min_value=all_data.min(),
    max_value=all_data.max(),
)

nur_oem1 = st.sidebar.checkbox("Nur Teile aus OEM1-Fahrzeugen", value=False)

page = st.sidebar.radio(
    "Seite",
    ["Übersicht", "Marktanteil", "Qualität (OEM1)", "Motor-Durchdringung", "Datentabellen"],
)

# --- Datum filtern ---
filtered = {}
for teil, df in einzelteile.items():
    passend = (df["Produktionsdatum"] >= pd.to_datetime(von)) & (df["Produktionsdatum"] <= pd.to_datetime(bis))
    filtered[teil] = df[passend]

stats = calc_stats(filtered, nur_oem1)
stats_oem1 = calc_stats(filtered, nur_oem1=True)
useage = calc_useage(komponenten)

# --- Seiten ---
if page == "Übersicht":
    st.title("Firma 202 - Übersicht")
    st.write("Die wichtigsten Kennzahlen für das Marketing.")

    market_share = round(stats["Teile 202"].sum() / stats["Teile gesamt"].sum() * 100, 2)
    # Über alle Motortypen zusammen zählen (nicht den Mittelwert der Prozente
    # nehmen, sonst zählen kleine und große Motortypen gleich viel).
    motors_w_202 = round(
        useage["Motoren mit 202"].sum() / useage["Motoren gesamt"].sum() * 100, 2
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Marktanteil von 202", f"{market_share} %")
    col2.metric("Motoren mit Teilen von 202", f"{motors_w_202} %")
    col3.metric("Werbeslogan", f"Jeder {100 / motors_w_202:.1f}. Motor")

    graph = px.bar(stats, x="Teil", y="Marktanteil 202 (%)",
                   title="Marktanteil von 202 je Teiletyp",
                   color_discrete_sequence=[blue])
    st.plotly_chart(graph, width="stretch")

elif page == "Marktanteil":
    st.title("Marktanteil")
    st.write("Firma 202 im Vergleich zur Konkurrenz, je Teiletyp (Aufgabe 1).")

    # Aus zwei Spalten eine lange Tabelle machen, damit Plotly gruppieren kann.
    lang = stats.melt(
        id_vars="Teil",
        value_vars=["Teile 202", "Teile Konkurrenz"],
        var_name="Hersteller",
        value_name="Anzahl",
    )
    graph = px.bar(lang, x="Teil", y="Anzahl", color="Hersteller", barmode="group",
                   title="Produzierte Teile: 202 gegen Konkurrenz",
                   color_discrete_map={"Teile 202": blue, "Teile Konkurrenz": grey})
    st.plotly_chart(graph, width="stretch")
    st.dataframe(stats, width="stretch")

elif page == "Qualität (OEM1)":
    st.title("Qualität / Fehlerquote (OEM1)")
    st.write("Fehlerquote von 202 gegen Konkurrenz, nur OEM1-Fahrzeuge (Aufgabe 2).")

    lang = stats_oem1.melt(
        id_vars="Teil",
        value_vars=["Fehlerquote 202 (%)", "Fehlerquote Konkurrenz (%)"],
        var_name="Hersteller",
        value_name="Fehlerquote (%)",
    )
    graph = px.bar(lang, x="Teil", y="Fehlerquote (%)", color="Hersteller", barmode="group",
                   title="Fehlerquote je Teiletyp (nur OEM1)",
                   color_discrete_map={"Fehlerquote 202 (%)": blue, "Fehlerquote Konkurrenz (%)": grey})
    st.plotly_chart(graph, width="stretch")
    st.dataframe(stats_oem1, width="stretch")

elif page == "Motor-Durchdringung":
    st.title("Motor-Durchdringung")
    st.write('Werbeaussage: "In jedem x-ten Motor steckt ein Teil von 202." (Aufgabe 3)')

    graph = px.bar(useage, x="Motor", y="Anteil mit 202 (%)",
                   title="Anteil der Motoren mit Teilen von 202",
                   color_discrete_sequence=[blue])
    st.plotly_chart(graph, width="stretch")
    st.dataframe(useage, width="stretch")

elif page == "Datentabellen":
    st.title("Datentabellen")

    st.subheader("Einzelteile")
    teil = st.selectbox("Teiletyp", teile)
    st.dataframe(filtered[teil].head(1000), width="stretch")
    st.download_button(
        "Als CSV herunterladen",
        data=filtered[teil].to_csv(index=False).encode("utf-8"),
        file_name=teil + ".csv",
    )

    st.subheader("Komponenten")
    motor = st.selectbox("Motortyp", motoren)
    st.dataframe(komponenten[motoren.index(motor)].head(1000), width="stretch")
