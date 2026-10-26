@echo off
rem Silent launcher: hand over to VYRON.vbs so no console window stays open.
rem First setup or troubleshooting: run INSTALL_VYRON.bat instead.
start "" wscript //nologo "%~dp0VYRON.vbs"
exit /b 0
