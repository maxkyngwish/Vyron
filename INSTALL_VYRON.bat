@echo off
cd /d "%~dp0"
title VYRON - Installation
where py >nul 2>nul
if errorlevel 1 (
 echo Python introuvable. Installe Python 3.10+ et coche Add Python to PATH.
 pause
 exit /b 1
)
py -m pip install -r requirements.txt
if errorlevel 1 (
 echo Installation des dependances impossible.
 pause
 exit /b 1
)
echo Dependances installees. VYRON va demarrer sans fenetre de commande.
start "" wscript //nologo "%~dp0VYRON.vbs"
exit /b 0
