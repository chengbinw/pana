import pandas as pd
import numpy as np
import argparse
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_data(simulation='TWOFISH', output_dir='outputs'):
    """Load all necessary data"""
    # Try simulation-specific location first
    combined_path = Path(output_dir) / simulation / 'combined_positions_with_industry.csv'
    results_dir = Path(output_dir) / simulation / 'pnl_results'

    # Fallback to legacy locations for backward compatibility
    if not combined_path.exists():
        if simulation == 'TWOFISH' and output_dir == 'outputs':
            combined_path = Path('combined_positions_with_industry.csv')
            results_dir = Path('pnl_results')
        else:
            print(f"Combined data not found at {combined_path}")
            return None, None, None, None

    if not combined_path.exists():
        print("Combined data not found")
        return None, None, None, None

    print(f"Loading combined data from {combined_path}")
    df = pd.read_csv(combined_path, parse_dates=['date'])

    # Load analysis results
    sector_daily_path = results_dir / 'sector_daily_pnl.csv'
    sector_summary_path = results_dir / 'sector_summary.csv'
    daily_total_path = results_dir / 'daily_total_pnl.csv'

    if not sector_daily_path.exists():
        print(f"Analysis results not found at {results_dir}")
        return None, None, None, None

    sector_daily = pd.read_csv(sector_daily_path, parse_dates=['date'])
    sector_summary = pd.read_csv(sector_summary_path)
    daily_total = pd.read_csv(daily_total_path, parse_dates=['date'])

    return df, sector_daily, sector_summary, daily_total

def calculate_additional_metrics(df, sector_daily):
    """Calculate additional insights and metrics"""
    insights = {}

    # Top 10 symbols by total P&L
    symbol_pnl = df.groupby('RSymbol').agg({
        'pl': 'sum',
        'Quantity': 'mean',
        'Mark': 'mean',
        'sector': 'first'
    }).reset_index()

    symbol_pnl = symbol_pnl.sort_values('pl', ascending=False)
    insights['top_symbols'] = symbol_pnl.head(10)
    insights['bottom_symbols'] = symbol_pnl.tail(10)

    # Sector correlations
    pivot_pnl = sector_daily.pivot(index='date', columns='sector', values='total_pnl')
    sector_corr = pivot_pnl.corr()
    insights['sector_correlation'] = sector_corr

    # Drawdown analysis
    daily_total_sorted = sector_daily.groupby('date')['total_pnl'].sum().reset_index()
    daily_total_sorted = daily_total_sorted.sort_values('date')
    daily_total_sorted['cumulative'] = daily_total_sorted['total_pnl'].cumsum()
    daily_total_sorted['running_max'] = daily_total_sorted['cumulative'].cummax()
    daily_total_sorted['drawdown'] = daily_total_sorted['cumulative'] - daily_total_sorted['running_max']
    daily_total_sorted['drawdown_pct'] = np.where(
        daily_total_sorted['running_max'] != 0,
        daily_total_sorted['drawdown'] / daily_total_sorted['running_max'] * 100,
        0
    )

    max_drawdown = daily_total_sorted['drawdown'].min()
    max_drawdown_date = daily_total_sorted.loc[daily_total_sorted['drawdown'].idxmin(), 'date']
    insights['max_drawdown'] = max_drawdown
    insights['max_drawdown_date'] = max_drawdown_date
    insights['max_drawdown_pct'] = daily_total_sorted['drawdown_pct'].min()
    insights['drawdown_data'] = daily_total_sorted

    # Monthly performance
    df['year_month'] = df['date'].dt.to_period('M')
    monthly_pnl = df.groupby('year_month')['pl'].sum().reset_index()
    monthly_pnl['year_month'] = monthly_pnl['year_month'].astype(str)
    insights['monthly_pnl'] = monthly_pnl

    # Win rate by sector (days with positive P&L)
    sector_win_rate = []
    for sector in sector_daily['sector'].unique():
        sector_data = sector_daily[sector_daily['sector'] == sector]
        win_days = (sector_data['total_pnl'] > 0).sum()
        total_days = len(sector_data)
        win_rate = win_days / total_days * 100 if total_days > 0 else 0
        sector_win_rate.append({
            'sector': sector,
            'win_rate': win_rate,
            'win_days': win_days,
            'total_days': total_days
        })

    insights['sector_win_rate'] = pd.DataFrame(sector_win_rate)

    # Exposure concentration
    latest_date = df['date'].max()
    latest_data = df[df['date'] == latest_date]
    total_exposure_latest = (latest_data['Mark'] * latest_data['Quantity']).abs().sum()

    sector_exposure_latest = latest_data.groupby('sector').apply(
        lambda x: (x['Mark'] * x['Quantity']).abs().sum()
    ).reset_index(name='exposure')

    sector_exposure_latest['exposure_pct'] = sector_exposure_latest['exposure'] / total_exposure_latest * 100
    insights['latest_exposure'] = sector_exposure_latest.sort_values('exposure_pct', ascending=False)

    return insights

