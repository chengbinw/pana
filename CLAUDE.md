# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a financial position analysis pipeline for processing daily stock position files. The system reads EOD position CSVs, merges them with industry sector mappings, calculates P&L by sector, and generates visualizations and reports.

The analysis is implemented in three Python scripts that form a sequential pipeline.

## Development Setup

**Python Environment:** Python 3.14.3 is used. Install required packages:
```bash
pip install pandas numpy matplotlib seaborn
```

**Data Dependencies:** The `pos/` directory must contain:
- Daily position files: `ePos_TWOFISH_YYYYMMDD_EOD.csv`
- Industry mapping: `Industry.csv`

## Common Commands

**Run the full analysis pipeline:**
```bash
python combine_data.py        # Step 1: Combine daily files with industry data
python pnl_analysis.py        # Step 2: Calculate P&L by sector, generate visualizations
python generate_report.py     # Step 3: Create comprehensive reports
```

**Install dependencies (if missing):**
```bash
pip install pandas numpy matplotlib seaborn
```

**Check combined data:**
```bash
python -c "import pandas as pd; df = pd.read_csv('combined_positions_with_industry.csv'); print(df.shape)"
```

**Regenerate visualizations only** (after combined data exists):
```bash
python pnl_analysis.py
```

## Architecture

### Three-Stage Pipeline
1. **Data Combination** (`combine_data.py`):
   - Reads all `ePos_TWOFISH_*.csv` files from `pos/`
   - Extracts dates from filenames (YYYYMMDD format)
   - Loads `Industry.csv` and maps first two digits to sector names
   - Merges position data with industry mapping
   - Output: `combined_positions_with_industry.csv`

2. **P&L Analysis** (`pnl_analysis.py`):
   - Loads combined data
   - Calculates daily P&L aggregated by sector
   - Computes cumulative P&L, rolling metrics, exposure
   - Generates visualizations in `pnl_plots/`
   - Saves intermediate results to `pnl_results/`

3. **Report Generation** (`generate_report.py`):
   - Loads analysis results
   - Calculates additional metrics (top symbols, drawdown, win rates)
   - Generates markdown and HTML reports
   - Output: `position_analysis_report.md` and `.html`

### Data Flow
```
pos/*.csv + Industry.csv
    │
    ├── combine_data.py → combined_positions_with_industry.csv
    │
    ├── pnl_analysis.py → pnl_results/ + pnl_plots/
    │
    └── generate_report.py → position_analysis_report.{md,html}
```

### Key Directories
- `pos/`: Input position files and industry mapping
- `pnl_plots/`: Generated visualization images (PNG)
- `pnl_results/`: Intermediate analysis results (CSV)

## Data Structure

### Position Files
- **Filename pattern:** `ePos_TWOFISH_YYYYMMDD_EOD.csv`
- **Key columns:**
  - `RSymbol`: Stock symbol (e.g., 'AAPL.O')
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
  - `55`: Health Care, `56`: Financials
  - `57`: Information Technology, `58`: Communication Services
  - `59`: Utilities, `60`: Real Estate

### Combined Data Schema
The merged dataset includes all position columns plus:
- `date`: Extracted from filename
- `filename`: Source filename
- `symbol`, `origIndustry`, `newIndustry`: From industry mapping
- `sector_code`: First two digits of `newIndustry`
- `sector`: Mapped sector name

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

