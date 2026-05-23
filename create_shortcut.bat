@echo off
echo Creating desktop shortcuts...

:: Create "SHEIN Chrome" shortcut
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\SHEIN Chrome.lnk'); $s.TargetPath = '%~dp0chrome_debug.bat'; $s.WorkingDirectory = '%~dp0'; $s.IconLocation = 'C:\Program Files\Google\Chrome\Application\chrome.exe,0'; $s.Save()"

:: Create "SHEIN Auto Upload" shortcut
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%USERPROFILE%\Desktop\SHEIN Auto Upload.lnk'); $s.TargetPath = '%~dp0auto_start.bat'; $s.WorkingDirectory = '%~dp0'; $s.Save()"

echo Done! Check your desktop.
pause
