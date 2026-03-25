# Financial Position Analysis Pipeline

A Python-based pipeline for analyzing daily stock position files, calculating P&L by sector, and generating visualizations and reports.

## Overview

This project processes End-of-Day (EOD) position CSV files, merges them with industry sector mappings, calculates Profit & Loss by sector, and produces comprehensive visualizations and reports.

## Features

- **Multi-Simulation Support**: Process one or more simulation datasets (e.g., TWOFISH, BLOWFISH, bye, byd)
- **Data Combination**: Combines daily position files into simulation-specific datasets
- **Industry Mapping**: Maps stock symbols to sectors (2-digit industry codes) and bizsectors (4-digit industry groups) using hierarchical industry classification
- **Bizsector Analysis**: Additional granular analysis at 4-digit industry group (bizsector) level
- **P&L Analysis**: Calculates daily and cumulative P&L by sector and bizsector (industry group) for each simulation
- **Visualizations**: Generates heatmaps, line charts, and bar charts for individual simulations
- **Report Generation**: Creates detailed markdown and HTML reports for each simulation
- **Comparative Analysis**: Compares performance across multiple simulations with side-by-side metrics at both sector and bizsector levels
- **Comparative Visualizations**: Generates comparison charts, heatmaps, and correlation plots
- **Comprehensive Reporting**: Produces comparative analysis reports with insights and recommendations

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install pandas numpy matplotlib seaborn
   # or using requirements.txt
   pip install -r requirements.txt
   ```

2. **Run single simulation analysis**:
   ```bash
   # Option 1: Run each script individually (with simulation parameter)
   python combine_data.py --simulation TWOFISH --pos-dir pos
   python pnl_analysis.py --simulation TWOFISH --output-dir outputs
   python generate_report.py --simulation TWOFISH --output-dir outputs

   # Option 2: Use runner script (interactive)
   ./run_analysis.sh TWOFISH                    # Linux/macOS/Git Bash
   # or
   run_analysis.bat TWOFISH                     # Windows CMD

   # Option 3: Use auto runner (no prompts, overwrites files)
   ./run_analysis_auto.sh TWOFISH               # Linux/macOS/Git Bash

   # Note: On first use, you may need to make bash scripts executable:
   # chmod +x run_analysis.sh run_analysis_auto.sh
   ```

3. **Run multiple simulations with comparison**:
   ```bash
   # Analyze two simulations and compare results
   ./run_analysis_auto.sh bye byd --compare

   # With simulation subdirectories (e.g., bye/pos/, byd/pos/)
   ./run_analysis_auto.sh bye byd --pos-dir-base . --compare

   # Or run comparison on existing results
   python compare_simulations.py bye byd --output-base-dir outputs
   python generate_comparison_report.py --comparison-dir outputs/comparison
   ```

## Project Structure

```
├── combine_data.py              # Data combination script (multi-simulation)
├── pnl_analysis.py              # P&L analysis script (per simulation)
├── generate_report.py           # Report generation script (per simulation)
├── compare_simulations.py       # Comparative analysis script (multi-simulation)
├── generate_comparison_report.py # Comparison report generation
├── run_analysis.sh              # Pipeline runner (Bash, interactive)
├── run_analysis.bat             # Pipeline runner (Windows CMD)
├── run_analysis_auto.sh         # Pipeline runner (Bash, auto mode with comparison)
├── requirements.txt             # Python dependencies
├── CLAUDE.md                    # Development guide
├── README.md                    # This file
├── .gitignore                   # Git exclusions
└── Industry.csv                 # Industry mapping file
```

## Runner Scripts

Three runner scripts are provided for convenience, all supporting multi-simulation analysis and comparison:

1. **`run_analysis.sh`** (Bash, interactive):
   - Runs the complete pipeline for one or more simulations
   - Checks for dependencies and Python version
   - Prompts before overwriting existing files
   - Works on Linux, macOS, and Git Bash (Windows)
   - **Usage**: `./run_analysis.sh [SIMULATION...] [--compare] [--pos-dir-base DIR]`

2. **`run_analysis.bat`** (Windows CMD):
   - Windows batch file with same functionality
   - Includes pause on error and completion
   - **Usage**: `run_analysis.bat [SIMULATION...] [--compare] [--pos-dir-base DIR]`

3. **`run_analysis_auto.sh`** (Bash, auto mode):
   - Automatically overwrites existing files without prompts
   - Supports multi-simulation analysis with `--compare` option
   - Runs comparative analysis after processing all simulations
   - Useful for automated runs and CI/CD pipelines
   - **Usage**: `./run_analysis_auto.sh [SIMULATION...] [--compare] [--pos-dir-base DIR]`

All runners validate Python and package dependencies before starting and support:
- **Multiple simulations**: Analyze several datasets in sequence
- **Comparison mode**: Generate comparative analysis with `--compare` flag
- **Flexible data organization**: Use `--pos-dir-base` for simulation subdirectories

## Data Requirements

### Data Organization Options

**Option 1: Single simulation in `pos/` directory:**
- Daily position files: `ePos_TWOFISH_YYYYMMDD_EOD.csv`
- Industry mapping: `Industry.csv` (in `pos/`, current directory, or parent directory)

**Option 2: Multiple simulations in separate directories:**
- Base directory with simulation subdirectories (e.g., `bye/pos/`, `byd/pos/`)
- Each subdirectory contains: `ePos_TWOFISH_YYYYMMDD_EOD.csv` files
- Industry mapping: `Industry.csv` (searched in multiple locations)

**Option 3: Multiple simulations with different prefixes:**
- All files in `pos/` directory with different prefixes: `ePos_{SIMULATION}_YYYYMMDD_EOD.csv`
- Industry mapping: `Industry.csv` in `pos/` directory

**Note**: The `pos/` directory, simulation subdirectories, and generated data files are excluded from git via `.gitignore`.

## Outputs

### Per Simulation Outputs
- `outputs/{SIMULATION}/combined_positions_with_industry.csv`: Combined dataset with sector and bizsector columns
- `outputs/{SIMULATION}/pnl_plots/`: Sector-level visualization images (PNG)
- `outputs/{SIMULATION}/bizsector_plots/`: Bizsector-level visualization images (PNG)
- `outputs/{SIMULATION}/pnl_results/`: Intermediate analysis results (CSV) including sector and bizsector metrics
- `outputs/{SIMULATION}/{SIMULATION}_analysis_report.{md,html}`: Comprehensive reports with sector and bizsector insights

### Comparison Outputs (when using `--compare`)
- `outputs/comparison/`: Comparative analysis directory
- `outputs/comparison/comparison_plots/`: Comparative visualizations including sector and bizsector comparisons
- `outputs/comparison/comparison_data/`: Comparison metrics and data including sector and bizsector JSON files
- `outputs/comparison/comparison_report.{md,html}`: Comprehensive comparison report with sector and bizsector analysis

### Example Output Structure
```
outputs/
├── TWOFISH/
│   ├── combined_positions_with_industry.csv
│   ├── pnl_results/           # Contains sector_*.csv and bizsector_*.csv files
│   ├── pnl_plots/             # Sector-level visualizations
│   ├── bizsector_plots/       # Bizsector-level visualizations
│   └── TWOFISH_analysis_report.{md,html}
├── BLOWFISH/
│   ├── combined_positions_with_industry.csv
│   ├── pnl_results/           # Contains sector_*.csv and bizsector_*.csv files
│   ├── pnl_plots/             # Sector-level visualizations
│   ├── bizsector_plots/       # Bizsector-level visualizations
│   └── BLOWFISH_analysis_report.{md,html}
└── comparison/
    ├── comparison_plots/      # Includes sector and bizsector comparison charts
    ├── comparison_data/       # Includes sector_*.json and bizsector_*.json files
    └── comparison_report.{md,html}
```

## License

This project is available for use and modification.