@echo off
cd /d "%~dp0"

IF NOT EXIST ".venv\" (
    echo Creating virtual environment...
    :: Створюємо .venv
    python -m venv .venv
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment. Make sure Python is installed and in PATH.
        pause
        exit /b
    )
)

call ".venv\Scripts\activate.bat"

IF NOT EXIST ".venv\Lib\site-packages\PySide6\" (
    echo Installing dependencies...
    pip install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        echo Failed to install dependencies.
        pause
        exit /b
    )
)

echo Starting Flipbook Creator...
START "Flipbook" pythonw Flipbook-Creator.py