@echo off
cd /d "%~dp0"

for /f "delims=" %%D in ('dir /a:d /b /s ^| sort /r') do (
    rd "%%D" 2>nul
)