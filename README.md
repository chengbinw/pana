# Financial Position Analysis Pipeline

A Python-based pipeline for analyzing daily stock position files, calculating P&L by sector, and generating visualizations and reports.

## Overview

This project processes End-of-Day (EOD) position CSV files, merges them with industry sector mappings, calculates Profit & Loss by sector, and produces comprehensive visualizations and reports.

## Features

- **Data Combination**: Combines multiple daily position files into a single dataset
- **Industry Mapping**: Maps stock symbols to sectors using industry codes
- **P&L Analysis**: Calculates daily and cumulative P&L by sector
- **Visualizations**: Generates heatmaps, line charts, and bar charts
- **Report Generation**: Creates detailed markdown and HTML reports

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install pandas numpy matplotlib seaborn
   # or using requirements.txt
   pip install -r requirements.txt
   ```

2. **Run the analysis pipeline**:
   ```bash
   # Option 1: Run each script individually
   python combine_data.py        # Step 1: Combine data
   python pnl_analysis.py        # Step 2: Analyze P&L
   python generate_report.py     # Step 3: Generate reports

   # Option 2: Use the runner script (interactive)
   ./run_analysis.sh             # Linux/macOS/Git Bash
   # or
   run_analysis.bat              # Windows CMD

   # Option 3: Use the auto runner (no prompts, overwrites files)
   ./run_analysis_auto.sh        # Linux/macOS/Git Bash

   # Note: On first use, you may need to make bash scripts executable:
   # chmod +x run_analysis.sh run_analysis_auto.sh
   ```

## Project Structure

```
├── combine_data.py              # Data combination script
├── pnl_analysis.py              # P&L analysis script
├── generate_report.py           # Report generation script
├── run_analysis.sh              # Pipeline runner (Bash, interactive)
├── run_analysis.bat             # Pipeline runner (Windows CMD)
├── run_analysis_auto.sh         # Pipeline runner (Bash, auto mode)
├── requirements.txt             # Python dependencies
├── CLAUDE.md                    # Development guide
├── README.md                    # This file
├── .gitignore                   # Git exclusions
└── position_analysis_report.md  # Sample output report
```

## Runner Scripts

Three runner scripts are provided for convenience:

1. **`run_analysis.sh`** (Bash, interactive):
   - Runs all three Python scripts in sequence
   - Checks for dependencies and Python version
   - Prompts before overwriting existing files
   - Works on Linux, macOS, and Git Bash (Windows)

2. **`run_analysis.bat`** (Windows CMD):
   - Windows batch file with same functionality
   - Includes pause on error and completion

3. **`run_analysis_auto.sh`** (Bash, auto mode):
   - Automatically overwrites existing files without prompts
   - Useful for automated runs and CI/CD pipelines

All runners validate Python and package dependencies before starting.

## Data Requirements

Place the following in a `pos/` directory:
- Daily position files: `ePos_TWOFISH_YYYYMMDD_EOD.csv`
- Industry mapping: `Industry.csv`

**Note**: The `pos/` directory and generated data files are excluded from git via `.gitignore`.

## Outputs

- `combined_positions_with_industry.csv`: Combined dataset
- `pnl_plots/`: Visualization images (PNG)
- `pnl_results/`: Intermediate analysis results (CSV)
- `position_analysis_report.{md,html}`: Comprehensive reports

## License

This project is available for use and modification.