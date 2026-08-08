@echo off
REM Convenience batch file for Windows (cmd.exe)
IF NOT EXIST ".venv\Scripts\python.exe" (
  echo Creating virtual environment .venv...
  python -m venv .venv
) ELSE (
  echo Virtual environment already exists
)

echo Upgrading pip and installing requirements...
.venv\Scripts\python.exe -m pip install --upgrade pip
IF EXIST requirements.txt (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
) ELSE (
  echo requirements.txt not found, skipping
)

echo Starting Streamlit app...
.venv\Scripts\python.exe -m streamlit run app.py
