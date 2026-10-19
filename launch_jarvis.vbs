Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "d:\engineers\JAY\MARK-56\Mark-LVI-main"
WshShell.Run """" & "d:\engineers\JAY\MARK-56\Mark-LVI-main\.venv\Scripts\pythonw.exe" & """ run_holo.py", 0, False
