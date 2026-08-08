How to run the Streamlit app (Windows PowerShell)

1) Create venv and install dependencies (recommended):

   PowerShell -ExecutionPolicy Bypass -File .\setup_and_run.ps1

2) Create venv, install dependencies, and run immediately:

   PowerShell -ExecutionPolicy Bypass -File .\setup_and_run.ps1 -RunImmediately

Alternative (cmd.exe):

   run.bat

Manual steps if you prefer interactive commands:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1   # in PowerShell
   pip install -r requirements.txt
   streamlit run app.py

The app opens by default at http://localhost:8501

Downloadable ZIP
-----------------
The Streamlit app now includes a "Project release" expander with a "Create ZIP release" button. Click it to prepare a ZIP and then use the provided download button to download Dairy_Yield_Chain_Updated.zip. The archive excludes common development folders (.venv, .git, __pycache__, .streamlit).
