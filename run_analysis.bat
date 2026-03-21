@echo off
REM Financial Position Analysis Pipeline Runner
REM This batch file runs the complete analysis pipeline for one or more simulations
REM Usage:
REM   run_analysis.bat                         Run default simulation (TWOFISH)
REM   run_analysis.bat TWOFISH                 Run specific simulation
REM   run_analysis.bat TWOFISH BLOWFISH        Run multiple simulations
REM   run_analysis.bat TWOFISH BLOWFISH --compare  Run multiple and compare
REM   run_analysis.bat --help                  Show help

setlocal enabledelayedexpansion

REM Default values
set SIMULATIONS=TWOFISH
set COMPARE_MODE=0
set POS_DIR=pos
set POS_DIR_BASE=
set OUTPUT_BASE_DIR=outputs

REM Parse command line arguments
:parse_args
if "%~1"=="" goto end_parse
if /i "%~1"=="--help" goto show_help
if /i "%~1"=="-h" goto show_help
if /i "%~1"=="--compare" (
    set COMPARE_MODE=1
    shift /1
    goto parse_args
)
if /i "%~1"=="--pos-dir" (
    set POS_DIR=%~2
    shift /2
    goto parse_args
)
if /i "%~1"=="--pos-dir-base" (
    set POS_DIR_BASE=%~2
    shift /2
    goto parse_args
)
if /i "%~1"=="--output-dir" (
    set OUTPUT_BASE_DIR=%~2
    shift /2
    goto parse_args
)
if "%~1"=="--*" (
    echo Error: Unknown option %~1
    echo Use --help for usage information
    exit /b 1
)
REM Assume it's a simulation name
if "!SIMULATIONS!"=="TWOFISH" (
    set SIMULATIONS=%~1
) else (
    set SIMULATIONS=!SIMULATIONS! %~1
)
shift /1
goto parse_args

:show_help
echo Financial Position Analysis Pipeline
echo Usage: %0 [SIMULATION...] [--compare] [--pos-dir DIR] [--pos-dir-base DIR] [--output-dir DIR]
echo.
echo Arguments:
echo   SIMULATION...    One or more simulation names (default: TWOFISH)
echo   --compare        Run comparison after analyzing all simulations
echo   --pos-dir DIR    Directory containing position files (default: pos)
echo   --pos-dir-base DIR Base directory with simulation subdirectories
echo                    (if set, uses DIR\SIMULATION\pos for each simulation)
echo   --output-dir DIR Base output directory (default: outputs)
echo   --help, -h       Show this help message
exit /b 0

:end_parse

echo ========================================
echo Financial Position Analysis Pipeline
echo ========================================
echo Starting at: %date% %time%
echo.
echo Configuration:
echo   Simulations: %SIMULATIONS%
if not "%POS_DIR_BASE%"=="" (
    echo   Position directory base: %POS_DIR_BASE% (simulation subdirectories: BASE\SIM\pos)
) else (
    echo   Position directory: %POS_DIR%
)
echo   Output directory: %OUTPUT_BASE_DIR%
echo   Compare mode: %COMPARE_MODE%
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

REM Create output base directory
if not exist "%OUTPUT_BASE_DIR%" mkdir "%OUTPUT_BASE_DIR%"

REM Function to run pipeline for a single simulation
REM %1 = simulation name, %2 = position directory, %3 = output base directory
:run_simulation
set SIM=%~1
set POS_DIR_ARG=%~2
set OUTPUT_BASE_ARG=%~3

echo.
echo ========================================
echo Analyzing simulation: %SIM%
echo ========================================

REM Step 1: Combine data
echo.
echo Step 1: Combining position files with industry data
echo ----------------------------------------

REM Check if output already exists
set SIM_OUTPUT_DIR=%OUTPUT_BASE_ARG%\%SIM%
set COMBINED_FILE=%SIM_OUTPUT_DIR%\combined_positions_with_industry.csv

if exist "%COMBINED_FILE%" (
    echo Note: Combined data already exists for %SIM%
    echo It will be overwritten with new data
    set /p CONTINUE=Continue? (y/n):
    if /i not "!CONTINUE!"=="y" (
        echo Skipping %SIM%
        exit /b 0
    )
)

echo Running combine_data.py for %SIM%...
python combine_data.py --simulation "%SIM%" --pos-dir "%POS_DIR_ARG%" --output-dir "%OUTPUT_BASE_ARG%"
if errorlevel 1 (
    echo ERROR: combine_data.py failed for %SIM%
    exit /b 1
)

REM Step 2: P&L Analysis
echo.
echo Step 2: Calculating P&L by sector and generating visualizations
echo ----------------------------------------

set PLOTS_DIR=%SIM_OUTPUT_DIR%\pnl_plots
set RESULTS_DIR=%SIM_OUTPUT_DIR%\pnl_results

if exist "%PLOTS_DIR%" (
    echo Note: Previous analysis results exist for %SIM%
    echo They will be overwritten with new results
    set /p CONTINUE=Continue? (y/n):
    if /i not "!CONTINUE!"=="y" (
        echo Skipping P^&L analysis for %SIM%
        exit /b 0
    )
)

echo Running pnl_analysis.py for %SIM%...
python pnl_analysis.py --simulation "%SIM%" --output-dir "%OUTPUT_BASE_ARG%"
if errorlevel 1 (
    echo ERROR: pnl_analysis.py failed for %SIM%
    exit /b 1
)

REM Step 3: Generate reports
echo.
echo Step 3: Generating comprehensive reports
echo ----------------------------------------

