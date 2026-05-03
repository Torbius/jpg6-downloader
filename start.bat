@echo off
setlocal

set "APP_DIR=%~dp0"
set "PYW=%APP_DIR%..\..\.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%APP_DIR%..\.venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=%APP_DIR%venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"

start "" "%PYW%" "%APP_DIR%main.py"
