$p = Get-NetTCPConnection -LocalPort 8501 -ErrorAction SilentlyContinue
if ($p) {
	Write-Output "Found process id: $($p.OwningProcess)"
	try {
		Stop-Process -Id $p.OwningProcess -Force -ErrorAction Stop
		Write-Output "Stopped process $($p.OwningProcess)"
	} catch {
		Write-Output "Failed to stop process $($p.OwningProcess): $_"
	}
} else {
	# fallback: find any processes whose command line contains 'streamlit'
	$procs = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'streamlit' }
	if ($procs) {
		foreach ($pr in $procs) {
			Write-Output "Stopping PID: $($pr.ProcessId)"
			try {
				Stop-Process -Id $pr.ProcessId -Force -ErrorAction Stop
			} catch {
				Write-Output "Failed to stop PID $($pr.ProcessId): $_"
			}
		}
	} else {
		Write-Output 'No process found on port 8501 or streamlit processes'
	}
}