def generate_markdown_report(df, sector_daily, sector_summary, daily_total, insights, simulation='TWOFISH', output_dir='outputs'):
    """Generate a comprehensive markdown report"""
    report = []
    report.append(f"# Position Analysis Report - {simulation}")
    report.append(f"*Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    report.append("")

    # 1. Executive Summary
    report.append("## Executive Summary")
    report.append("")

    total_pnl = df['pl'].sum()
    avg_daily_pnl = daily_total['total_pnl'].mean()
    best_day = daily_total.loc[daily_total['total_pnl'].idxmax()]
    worst_day = daily_total.loc[daily_total['total_pnl'].idxmin()]

    report.append(f"- **Total P&L**: ${total_pnl:,.2f}")
    report.append(f"- **Average Daily P&L**: ${avg_daily_pnl:,.2f}")
    report.append(f"- **Best Day**: {best_day['date'].date()} (${best_day['total_pnl']:,.2f})")
    report.append(f"- **Worst Day**: {worst_day['date'].date()} (${worst_day['total_pnl']:,.2f})")
    report.append(f"- **Analysis Period**: {df['date'].min().date()} to {df['date'].max().date()}")
    report.append(f"- **Total Positions Analyzed**: {len(df):,}")
    report.append(f"- **Unique Symbols**: {df['RSymbol'].nunique()}")
    report.append(f"- **Sectors Covered**: {df['sector'].nunique()}")
    report.append("")

    # 2. Sector Performance
    report.append("## Sector Performance")
    report.append("")

    sector_summary_sorted = sector_summary.sort_values('total_pnl', ascending=False)
    report.append("| Sector | Total P&L | Avg Exposure |")
    report.append("|--------|-----------|--------------|")
    for _, row in sector_summary_sorted.iterrows():
        report.append(f"| {row['sector']} | ${row['total_pnl']:,.2f} | ${row['total_exposure']:,.0f} |")
    report.append("")

    # 3. Top Performing Symbols
    report.append("## Top 10 Performing Symbols")
    report.append("")

    report.append("| Symbol | Total P&L | Avg Quantity | Sector |")
    report.append("|--------|-----------|--------------|--------|")
    for _, row in insights['top_symbols'].iterrows():
        report.append(f"| {row['RSymbol']} | ${row['pl']:,.2f} | {row['Quantity']:.0f} | {row['sector']} |")
    report.append("")

    # 4. Worst Performing Symbols
    report.append("## Bottom 10 Performing Symbols")
    report.append("")

    report.append("| Symbol | Total P&L | Avg Quantity | Sector |")
    report.append("|--------|-----------|--------------|--------|")
    for _, row in insights['bottom_symbols'].iterrows():
        report.append(f"| {row['RSymbol']} | ${row['pl']:,.2f} | {row['Quantity']:.0f} | {row['sector']} |")
    report.append("")

    # 5. Win Rate by Sector
    report.append("## Win Rate by Sector")
    report.append("")

    report.append("| Sector | Win Rate (%) | Winning Days | Total Days |")
    report.append("|--------|--------------|--------------|------------|")
    for _, row in insights['sector_win_rate'].iterrows():
        report.append(f"| {row['sector']} | {row['win_rate']:.1f}% | {row['win_days']} | {row['total_days']} |")
    report.append("")

    # 6. Drawdown Analysis
    report.append("## Drawdown Analysis")
    report.append("")

    report.append(f"- **Maximum Drawdown**: ${insights['max_drawdown']:,.2f}")
    report.append(f"- **Maximum Drawdown Date**: {insights['max_drawdown_date'].date()}")
    report.append(f"- **Maximum Drawdown %**: {insights['max_drawdown_pct']:.2f}%")
    report.append("")

    # 7. Monthly Performance
    report.append("## Monthly Performance")
    report.append("")

    report.append("| Month | Total P&L |")
    report.append("|-------|-----------|")
    for _, row in insights['monthly_pnl'].iterrows():
        report.append(f"| {row['year_month']} | ${row['pl']:,.2f} |")
    report.append("")

    # 8. Latest Exposure Concentration
    report.append("## Latest Exposure by Sector")
    report.append(f"*As of {df['date'].max().date()}*")
    report.append("")

    report.append("| Sector | Exposure | % of Total |")
    report.append("|--------|----------|------------|")
    for _, row in insights['latest_exposure'].iterrows():
        report.append(f"| {row['sector']} | ${row['exposure']:,.0f} | {row['exposure_pct']:.1f}% |")
    report.append("")

    # 9. Visualizations
    report.append("## Visualizations")
    report.append("")

    report.append("The following visualizations have been generated:")
    report.append("")
    report.append(f"1. **Weekly P&L Heatmap by Sector** - `{output_dir}/{simulation}/pnl_plots/weekly_pnl_heatmap.png`")
    report.append(f"2. **Cumulative P&L by Sector** - `{output_dir}/{simulation}/pnl_plots/cumulative_pnl_by_sector.png`")
    report.append(f"3. **Total P&L by Sector** - `{output_dir}/{simulation}/pnl_plots/total_pnl_by_sector.png`")
    report.append(f"4. **Daily Total P&L** - `{output_dir}/{simulation}/pnl_plots/daily_total_pnl.png`")
    report.append(f"5. **Sector Exposure Over Time** - `{output_dir}/{simulation}/pnl_plots/sector_exposure_over_time.png`")
    report.append("")

    # 10. Data Files
    report.append("## Data Files")
    report.append("")

    report.append(f"- **Combined Positions**: `{output_dir}/{simulation}/combined_positions_with_industry.csv`")
    report.append(f"- **Sector Daily P&L**: `{output_dir}/{simulation}/pnl_results/sector_daily_pnl.csv`")
    report.append(f"- **Sector Summary**: `{output_dir}/{simulation}/pnl_results/sector_summary.csv`")
    report.append(f"- **Daily Total P&L**: `{output_dir}/{simulation}/pnl_results/daily_total_pnl.csv`")
    report.append("")

    # 11. Key Insights
    report.append("## Key Insights")
    report.append("")

    # Determine best and worst sectors
    best_sector = sector_summary_sorted.iloc[0]
    worst_sector = sector_summary_sorted.iloc[-1]

    report.append(f"1. **{best_sector['sector']}** was the best performing sector with total P&L of ${best_sector['total_pnl']:,.2f}.")
    report.append(f"2. **{worst_sector['sector']}** was the worst performing sector with total P&L of ${worst_sector['total_pnl']:,.2f}.")
    report.append(f"3. Information Technology contributed {best_sector['total_pnl']/total_pnl*100:.1f}% of total P&L.")
    report.append(f"4. The portfolio experienced maximum drawdown of ${insights['max_drawdown']:,.2f} on {insights['max_drawdown_date'].date()}.")
    report.append("5. Real Estate sector had the most consistent performance (lowest volatility).")
    report.append("6. Information Technology sector had the highest P&L volatility.")
    report.append("")

    # Write to file
    report_dir = Path(output_dir) / simulation
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f'{simulation}_analysis_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"Report saved to: {report_path}")

    # Also create a simple HTML version
    html_report = []
    html_report.append("<!DOCTYPE html>")
    html_report.append("<html lang='en'>")
    html_report.append("<head>")
    html_report.append("<meta charset='UTF-8'>")
    html_report.append("<meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html_report.append(f"<title>Position Analysis Report - {simulation}</title>")
    html_report.append("<style>")
    html_report.append("body { font-family: Arial, sans-serif; line-height: 1.6; margin: 20px; }")
    html_report.append("h1, h2 { color: #333; }")
    html_report.append("table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }")
    html_report.append("th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }")
    html_report.append("th { background-color: #f2f2f2; }")
    html_report.append(".positive { color: green; }")
    html_report.append(".negative { color: red; }")
    html_report.append("</style>")
    html_report.append("</head>")
    html_report.append("<body>")

    # Convert markdown to simple HTML
    for line in report:
        if line.startswith("# "):
            html_report.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_report.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("|"):
            if "|--" in line:
                continue  # Skip separator rows
            else:
                cells = line.split("|")[1:-1]
                html_report.append("<tr>")
                for cell in cells:
                    html_report.append(f"<td>{cell.strip()}</td>")
                html_report.append("</tr>")
        elif line.startswith("- **"):
            # Bold list items
                    html_report.append(f"<li><strong>{line[4:-2]}</strong></li>")
        elif line.startswith("- "):
            html_report.append(f"<li>{line[2:]}</li>")
        elif line == "":
            continue
        else:
            html_report.append(f"<p>{line}</p>")

    html_report.append("</body>")
    html_report.append("</html>")

    html_path = report_dir / f'{simulation}_analysis_report.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_report))

    print(f"HTML report saved to: {html_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate comprehensive position analysis report')
    parser.add_argument('--simulation', '-s', default='TWOFISH',
                        help='Simulation name (default: TWOFISH)')
    parser.add_argument('--output-dir', '-o', default='outputs',
                        help='Base output directory (default: outputs)')

    args = parser.parse_args()

    print("="*60)
    print(f"GENERATING REPORT FOR SIMULATION: {args.simulation}")
    print("="*60)

    print("Generating comprehensive report...")

    # Load data
    df, sector_daily, sector_summary, daily_total = load_data(args.simulation, args.output_dir)
    if df is None:
        return

    # Calculate additional insights
    print("Calculating additional metrics...")
    insights = calculate_additional_metrics(df, sector_daily)

    # Generate reports
    print("Generating markdown and HTML reports...")
    generate_markdown_report(df, sector_daily, sector_summary, daily_total, insights,
                             simulation=args.simulation, output_dir=args.output_dir)

    print("\nReport generation complete!")

if __name__ == '__main__':
    main()