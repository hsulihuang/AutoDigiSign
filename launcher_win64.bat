@echo off

echo Running Python script...
py "D:\Users\ntuhuser\Desktop\AutoDigiSign\src\main.py"
echo Python script finished. Checking exit status...

REM Check if the email was sent successfully
IF %ERRORLEVEL% EQU 0 (
    echo Email sent successfully.
) ELSE (
    echo Email failed to send. Keeping the window open for troubleshooting.
    pause
)

echo Done. Closing the script in 10 seconds.
timeout /t 10 /nobreak >nul

exit
