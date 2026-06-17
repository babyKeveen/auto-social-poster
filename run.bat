@echo off
setlocal
cd /d "%~dp0"

if "%~1"=="" (
    set /p IMAGE="Image path: "
) else (
    set "IMAGE=%~1"
)

if not exist "%IMAGE%" (
    echo Image not found: %IMAGE%
    pause
    exit /b 1
)

set /p CAPTION="Caption: "

set /p PROVIDER="Provider [openai/gemini/moondream] (default moondream): "
if "%PROVIDER%"=="" set "PROVIDER=moondream"

set /p POSTTO="Post to [mastodon/instagram/all/none] (default none): "
if "%POSTTO%"=="" set "POSTTO=none"

if /i "%POSTTO%"=="none" (
    "%~dp0venv\Scripts\python.exe" "%~dp0main.py" "%IMAGE%" --caption "%CAPTION%" --provider %PROVIDER% --no-post
) else (
    "%~dp0venv\Scripts\python.exe" "%~dp0main.py" "%IMAGE%" --caption "%CAPTION%" --provider %PROVIDER% --post-to %POSTTO%
)

echo.
pause
