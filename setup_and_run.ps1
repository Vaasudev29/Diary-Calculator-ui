param(
	[switch]$RunImmediately
)

# Windows PowerShell helper to create a virtual environment, install requirements, and optionally run the Streamlit app.
# Usage:
#   PowerShell -ExecutionPolicy Bypass -File .\setup_and_run.ps1        # create venv and install deps
#   PowerShell -ExecutionPolicy Bypass -File .\setup_and_run.ps1 -RunImmediately

Write-Output "Working directory: $(Get-Location)"

if (-not (Test-Path ".venv")) {
	Write-Output "Creating virtual environment .venv..."
	python -m venv .venv
} else {
	Write-Output "Virtual environment already exists: .venv"
}

$venvPython = Join-Path -Path (Join-Path -Path (Get-Location) -ChildPath ".venv") -ChildPath "Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
	Write-Error "Cannot find venv python at $venvPython. Ensure Python is installed and available as 'python'."
	exit 1
}

Write-Output "Upgrading pip and installing requirements..."
& $venvPython -m pip install --upgrade pip
if (Test-Path "requirements.txt") {
	& $venvPython -m pip install -r requirements.txt
} else {
	Write-Output "No requirements.txt found; skipping pip install -r requirements.txt"
}

if ($RunImmediately) {
	Write-Output "Starting Streamlit app..."
	& $venvPython -m streamlit run app.py
}
