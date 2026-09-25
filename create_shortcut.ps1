$desktop = [Environment]::GetFolderPath('Desktop')
$ws = New-Object -ComObject WScript.Shell
$shortcutPath = Join-Path $desktop "LogiMate AI Controller.lnk"
$s = $ws.CreateShortcut($shortcutPath)
$s.TargetPath = "F:\original final downloads\logism ai control\dist\AI_Logisim_Controller\AI_Logisim_Controller.exe"
$s.WorkingDirectory = "F:\original final downloads\logism ai control\dist\AI_Logisim_Controller"
$s.IconLocation = "F:\original final downloads\logism ai control\dist\AI_Logisim_Controller\app_icon.ico"
$s.Description = "LogiMate AI Controller Desktop App"
$s.Save()
Write-Host "SUCCESS: Desktop shortcut created at $shortcutPath"
