# IDA Case Study | Group 14

SoSe 2026 | Introduction to Data Analytics

## Setup

All required packages are listed in `environment.yml`.

```
conda env create -f environment.yml
conda activate ida-group-14
```

## Running the web application

```
streamlit run SoSe26_Case_Study_App_Group_14.py
```

The app loads `SoSe26_Case_Study_finalData_Group_14.parquet`. If Parquet cannot be read it automatically falls back to `SoSe26_Case_Study_finalData_Group_14.csv`, which holds the same data. Both files are included.

Parquet is the default because the dataset has 9.3 million rows and loads roughly ten times faster in that format.