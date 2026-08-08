$pythonPrefix = python -c "import sys; print(sys.prefix)"
$condaLibraryBin = Join-Path $pythonPrefix "Library\bin"

if (Test-Path $condaLibraryBin) {
    $env:PATH = "$condaLibraryBin;$env:PATH"
}

python -m streamlit run app.py
