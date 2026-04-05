# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a financial position analysis pipeline for processing daily stock position files from multiple simulations. The system reads EOD position CSVs for one or more simulations, merges them with industry sector mappings, calculates P&L by sector and bizsector (4-digit industry group), generates visualizations and reports, and provides comparative analysis between simulations at both sector and bizsector levels.

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

# Analyze three simulations and compare  
./run_analysis_auto.sh bye byd byeorig --compare

# Analyze with simulation subdirectories
./run_analysis_auto.sh bye byd --pos-dir-base . --compare

# Run comparison on existing results
python compare_simulations.py bye byd --output-base-dir outputs
# Compare three simulations: python compare_simulations.py bye byd byeorig --output-base-dir outputs
python generate_comparison_report.py --comparison-dir outputs/comparison

# Check sector Sharpe ratio comparison
python -c "
import json;
with open('outputs/comparison/sector_sharpe_comparison.json') as f:
    data = json.load(f);
for sector, sims in data.items():
    print(f'{sector:30} {str(sims)}')
"
```

### Yearly Comparison Reports
**Generate comparison reports for specific years:** Year appears in visualization titles for yearly comparison reports.
```bash
# Compare simulations for a specific year
python compare_simulations.py bye byeorig --year 2022
python generate_comparison_report.py --comparison-dir outputs/comparison_2022 --output-dir outputs/comparison_2022

# Generate separate comparison reports for all years
python compare_simulations.py bye byeorig --all-years
for year in 2022 2023 2024 2025 2026; do
    python generate_comparison_report.py --comparison-dir outputs/comparison_$year --output-dir outputs/comparison_$year
done

# Check yearly sector Sharpe ratio comparison for 2022
python -c "
import json;
with open('outputs/comparison_2022/sector_sharpe_comparison.json') as f:
    data = json.load(f);
print('Year 2022 Sector Sharpe Ratios:')
for sector, sims in data.items():
    print(f'{sector:30} {str(sims)}')
"
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

