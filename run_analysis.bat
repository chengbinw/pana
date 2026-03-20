@echo off
REM Financial Position Analysis Pipeline Runner
REM This batch file runs the complete analysis pipeline in sequence:
REM 1. combine_data.py - Combines daily position files with industry data
REM 2. pnl_analysis.py - Calculates P&L by sector and generates visualizations
REM 3. generate_report.py - Generates comprehensive markdown and HTML reports

echo ========================================
echo Financial Position Analysis Pipeline
echo ========================================
echo Starting at: %date% %time%
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.6 or higher
    pause
    exit /b 1
)

REM Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%

REM Check if required packages are installed
echo Checking for required Python packages...
python -c "import pandas, numpy, matplotlib, seaborn, pathlib" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Missing required Python packages
    echo Please install with: pip install pandas numpy matplotlib seaborn
    pause
    exit /b 1
) else (
    echo ✓ All required packages are installed
)

REM Step 1: Combine data
echo.
echo ========================================
echo Step 1: Combining position files with industry data
echo ========================================
if exist "combined_positions_with_industry.csv" (
    echo Note: combined_positions_with_industry.csv already exists
    echo It will be overwritten with new data
    set /p CONTINUE=Continue? (y/n):
    if /i not "%CONTINUE%"=="y" (
        echo Aborted by user
        pause
        exit /b 0
    )
)

python combine_data.py
if errorlevel 1 (
    echo ERROR: combine_data.py failed
    pause
    exit /b 1
)

REM Step 2: P&L Analysis
echo.
echo ========================================
echo Step 2: Calculating P&L by sector and generating visualizations
echo ========================================
if exist "pnl_plots" (
    echo Note: Previous analysis results exist
    echo They will be overwritten with new results
    set /p CONTINUE=Continue? (y/n):
    if /i not "%CONTINUE%"=="y" (
        echo Aborted by user
        pause
        exit /b 0
    )
)

python pnl_analysis.py
if errorlevel 1 (
    echo ERROR: pnl_analysis.py failed
    pause
    exit /b 1
)

REM Step 3: Generate reports
echo.
echo ========================================
echo Step 3: Generating comprehensive reports
echo ========================================
if exist "position_analysis_report.md" (
    echo Note: Previous reports exist
    echo They will be overwritten with new reports
    set /p CONTINUE=Continue? (y/n):
    if /i not "%CONTINUE%"=="y" (
        echo Aborted by user
        pause
        exit /b 0
    )
)

python generate_report.py
if errorlevel 1 (
    echo ERROR: generate_report.py failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Pipeline completed successfully!
echo ========================================
echo Generated outputs:
echo.
echo 1. Data Files:
echo    - combined_positions_with_industry.csv (Combined dataset)
echo.
echo 2. Analysis Results:
echo    - pnl_results\ (Intermediate analysis CSVs)
echo.
echo 3. Visualizations:
echo    - pnl_plots\ (5 visualization PNGs)
echo.
echo 4. Reports:
echo    - position_analysis_report.md (Markdown report)
echo    - position_analysis_report.html (HTML report)
echo.
echo Completed at: %date% %time%
echo ========================================
pause