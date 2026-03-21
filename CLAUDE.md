# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a financial position analysis pipeline for processing daily stock position files from multiple simulations. The system reads EOD position CSVs for one or more simulations, merges them with industry sector mappings, calculates P&L by sector, generates visualizations and reports, and provides comparative analysis between simulations.

The analysis is implemented in a five-script pipeline supporting single-simulation analysis and multi-simulation comparison.

## Development Setup

**Python Environment:** Python 3.14.3 is used. Install required packages:
```bash
pip install pandas numpy matplotlib seaborn
```

**Data Dependencies:** Position files can be organized in multiple ways:

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

## Common Commands

### Single Simulation Analysis
**Run the full analysis pipeline for one simulation:**
```bash
# Analyze TWOFISH simulation (default)
python combine_data.py --simulation TWOFISH --pos-dir pos
python pnl_analysis.py --simulation TWOFISH --output-dir outputs
python generate_report.py --simulation TWOFISH --output-dir outputs

# Or use runner scripts:
./run_analysis.sh TWOFISH                    # Interactive prompts
./run_analysis_auto.sh TWOFISH               # Auto mode (overwrites files)
run_analysis.bat TWOFISH                     # Windows CMD
```

### Multiple Simulation Analysis with Comparison
**Analyze multiple simulations and compare results:**
```bash
# Analyze two simulations and compare
./run_analysis_auto.sh bye byd --compare

# Analyze with simulation subdirectories
./run_analysis_auto.sh bye byd --pos-dir-base . --compare

# Run comparison on existing results
python compare_simulations.py bye byd --output-base-dir outputs
python generate_comparison_report.py --comparison-dir outputs/comparison
```

**Install dependencies (if missing):**
```bash
pip install pandas numpy matplotlib seaborn
```

**Check combined data for a simulation:**
```bash
python -c "import pandas as pd; df = pd.read_csv('outputs/TWOFISH/combined_positions_with_industry.csv'); print(df.shape)"
```

**Regenerate visualizations for a simulation:**
```bash
python pnl_analysis.py --simulation TWOFISH --output-dir outputs
```

## Architecture

### Five-Stage Pipeline (Single or Multi-Simulation)
1. **Data Combination** (`combine_data.py`):
   - Reads all `ePos_{SIMULATION}_*.csv` files from specified directory
   - Extracts dates from filenames (YYYYMMDD format)
   - Loads `Industry.csv` (searches multiple locations)
   - Maps first two digits of industry codes to sector names
   - Merges position data with industry mapping
   - Output: `outputs/{SIMULATION}/combined_positions_with_industry.csv`

2. **P&L Analysis** (`pnl_analysis.py`):
   - Loads combined data for a specific simulation
   - Calculates daily P&L aggregated by sector
   - Computes cumulative P&L, rolling metrics, exposure
   - Generates visualizations in `outputs/{SIMULATION}/pnl_plots/`
   - Saves intermediate results to `outputs/{SIMULATION}/pnl_results/`

3. **Report Generation** (`generate_report.py`):
   - Loads analysis results for a specific simulation
   - Calculates additional metrics (top symbols, drawdown, win rates)
   - Generates markdown and HTML reports
   - Output: `outputs/{SIMULATION}/{SIMULATION}_analysis_report.{md,html}`

4. **Simulation Comparison** (`compare_simulations.py`):
   - Loads results from multiple simulation directories
   - Calculates comparative metrics: total P&L difference, sector performance deltas
   - Computes risk metrics (volatility, Sharpe ratio, max drawdown)
   - Analyzes correlation between simulation returns
   - Generates comparative visualizations in `outputs/comparison/comparison_plots/`
   - Saves comparison data to `outputs/comparison/`

5. **Comparison Reporting** (`generate_comparison_report.py`):
   - Loads comparison results
   - Generates comprehensive comparison report with insights
   - Creates markdown and HTML comparison reports
   - Output: `outputs/comparison/comparison_report.{md,html}`

### Data Flow (Multi-Simulation)
```
simulation1/pos/ePos_TWOFISH_*.csv + Industry.csv
    │
simulation2/pos/ePos_TWOFISH_*.csv + Industry.csv
    │
    ├── combine_data.py (per simulation) → outputs/{SIMULATION}/combined_positions_with_industry.csv
    │
    ├── pnl_analysis.py (per simulation) → outputs/{SIMULATION}/pnl_results/ + pnl_plots/
    │
    ├── generate_report.py (per simulation) → outputs/{SIMULATION}/{SIMULATION}_analysis_report.{md,html}
    │
    ├── compare_simulations.py → outputs/comparison/ (metrics + visualizations)
    │
    └── generate_comparison_report.py → outputs/comparison/comparison_report.{md,html}
```

### Key Directories
- **Input Directories:**
  - `pos/` or `{simulation}/pos/`: Input position files
  - Industry mapping can be in: `pos/Industry.csv`, `./Industry.csv`, or `../Industry.csv`

- **Output Directories (per simulation):**
  - `outputs/{SIMULATION}/`: Simulation-specific outputs
  - `outputs/{SIMULATION}/pnl_plots/`: Visualization images (PNG)
  - `outputs/{SIMULATION}/pnl_results/`: Intermediate analysis results (CSV)

