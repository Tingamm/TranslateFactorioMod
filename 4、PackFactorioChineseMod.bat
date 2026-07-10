@echo off
chcp 65001 >nul
powershell.exe -ExecutionPolicy Bypass -File "%~dp0PackFactorioChineseMod.ps1"
pause
