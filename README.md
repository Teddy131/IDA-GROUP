# IDA-GROUP

Shared Jupyter notebooks for the group assignment. The Python environment is managed with [pixi](https://pixi.sh), so everyone works with identical package versions.

Do not use `conda install` or `pip install` in this project. See "Adding a package" below.

---

## 1. One-time setup

### Install pixi

**Windows** (PowerShell):

```powershell
winget install prefix-dev.pixi
```

If winget is not available:

```powershell
powershell -ExecutionPolicy ByPass -c "irm -useb https://pixi.sh/install.ps1 | iex"
```

**macOS** (Terminal):

```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

Or via Homebrew: `brew install pixi`

Close and reopen the terminal afterwards, then check:

```
pixi --version
```

### Create the environment

```
pixi install
```

### Add the data
 
The datasets are not part of the repository. Copy them into a `data/` folder in the project root so that all notebooks find them under the same relative paths:
 
```
IDA-GROUP/
└── data/
    ├── Einzelteil/
    ├── Fahrzeug/
    ├── Geodaten/
    ├── Komponente/
    ├── Logistikverzug/
    ├── Zulassungen/
    └── Einzelteil_T23.csv
```

---

## 2. Working in VS Code

1. **Open the folder**: File > Open Folder > `IDA-GROUP`. The interpreter is only found when the project root is the workspace.
2. Open a notebook, click the kernel selector in the top right, choose **Select Another Kernel > Python Environments**, and pick the entry under `.pixi/envs/default`.


---

## 3. Working in the browser/JupiterLab instead


```
pixi run jupyter lab
```


---

## 4. Adding a package

Whoever needs it runs:

```
pixi add <package_name>

# Example
pixi add matplotlib
```



# General Task distribution

* Task 1: Ibo + Fehmi

* Task 2: Fehmi

* Task 3+4: Leyla

* Task 5: Cagatay

* Task 6: Erol




General Tasks until next Meeting on NA
