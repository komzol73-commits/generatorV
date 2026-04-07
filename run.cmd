@echo off
setlocal
set "APPDIR=%~dp0"
set "PYTHONW=C:\Users\turch\AppData\Local\Programs\Python\Python310\pythonw.exe"
set "PYTHON=C:\Users\turch\AppData\Local\Programs\Python\Python310\python.exe"
if exist "%PYTHONW%" (
  start "" "%PYTHONW%" "%APPDIR%gui_app.py"
) else (
  start "" "%PYTHON%" "%APPDIR%gui_app.py"
)
endlocal
