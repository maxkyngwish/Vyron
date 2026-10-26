@echo off
cd /d "%~dp0"
title VYRON EXE Builder
where py >nul 2>nul
if errorlevel 1 (
 echo Python introuvable. Installe Python 3.10+ et coche Add Python to PATH.
 pause
 exit /b 1
)
py -m pip install -r requirements.txt
if errorlevel 1 goto fail
py -m pip install pyinstaller
if errorlevel 1 goto fail
py -m PyInstaller --noconfirm --clean --onefile --windowed --name VYRON --icon "vyron\assets\vyron.ico" --add-data "vyron\assets;vyron\assets" --collect-all customtkinter main.py
if errorlevel 1 goto fail
echo VYRON.exe cree dans le dossier dist.
start "" "%~dp0dist\VYRON.exe"
pause
exit /b 0
:fail
echo La construction a echoue. Lis le message d'erreur ci-dessus.
pause
exit /b 1
