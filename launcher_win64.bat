@echo off

REM Get current timestamp and format it as YYYYMMDD_HHMMSS
for /f "tokens=2 delims==." %%I in ('"wmic os get localdatetime /value"') do set datetime=%%I
set timestamp=%datetime:~0,8%_%datetime:~8,6%

REM Set log file path with timestamp
set LOGFILE=D:\Users\ntuhuser\Desktop\AutoDigiSign\logs\autorun_%timestamp%.log

REM Redirect all output to the log file
(
    echo Running Python script...
    py "D:\Users\ntuhuser\Desktop\AutoDigiSign\main.py"
    
    echo Python script finished. Checking exit status...
    REM Check if the email was sent successfully
    IF %ERRORLEVEL% EQU 0 (
        echo Email sent successfully.
    ) ELSE (
        echo Email failed to send. Keeping the window open for troubleshooting.
        pause
    )
    
    echo Done. Closing the script in 5 seconds.
    timeout /t 5 /nobreak >nul
) > %LOGFILE% 2>&1

exit
