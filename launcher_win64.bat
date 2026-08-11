@echo off
setlocal

set "AUTODIGISIGN_SCHEDULED=0"
if /I "%~1"=="--scheduled" set "AUTODIGISIGN_SCHEDULED=1"

REM Use the project directory even when Task Scheduler starts elsewhere.
pushd "%~dp0"
if errorlevel 1 (
    echo AutoDigiSign could not open its project directory.
    exit /b 1
)

set "PYTHONPATH=%~dp0src"
if not exist "%~dp0.venv\Scripts\python.exe" goto missing_virtual_environment

echo Running AutoDigiSign...
"%~dp0.venv\Scripts\python.exe" -m autodigisign
set "AUTODIGISIGN_EXIT_CODE=%ERRORLEVEL%"
goto execution_finished

:missing_virtual_environment
echo Project virtual environment was not found.
echo Create it with: py -V:3.14 -m venv .venv
echo Then install the project with: .venv\Scripts\python.exe -m pip install --editable .
set "AUTODIGISIGN_EXIT_CODE=1"

:execution_finished
popd

REM Report the actual application result to interactive users and Task Scheduler.
IF %AUTODIGISIGN_EXIT_CODE% EQU 0 (
    echo AutoDigiSign completed successfully.
) ELSE (
    echo AutoDigiSign failed with exit code %AUTODIGISIGN_EXIT_CODE%.
)

IF "%AUTODIGISIGN_SCHEDULED%"=="0" (
    IF %AUTODIGISIGN_EXIT_CODE% EQU 0 (
        echo This launcher will exit in 10 seconds.
        timeout /t 10 /nobreak >nul
    ) ELSE (
        echo Press any key to close this launcher.
        pause >nul
    )
)

exit /b %AUTODIGISIGN_EXIT_CODE%
