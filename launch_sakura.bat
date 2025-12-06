@echo off
TITLE Sakura Assistant
CLS

REM Check if venv exists
IF NOT EXIST "PA" (
    ECHO ❌ Virtual environment not found.
    ECHO Please run 'python installer/bootstrap.py' first.
    PAUSE
    EXIT /B
)

REM Activate venv
CALL PA\Scripts\activate

REM Run Application
python run_sakura.py

PAUSE