**Check sector Sharpe ratios for a simulation:**
```bash
python -c "
import pandas as pd;
df = pd.read_csv('outputs/TWOFISH/pnl_results/sector_summary.csv');
print(df[['sector', 'total_pnl', 'sharpe_ratio']].sort_values('sharpe_ratio', ascending=False))
"
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
   - **Calculates annualized Sharpe ratios per sector** (risk-free rate = 0, √252 annualization)
   - Generates visualizations in `outputs/{SIMULATION}/pnl_plots/`
   - Saves intermediate results to `outputs/{SIMULATION}/pnl_results/`

3. **Report Generation** (`generate_report.py`):
   - Loads analysis results for a specific simulation
   - Calculates additional metrics (top symbols, drawdown, win rates)
   - Generates markdown and HTML reports
   - Output: `outputs/{SIMULATION}/{SIMULATION}_analysis_report.{md,html}`

4. **Simulation Comparison** (`compare_simulations.py`):
   - Loads results from multiple simulation directories
   - **Supports yearly filtering** (`--year`, `--all-years`) for period-specific comparisons
   - Calculates comparative metrics: total P&L difference, sector performance deltas
   - Computes risk metrics (volatility, Sharpe ratio, max drawdown)
   - Analyzes correlation between simulation returns
   - Generates comparative visualizations in `outputs/comparison/comparison_plots/` (or `comparison_{YEAR}/`)
   - Saves comparison data to `outputs/comparison/` (or `outputs/comparison_{YEAR}/`)

5. **Comparison Reporting** (`generate_comparison_report.py`):
   - Loads comparison results including sector Sharpe ratio comparisons
   - Generates comprehensive comparison report with insights
   - Creates markdown and HTML comparison reports
   - **Includes sector Sharpe ratio analysis and rankings**
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
  - `outputs/comparison/comparison_plots/`: Comparative visualizations (including `sector_sharpe_comparison.png`)
  - `outputs/comparison/comparison_data/`: Comparison metrics and data (CSV and JSON files)

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
- **Bizsector mapping** (first four digits, industry groups):
  - Examples: `5310`: "Automobiles & Components", `5320`: "Consumer Durables & Apparel"
  - `5330`: "Consumer Services", `5340`: "Retailing"
  - `5410`: "Food, Beverage & Tobacco", `5420`: "Household & Personal Products"
  - `5430`: "Food & Staples Retailing", `5440`: "Industrial Conglomerates"
  - `5010`: "Oil, Gas & Consumable Fuels", `5020`: "Renewable Energy"
  - `5510`: "Financial Services", `5530`: "Insurance"
  - `5550`: "Private Equity", `5610`: "Health Care Equipment & Services"
  - `5620`: "Pharmaceuticals & Biotechnology", `5210`: "Capital Goods"
  - `5220`: "Commercial & Professional Services", `5240`: "Transportation"
  - `5710`: "Technology Hardware & Equipment", `5720`: "Software & Services"
  - `5730`: "Financial Technology", `5740`: "Telecommunications"
  - `5110`: "Chemicals", `5120`: "Construction Materials"
  - `5130`: "Containers & Packaging", `6010`: "Real Estate Investment Trusts (REITs)"
  - `5910`: "Electric Utilities"
  - Unmapped bizsector codes default to 'Other'

### Combined Data Schema
The merged dataset includes all position columns plus:
- `date`: Extracted from filename (datetime)
- `filename`: Source filename
- `symbol`, `origIndustry`, `newIndustry`: From industry mapping
- `sector_code`: First two digits of `newIndustry`
- `sector`: Mapped sector name (based on corrected mapping)
- `bizsector_code`: First four digits of `newIndustry`
- `bizsector`: Mapped bizsector name (industry group)

### Comparison Data Files
- **`sector_sharpe_comparison.json`**: Sector-level Sharpe ratio comparisons across simulations
  - Format: `{sector: {simulation1: sharpe_ratio, simulation2: sharpe_ratio, ...}}`
  - Used for risk-adjusted performance analysis across sectors
- **`sector_comparison.json`**: Sector-level total P&L comparisons across simulations
- **`bizsector_sharpe_comparison.json`**: Bizsector-level Sharpe ratio comparisons across simulations
  - Format: `{bizsector: {simulation1: sharpe_ratio, simulation2: sharpe_ratio, ...}}`
  - Used for risk-adjusted performance analysis across industry groups
- **`bizsector_comparison.json`**: Bizsector-level total P&L comparisons across simulations
- **`total_pnl_comparison.csv`**: Total P&L comparison across simulations
- **`risk_metrics_comparison.csv`**: Risk metrics comparison (volatility, Sharpe ratio, max drawdown, win rate)
- **`correlations.csv`**: Correlation matrix between simulation returns

## Key Implementation Details

### P&L Calculation
- **Unrealized P&L:** Uses `pl` column from source data (`(Mark - CMark) * Quantity`)
- **Sector aggregation:** Group by `date` and `sector`, sum `pl`
- **Bizsector aggregation:** Group by `date` and `bizsector`, sum `pl`
- **Exposure:** `Mark * Quantity` (absolute value for percentage calculations)
- **Cumulative P&L:** `cumsum()` within each sector and bizsector

### Sharpe Ratio Calculation
- **Annualized Sharpe:** `mean_return / std_return * √252` (assuming risk-free rate = 0)
- **Sector-level:** Calculated per sector using daily P&L returns
- **Bizsector-level:** Calculated per bizsector using daily P&L returns
- **Edge cases:** Handles single data point (Sharpe = 0) and zero standard deviation (Sharpe = 0)
- **Comparison:** Sector and bizsector Sharpe ratios compared across simulations in comparative analysis

### Visualization Types
1. **Weekly P&L Heatmap:** Sector performance over time (resampled weekly)
2. **Cumulative P&L by Sector:** Line chart showing growth
3. **Total P&L by Sector:** Bar chart of aggregated performance
4. **Daily Total P&L:** Timeline with positive/negative fill
5. **Sector Exposure Over Time:** Log-scale line chart
6. **Bizsector Visualizations:** Parallel set of visualizations for bizsector-level analysis (bizsector_plots directory)

### Report Insights
- Top/bottom 10 symbols by P&L
- Sector win rates (days with positive P&L)
- **Sector Sharpe ratios** (annualized risk-adjusted performance)
- Bizsector win rates and Sharpe ratios
- Maximum drawdown analysis
- Monthly performance breakdown
- Latest exposure concentration (sector and bizsector)

### Comparison Metrics (Multi-Simulation)
- **Total P&L Comparison:** Absolute and percentage differences between simulations
- **Sector Performance Deltas:** Sector-by-sector performance differences
- **Sector Sharpe Ratio Comparison:** Risk-adjusted performance comparison across sectors
- **Bizsector Performance Deltas:** Bizsector-by-bizsector performance differences
- **Bizsector Sharpe Ratio Comparison:** Risk-adjusted performance comparison across industry groups
- **Risk Metrics Comparison:** Volatility, Sharpe ratio, max drawdown, win rates
- **Correlation Analysis:** Daily return correlations between simulation pairs
- **Statistical Significance:** Performance difference significance testing
- **Visual Comparisons:** Side-by-side bar charts, overlay line charts, heatmaps, scatter plots, sector and bizsector Sharpe ratio charts

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
- Positional arguments: Simulation names, space-separated or comma-separated (e.g., `bye byd` or `bye,byd`)
- `--output-base-dir`: Base output directory (default: outputs)
- `--comparison-dir`: Comparison output directory (default: outputs/comparison)
- `--year, -y`: Filter data to specific year (e.g., 2022). If not provided, uses all years
- `--all-years`: Generate separate comparison reports for each year present in data

**`generate_comparison_report.py`:**
- `--comparison-dir, -c`: Directory containing comparison results (default: outputs/comparison)
- `--output-dir, -o`: Directory to save reports (default: outputs/comparison)

**Runner Scripts:**
- `SIMULATION...`: One or more simulation names, comma-separated or space-separated (default: TWOFISH)
- `--compare`: Run comparison after analyzing all simulations
- `--year YEAR`: Filter comparison to specific year (e.g., 2022) (requires `--compare`)
- `--all-years`: Generate separate comparison reports for each year (requires `--compare`)
- `--pos-dir-base`: Base directory with simulation subdirectories
- `--pos-dir`: Directory containing position files
- `--output-dir`: Base output directory

## Case Study: Three‑Simulation Comparative Analysis

A comprehensive analysis of three simulations (`byd`, `byeorig`, `bye`) demonstrates the pipeline's capability to evaluate different trading strategies.

### Performance Rankings (All Years Combined)

| Metric | 1st | 2nd | 3rd |
|--------|-----|-----|-----|
| **Total P&L** | byeorig ($13.34M) | bye ($12.87M) | byd ($9.91M) |
| **Sharpe Ratio** | bye (0.124) | byeorig (0.116) | byd (0.088) |
| **Volatility** | bye (97,395) | byd (105,432) | byeorig (107,567) |
| **Win Rate** | bye (54.22%) | byd (53.66%) | byeorig (53.28%) |
| **Max Drawdown** | byd ($2.20M) | bye ($2.30M) | byeorig ($2.43M) |

### Strategy Type Inference

| Simulation | Likely Strategy | Characteristics |
|------------|----------------|-----------------|
| **bye** | Balanced Risk‑Managed | Highest Sharpe, lowest volatility, best consistency |
| **byeorig** | High‑Return Aggressive | Maximum absolute returns, higher volatility |
| **byd** | Conservative Capital‑Preservation | Best drawdown control, utility‑focused |

### Year‑by‑Year Patterns
- **2022**: `byeorig` dominance (aggressive strategy worked)
- **2023‑2024**: `byd` outperforms (conservative strategy excels)  
- **2025‑2026**: `bye` leads (balanced strategy adapts best)

### Recommendations
- **For risk‑adjusted returns**: `bye` (highest Sharpe ratio, lowest volatility)
- **For absolute returns**: `byeorig` (highest total P&L)
- **For capital preservation**: `byd` (smallest maximum drawdown)
- **Overall balanced choice**: `bye` (best composite score across metrics)

### Sector‑Level Insights
- All simulations excel in **Utilities** and **Information Technology**
- `bye` leads in 5 sectors (broadest strength)
- `byd` strongest in Utilities (1.026 Sharpe)
- `byeorig` strongest in Information Technology (1.247 Sharpe)

This analysis demonstrates how the pipeline can identify strategy characteristics, assess performance across different market regimes, and provide actionable recommendations for strategy selection.

