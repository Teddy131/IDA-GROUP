# IDA Case Study | Group 14

SoSe 2026 | Introduction to Data Analytics

## Setup

No installation needed. Every package used here ships with the current Anaconda distribution (verified against Anaconda 2026.07: pandas 3.0.3, plotly 6.7.0, pyarrow 23.0.1, streamlit 1.58.0, numpy, scipy, scikit-learn, matplotlib).

An `environment.yml` is included in case an isolated environment is preferred:

```
conda env create -f environment.yml
conda activate ida-group-14
```

## Running the web application
Run it from this root folder because the code uses relative paths

```
streamlit run SoSe26_Case_Study_App_Group_14.py
```

The app loads `SoSe26_Case_Study_finalData_Group_14.parquet`. If Parquet cannot be read it automatically falls back to `SoSe26_Case_Study_finalData_Group_14.csv`, which holds the same data. Both files are included.

Parquet is the default because the dataset has 9.3 million rows and loads roughly ten times faster in that format.