Option Explicit
Dim fso, shell, root, mainfile, check

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
mainfile = root & "\main.py"

If Not fso.FileExists(mainfile) Then
    MsgBox "main.py est introuvable." & vbCrLf & _
           "Relance VYRON depuis son dossier d'origine.", vbCritical, "VYRON"
    WScript.Quit
End If

If shell.Run("cmd /c where py >nul 2>nul", 0, True) <> 0 Then
    MsgBox "Python 3.10 ou plus est requis." & vbCrLf & _
           "Installe Python en cochant ""Add Python to PATH"", puis relance VYRON.", _
           vbCritical, "VYRON"
    WScript.Quit
End If

check = "cmd /c py -c ""import customtkinter, psutil"" >nul 2>nul"
If shell.Run(check, 0, True) <> 0 Then
    shell.Popup "Premiere installation de VYRON..." & vbCrLf & _
                "Installation des dependances, cela peut prendre une minute.", _
                6, "VYRON", 64
    shell.Run "cmd /c py -m pip install -r requirements.txt", 0, True
End If

If shell.Run(check, 0, True) <> 0 Then
    MsgBox "Impossible d'installer les dependances." & vbCrLf & _
           "Verifie ta connexion Internet, puis lance INSTALL_VYRON.bat " & _
           "pour voir le detail de l'erreur.", vbCritical, "VYRON"
    WScript.Quit
End If

If shell.Run("cmd /c where pyw >nul 2>nul", 0, True) = 0 Then
    shell.Run "pyw """ & mainfile & """", 0, False
Else
    shell.Run "pythonw """ & mainfile & """", 0, False
End If
