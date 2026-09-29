@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist "out\last_edited.txt" (echo Run 2 first. & pause & exit /b)
set /p F=<"out\last_edited.txt"
start "" "%F%"
