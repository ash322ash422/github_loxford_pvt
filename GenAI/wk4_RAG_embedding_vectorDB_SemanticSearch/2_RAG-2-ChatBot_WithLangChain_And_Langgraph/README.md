# STEPS

## Work with python3.10. Do not work with higher version.


### 1) Create virtual environment:

> C:\Users\hi\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv


### 2) Activate virtual envir

> .venv\Scripts\Activate.ps1


### 3) Install jupyter:

> python -m pip install jupyter

### 4) Run jupyter:

> python -m jupyter notebook

### 5) Install following packages from jupyter (or use python virtual end):

#### From Jupyter
> !pip install langchain==0.2.14 langchain-community==0.2.12 langchain-openai==0.1.25 langchain-text-splitters

OR

#### From command line

> .\.venv\Scripts\python.exe pip install langchain==0.2.14 langchain-community==0.2.12 langchain-openai==0.1.25 langchain-text-splitters
