Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

strPythonw = strPath & "\.venv\Scripts\pythonw.exe"

If Not fso.FileExists(strPythonw) Then
    strPythonw = "pythonw.exe"
End If

WshShell.Run """" & strPythonw & """ """ & strPath & "\main.py""", 0, False