set REPORT_MD=%SIM%_analysis_report.md
set REPORT_HTML=%SIM%_analysis_report.html

if exist "%REPORT_MD%" (
    echo Note: Previous reports exist for %SIM%
    echo They will be overwritten with new reports
    set /p CONTINUE=Continue? (y/n):
    if /i not "!CONTINUE!"=="y" (
        echo Skipping report generation for %SIM%
        exit /b 0
    )
)

echo Running generate_report.py for %SIM%...
python generate_report.py --simulation "%SIM%" --output-dir "%OUTPUT_BASE_ARG%"
if errorlevel 1 (
    echo ERROR: generate_report.py failed for %SIM%
    exit /b 1
)

echo.
echo ✓ Completed analysis for %SIM%
echo   Output directory: %SIM_OUTPUT_DIR%
echo   Report: %SIM%_analysis_report.{md,html}
exit /b 0

REM Main execution
echo.
echo ========================================
echo Starting analysis for simulations: %SIMULATIONS%
echo ========================================

set FAILED_SIMS=
for %%s in (%SIMULATIONS%) do (
    echo.
    echo Processing simulation: %%s

    REM Determine position directory based on POS_DIR_BASE
    if not "%POS_DIR_BASE%"=="" (
        set SIM_POS_DIR=%POS_DIR_BASE%\%%s\pos
    ) else (
        set SIM_POS_DIR=%POS_DIR%
    )
    echo Using position directory: !SIM_POS_DIR!

    call :run_simulation %%s "!SIM_POS_DIR!" "%OUTPUT_BASE_DIR%"
    if errorlevel 1 (
        echo ✗ Failed to analyze %%s
        set FAILED_SIMS=!FAILED_SIMS! %%s
    ) else (
        echo ✓ Successfully analyzed %%s
    )
)

REM Run comparison if requested
if "%COMPARE_MODE%"=="1" (
    echo.
    echo ========================================
    echo Running comparison analysis
    echo ========================================

    REM Build list of successful simulations
    set SUCCESSFUL_SIMS=
    for %%s in (%SIMULATIONS%) do (
        set SKIP=0
        for %%f in (%FAILED_SIMS%) do (
            if "%%s"=="%%f" set SKIP=1
        )
        if "!SKIP!"=="0" (
            set SUCCESSFUL_SIMS=!SUCCESSFUL_SIMS! %%s
        )
    )

    REM Count successful simulations
    set COUNT=0
    for %%s in (!SUCCESSFUL_SIMS!) do set /a COUNT+=1

    if !COUNT! LSS 2 (
        echo Warning: Need at least 2 successful simulations for comparison
        echo Skipping comparison (failed simulations: %FAILED_SIMS%)
    ) else (
        echo Comparing simulations: !SUCCESSFUL_SIMS!

        REM Run comparison
        python compare_simulations.py !SUCCESSFUL_SIMS! --output-base-dir "%OUTPUT_BASE_DIR%"
        if errorlevel 1 (
            echo ERROR: compare_simulations.py failed
        ) else (
            REM Generate comparison report
            python generate_comparison_report.py --comparison-dir "%OUTPUT_BASE_DIR%\comparison" --output-dir "%OUTPUT_BASE_DIR%\comparison"
            if errorlevel 1 (
                echo ERROR: generate_comparison_report.py failed
            ) else (
                echo ✓ Comparison completed
                echo   Comparison directory: %OUTPUT_BASE_DIR%\comparison
                echo   Report: %OUTPUT_BASE_DIR%\comparison\comparison_report.{md,html}
            )
        )
    )
)

REM Summary
echo.
echo ========================================
echo Pipeline completed!
echo ========================================

REM Count total simulations
set TOTAL_COUNT=0
for %%s in (%SIMULATIONS%) do set /a TOTAL_COUNT+=1

REM Count failed simulations
set FAILED_COUNT=0
for %%s in (%FAILED_SIMS%) do set /a FAILED_COUNT+=1

set /a SUCCESS_COUNT=TOTAL_COUNT-FAILED_COUNT

echo Summary:
echo   Total simulations: %TOTAL_COUNT%
echo   Successful: %SUCCESS_COUNT%
echo   Failed: %FAILED_COUNT%
if not "%FAILED_SIMS%"=="" echo   Failed simulations: %FAILED_SIMS%
echo.
echo Output structure:
echo   %OUTPUT_BASE_DIR%\
for %%s in (%SIMULATIONS%) do (
    set SKIP=0
    for %%f in (%FAILED_SIMS%) do (
        if "%%s"=="%%f" set SKIP=1
    )
    if !SKIP!==0 (
        echo     ├── %%s\
        echo     │   ├── combined_positions_with_industry.csv
        echo     │   ├── pnl_results\
        echo     │   ├── pnl_plots\
        echo     │   └── %%s_analysis_report.{md,html}
    )
)
if "%COMPARE_MODE%"=="1" (
    set SUCCESS_COUNT=0
    for %%s in (%SIMULATIONS%) do (
        set SKIP=0
        for %%f in (%FAILED_SIMS%) do (
            if "%%s"=="%%f" set SKIP=1
        )
        if !SKIP!==0 set /a SUCCESS_COUNT+=1
    )
    if !SUCCESS_COUNT! GEQ 2 (
        echo     └── comparison\
        echo         ├── comparison_plots\
        echo         ├── comparison_data\
        echo         └── comparison_report.{md,html}
    )
)

echo.
echo Completed at: %date% %time%
echo ========================================

REM Exit with error if any simulations failed
if not "%FAILED_SIMS%"=="" exit /b 1
pause