#!/bin/bash

# Financial Position Analysis Pipeline Runner
# This script runs the complete analysis pipeline in sequence:
# 1. combine_data.py - Combines daily position files with industry data
# 2. pnl_analysis.py - Calculates P&L by sector and generates visualizations
# 3. generate_report.py - Generates comprehensive markdown and HTML reports

set -e  # Exit on any error

echo "========================================"
echo "Financial Position Analysis Pipeline"
echo "========================================"
echo "Starting at: $(date)"
echo ""

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "ERROR: Python is not installed or not in PATH"
    echo "Please install Python 3.6 or higher"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

# Check if required packages are installed
echo "Checking for required Python packages..."
python -c "import pandas, numpy, matplotlib, seaborn, pathlib" && \
    echo "✓ All required packages are installed" || {
    echo "ERROR: Missing required Python packages"
    echo "Please install with: pip install pandas numpy matplotlib seaborn"
    exit 1
}

# Step 1: Combine data
echo ""
echo "========================================"
echo "Step 1: Combining position files with industry data"
echo "========================================"
if [ -f "combined_positions_with_industry.csv" ]; then
    echo "Note: combined_positions_with_industry.csv already exists"
    echo "It will be overwritten with new data"
    read -p "Continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted by user"
        exit 0
    fi
fi

python combine_data.py
if [ $? -ne 0 ]; then
    echo "ERROR: combine_data.py failed"
    exit 1
fi

# Step 2: P&L Analysis
echo ""
echo "========================================"
echo "Step 2: Calculating P&L by sector and generating visualizations"
echo "========================================"
if [ -d "pnl_plots" ] || [ -d "pnl_results" ]; then
    echo "Note: Previous analysis results exist"
    echo "They will be overwritten with new results"
    read -p "Continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted by user"
        exit 0
    fi
fi

python pnl_analysis.py
if [ $? -ne 0 ]; then
    echo "ERROR: pnl_analysis.py failed"
    exit 1
fi

# Step 3: Generate reports
echo ""
echo "========================================"
echo "Step 3: Generating comprehensive reports"
echo "========================================"
if [ -f "position_analysis_report.md" ] || [ -f "position_analysis_report.html" ]; then
    echo "Note: Previous reports exist"
    echo "They will be overwritten with new reports"
    read -p "Continue? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted by user"
        exit 0
    fi
fi

python generate_report.py
if [ $? -ne 0 ]; then
    echo "ERROR: generate_report.py failed"
    exit 1
fi

echo ""
echo "========================================"
echo "Pipeline completed successfully!"
echo "========================================"
echo "Generated outputs:"
echo ""
echo "1. Data Files:"
echo "   - combined_positions_with_industry.csv (Combined dataset)"
echo ""
echo "2. Analysis Results:"
echo "   - pnl_results/ (Intermediate analysis CSVs)"
echo ""
echo "3. Visualizations:"
echo "   - pnl_plots/ (5 visualization PNGs)"
echo ""
echo "4. Reports:"
echo "   - position_analysis_report.md (Markdown report)"
echo "   - position_analysis_report.html (HTML report)"
echo ""
echo "Completed at: $(date)"
echo "========================================"