- **Comparison Directories:**
  - `outputs/comparison/`: Comparative analysis results
  - `outputs/comparison/comparison_plots/`: Comparative visualizations
  - `outputs/comparison/comparison_data/`: Comparison metrics and data

## Data Structure

### Position Files
- **Filename pattern:** `ePos_{SIMULATION}_YYYYMMDD_EOD.csv` (e.g., `ePos_TWOFISH_20250321_EOD.csv`)
- **Multiple simulation support:**
  - Files can have different simulation prefixes (e.g., `ePos_TWOFISH_*.csv`, `ePos_BLOWFISH_*.csv`)
  - Files can be in simulation subdirectories (e.g., `bye/pos/ePos_TWOFISH_*.csv`)
  - Fallback logic: if simulation-named files not found, tries `TWOFISH` prefix
- **Key columns:**
  - `RSymbol`: Stock symbol (e.g., 'AAPL.O', 'DXCM.O')
  - `Quantity`: Position quantity (negative for short)
  - `Mark`: Current market price
  - `CMark`: Cost basis price
  - `pl`: Unrealized P&L calculated as `(Mark - CMark) * Quantity`
  - `bought`/`sold`: Trades executed on the date
  - `sbproceeds`/`ssproceeds`: Stock buy/sell trade proceeds

### Industry Mapping (`Industry.csv`)
- `symbol`: Stock symbol
- `origIndustry`/`newIndustry`: 10-digit industry codes
- **Sector mapping** (first two digits):
  - `50`: Energy, `51`: Materials, `52`: Industrials
  - `53`: Consumer Discretionary, `54`: Consumer Staples
  - `55`: Financials, `56`: Health Care  # Note: 55=Financials, 56=Health Care (corrected)
  - `57`: Information Technology, `58`: Communication Services
  - `59`: Utilities, `60`: Real Estate
  - Unmapped codes default to 'Other'

### Combined Data Schema
The merged dataset includes all position columns plus:
- `date`: Extracted from filename (datetime)
- `filename`: Source filename
- `symbol`, `origIndustry`, `newIndustry`: From industry mapping
- `sector_code`: First two digits of `newIndustry`
- `sector`: Mapped sector name (based on corrected mapping)

## Key Implementation Details

### P&L Calculation
- **Unrealized P&L:** Uses `pl` column from source data (`(Mark - CMark) * Quantity`)
- **Sector aggregation:** Group by `date` and `sector`, sum `pl`
- **Exposure:** `Mark * Quantity` (absolute value for percentage calculations)
- **Cumulative P&L:** `cumsum()` within each sector

### Visualization Types
1. **Weekly P&L Heatmap:** Sector performance over time (resampled weekly)
2. **Cumulative P&L by Sector:** Line chart showing growth
3. **Total P&L by Sector:** Bar chart of aggregated performance
4. **Daily Total P&L:** Timeline with positive/negative fill
5. **Sector Exposure Over Time:** Log-scale line chart

### Report Insights
- Top/bottom 10 symbols by P&L
- Sector win rates (days with positive P&L)
- Maximum drawdown analysis
- Monthly performance breakdown
- Latest exposure concentration

### Comparison Metrics (Multi-Simulation)
- **Total P&L Comparison:** Absolute and percentage differences between simulations
- **Sector Performance Deltas:** Sector-by-sector performance differences
- **Risk Metrics Comparison:** Volatility, Sharpe ratio, max drawdown, win rates
- **Correlation Analysis:** Daily return correlations between simulation pairs
- **Statistical Significance:** Performance difference significance testing
- **Visual Comparisons:** Side-by-side bar charts, overlay line charts, heatmaps, scatter plots

### Command-Line Interface
All scripts support command-line arguments for flexible execution:

**`combine_data.py`:**
- `--simulation, -s`: Simulation name (default: TWOFISH)
- `--pos-dir, -p`: Directory containing position files (default: pos)
- `--output-dir, -o`: Base output directory (default: outputs)
- `--industry-file`: Path to industry mapping CSV

**`pnl_analysis.py`:**
- `--simulation, -s`: Simulation name (default: TWOFISH)
- `--input-file`: Path to combined data file (default: outputs/{SIMULATION}/combined_positions_with_industry.csv)
- `--output-dir, -o`: Base output directory (default: outputs)

**`generate_report.py`:**
- `--simulation, -s`: Simulation name (default: TWOFISH)
- `--output-dir, -o`: Base output directory (default: outputs)

**`compare_simulations.py`:**
- Positional arguments: Simulation names (e.g., `bye byd`)
- `--output-base-dir`: Base output directory (default: outputs)
- `--comparison-dir`: Comparison output directory (default: outputs/comparison)

**`generate_comparison_report.py`:**
- `--comparison-dir, -c`: Directory containing comparison results (default: outputs/comparison)
- `--output-dir, -o`: Directory to save reports (default: outputs/comparison)

**Runner Scripts:**
- `--compare`: Run comparison after analyzing all simulations
- `--pos-dir-base`: Base directory with simulation subdirectories
- `--pos-dir`: Directory containing position files
- `--output-dir`: Base output directory

