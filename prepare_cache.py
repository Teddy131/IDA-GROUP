"""
Run this whenever the raw data changes) to pre-process the large
Einzelteil / Komponente / Fahrzeug files and cache the cleaned result to disk.

HOW TO RUN (once, in the terminal, from the project folder):
    python prepare_cache.py

This creates a ./cache/ folder with:
    einzelteile.pkl   (dict of the 5 cleaned T01-T05 dataframes, with In_OEM1 flag)
    engine_dfs.pkl     (list of the 4 cleaned engine/component dataframes, with In_OEM1 flag)

Re-run this script whenever the raw data in ./data/ changes.
"""

import io
import pickle
import time
from pathlib import Path

import pandas as pd

DATA = Path("data")
CACHE = Path("cache")
CACHE.mkdir(exist_ok=True)

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


def load_einzelteil(key: str) -> pd.DataFrame:
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
        "Part_ID", "Herstellernummer", "Werksnummer", "Produktionsdatum",
        "Fehlerhaft", "Fehlerhaft_Datum", "Fehlerhaft_Fahrleistung",
    ]
    return df[columns].reset_index(drop=True)


def main() -> None:
    t0 = time.time()

    print("Loading Einzelteile (this is the slow part for large files)...")
    einzelteile = {}
    for key in FILES:
        step_start = time.time()
        einzelteile[key] = load_einzelteil(key)
        print(f"  {key.upper()} loaded in {time.time() - step_start:.1f}s "
              f"({len(einzelteile[key]):,} rows)")

    print("Loading engine/component + OEM1 files...")
    engine_dfs = []
    for path in ENGINE_FILE_PATHS:
        df = pd.read_csv(path, sep=";").drop(columns=["Unnamed: 0"], errors="ignore")
        engine_dfs.append(df)

    oem_parts = [
        pd.read_csv(path, sep=";").drop(columns=["Unnamed: 0"], errors="ignore")
        for path in OEM1_FILE_PATHS
    ]
    oem_combined = pd.concat(oem_parts, ignore_index=True)

    print("Flagging In_OEM1...")
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

    print("Saving cache to ./cache/ ...")
    with open(CACHE / "einzelteile.pkl", "wb") as f:
        pickle.dump(einzelteile, f, protocol=pickle.HIGHEST_PROTOCOL)
    with open(CACHE / "engine_dfs.pkl", "wb") as f:
        pickle.dump(engine_dfs, f, protocol=pickle.HIGHEST_PROTOCOL)

    print(f"Done in {time.time() - t0:.1f}s total. "
          f"The Streamlit app will now load almost instantly.")


if __name__ == "__main__":
    main()
