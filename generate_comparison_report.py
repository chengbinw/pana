import pandas as pd
import numpy as np
import json
import argparse
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

def load_comparison_data(comparison_dir='outputs/comparison'):
    """Load all comparison results from directory"""
    comparison_dir = Path(comparison_dir)
    data = {}

    # Load total P&L comparison
    total_pnl_path = comparison_dir / 'total_pnl_comparison.csv'
    if total_pnl_path.exists():
        data['total_pnl'] = pd.read_csv(total_pnl_path)
    else:
        print(f"Warning: total_pnl_comparison.csv not found at {total_pnl_path}")
        data['total_pnl'] = None

    # Load risk metrics comparison
    risk_metrics_path = comparison_dir / 'risk_metrics_comparison.csv'
    if risk_metrics_path.exists():
        data['risk_metrics'] = pd.read_csv(risk_metrics_path)
    else:
        print(f"Warning: risk_metrics_comparison.csv not found at {risk_metrics_path}")
        data['risk_metrics'] = None

    # Load sector comparison (JSON)
    sector_comp_path = comparison_dir / 'sector_comparison.json'
    if sector_comp_path.exists():
        with open(sector_comp_path, 'r') as f:
            sector_data = json.load(f)
        # Convert to DataFrame for easier manipulation
        sector_rows = []
        for sector, sim_values in sector_data.items():
            row = {'sector': sector}
            row.update(sim_values)
            sector_rows.append(row)
        data['sector_comparison'] = pd.DataFrame(sector_rows)
    else:
        print(f"Warning: sector_comparison.json not found at {sector_comp_path}")
        data['sector_comparison'] = None

    # Load sector Sharpe comparison (JSON)
    sector_sharpe_path = comparison_dir / 'sector_sharpe_comparison.json'
    if sector_sharpe_path.exists():
        with open(sector_sharpe_path, 'r') as f:
            sector_sharpe_data = json.load(f)
        # Convert to DataFrame for easier manipulation
        sector_sharpe_rows = []
        for sector, sim_values in sector_sharpe_data.items():
            row = {'sector': sector}
            row.update(sim_values)
            sector_sharpe_rows.append(row)
        data['sector_sharpe_comparison'] = pd.DataFrame(sector_sharpe_rows)
    else:
        print(f"Warning: sector_sharpe_comparison.json not found at {sector_sharpe_path}")
        data['sector_sharpe_comparison'] = None

    # Load correlations
    correlations_path = comparison_dir / 'correlations.csv'
    if correlations_path.exists():
        data['correlations'] = pd.read_csv(correlations_path, header=None, names=['pair', 'correlation'])
        # Ensure correlation column is numeric
        data['correlations']['correlation'] = pd.to_numeric(data['correlations']['correlation'], errors='coerce')
    else:
        print(f"Warning: correlations.csv not found at {correlations_path}")
        data['correlations'] = None

    # Load comparison metrics
    comp_metrics_path = comparison_dir / 'comparison_metrics.csv'
    if comp_metrics_path.exists():
        data['comparison_metrics'] = pd.read_csv(comp_metrics_path, header=None, names=['metric', 'value'])
    else:
        print(f"Warning: comparison_metrics.csv not found at {comp_metrics_path}")
        data['comparison_metrics'] = None

    # List visualization files
    viz_files = list(comparison_dir.glob('*.png'))
    data['visualizations'] = [f.name for f in viz_files]

    return data

def generate_comparison_insights(data):
    """Generate insights from comparison data"""
    insights = {}

    # Total P&L insights
    if data['total_pnl'] is not None and not data['total_pnl'].empty:
        total_pnl_df = data['total_pnl']
        insights['total_pnl'] = {
            'best_simulation': total_pnl_df.loc[total_pnl_df['total_pnl'].idxmax(), 'simulation'],
            'best_value': total_pnl_df['total_pnl'].max(),
            'worst_simulation': total_pnl_df.loc[total_pnl_df['total_pnl'].idxmin(), 'simulation'],
            'worst_value': total_pnl_df['total_pnl'].min(),
            'range': total_pnl_df['total_pnl'].max() - total_pnl_df['total_pnl'].min(),
            'avg': total_pnl_df['total_pnl'].mean()
        }

        # Calculate percentage differences
        if len(total_pnl_df) >= 2:
            sims = total_pnl_df['simulation'].tolist()
            values = total_pnl_df['total_pnl'].tolist()
            insights['total_pnl']['comparisons'] = []
            for i in range(len(sims)):
                for j in range(i+1, len(sims)):
                    diff = values[j] - values[i]
                    pct_diff = (diff / abs(values[i])) * 100 if values[i] != 0 else np.nan
                    insights['total_pnl']['comparisons'].append({
                        'pair': f'{sims[j]} vs {sims[i]}',
                        'difference': diff,
                        'percentage': pct_diff
                    })

    # Risk metrics insights
    if data['risk_metrics'] is not None and not data['risk_metrics'].empty:
        risk_df = data['risk_metrics']
        insights['risk_metrics'] = {}

        for metric in ['volatility', 'avg_daily_return', 'sharpe_ratio', 'max_drawdown', 'win_rate']:
            if metric in risk_df.columns:
                best_idx = risk_df[metric].idxmax() if metric != 'max_drawdown' else risk_df[metric].idxmin()
                worst_idx = risk_df[metric].idxmin() if metric != 'max_drawdown' else risk_df[metric].idxmax()
                insights['risk_metrics'][metric] = {
                    'best_simulation': risk_df.loc[best_idx, 'simulation'],
                    'best_value': risk_df.loc[best_idx, metric],
                    'worst_simulation': risk_df.loc[worst_idx, 'simulation'],
                    'worst_value': risk_df.loc[worst_idx, metric]
                }

    # Sector comparison insights
    if data['sector_comparison'] is not None and not data['sector_comparison'].empty:
        sector_df = data['sector_comparison']
        # Identify simulation columns (exclude 'sector' column)
        sim_cols = [col for col in sector_df.columns if col != 'sector']

        if len(sim_cols) >= 2:
            insights['sector'] = {}
            # Find sectors with largest differences
            for sector in sector_df['sector']:
                row = sector_df[sector_df['sector'] == sector].iloc[0]
                values = [row[col] for col in sim_cols]
                max_val = max(values)
                min_val = min(values)
                max_sim = sim_cols[values.index(max_val)]
                min_sim = sim_cols[values.index(min_val)]
                diff = max_val - min_val

                if diff != 0:  # Only record meaningful differences
                    insights['sector'][sector] = {
                        'largest_difference': diff,
                        'best_simulation': max_sim,
                        'best_value': max_val,
                        'worst_simulation': min_sim,
                        'worst_value': min_val
                    }

    # Correlation insights
    if data['correlations'] is not None and not data['correlations'].empty:
        corr_df = data['correlations']
        # Ensure correlation column is numeric
        corr_series = pd.to_numeric(corr_df['correlation'], errors='coerce')
        insights['correlations'] = {
            'highest': corr_df.loc[corr_series.idxmax()].to_dict(),
            'lowest': corr_df.loc[corr_series.idxmin()].to_dict(),
            'average': corr_series.mean()
        }

    # Sector Sharpe ratio insights
    if data['sector_sharpe_comparison'] is not None and not data['sector_sharpe_comparison'].empty:
        sharpe_df = data['sector_sharpe_comparison']
        # Identify simulation columns (exclude 'sector' column)
        sim_cols = [col for col in sharpe_df.columns if col != 'sector']

        if len(sim_cols) >= 1:
            insights['sector_sharpe'] = {}
            # Find best and worst Sharpe ratios per sector
            for sector in sharpe_df['sector']:
                row = sharpe_df[sharpe_df['sector'] == sector].iloc[0]
                values = [row[col] for col in sim_cols]
                max_val = max(values)
                min_val = min(values)
                max_sim = sim_cols[values.index(max_val)]
                min_sim = sim_cols[values.index(min_val)]
                diff = max_val - min_val

                insights['sector_sharpe'][sector] = {
                    'largest_difference': diff,
                    'best_simulation': max_sim,
                    'best_value': max_val,
                    'worst_simulation': min_sim,
                    'worst_value': min_val
                }

            # Overall best Sharpe ratios across all sectors
            best_overall = []
            for sector in sharpe_df['sector']:
                row = sharpe_df[sharpe_df['sector'] == sector].iloc[0]
                for sim in sim_cols:
                    best_overall.append((sector, sim, row[sim]))

            # Sort by Sharpe ratio descending
            best_overall.sort(key=lambda x: x[2], reverse=True)
            insights['sector_sharpe_overall'] = {
                'top_5': best_overall[:5],
                'bottom_5': best_overall[-5:] if len(best_overall) >= 5 else best_overall
            }

    return insights

def generate_markdown_report(data, insights, output_dir='outputs/comparison'):
    """Generate comprehensive comparison report in markdown"""
    report = []
    report.append("# Simulation Comparison Report")
    report.append(f"*Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    report.append("")

    # Executive Summary
    report.append("## Executive Summary")
    report.append("")

    if 'total_pnl' in insights:
        tnl = insights['total_pnl']
        report.append(f"- **Best Performing Simulation**: {tnl['best_simulation']} (${tnl['best_value']:,.2f})")
        report.append(f"- **Worst Performing Simulation**: {tnl['worst_simulation']} (${tnl['worst_value']:,.2f})")
        report.append(f"- **Performance Range**: ${tnl['range']:,.2f}")
        if 'comparisons' in tnl and tnl['comparisons']:
            for comp in tnl['comparisons']:
                report.append(f"- **{comp['pair']}**: ${comp['difference']:,.2f} ({comp['percentage']:.1f}%)")
        report.append("")

    # Total P&L Comparison
    if data['total_pnl'] is not None and not data['total_pnl'].empty:
        report.append("## Total P&L Comparison")
        report.append("")

        report.append("| Simulation | Total P&L |")
        report.append("|------------|-----------|")
        for _, row in data['total_pnl'].iterrows():
            report.append(f"| {row['simulation']} | ${row['total_pnl']:,.2f} |")
        report.append("")

    # Risk Metrics Comparison
    if data['risk_metrics'] is not None and not data['risk_metrics'].empty:
        report.append("## Risk Metrics Comparison")
        report.append("")

        risk_df = data['risk_metrics']
        # Create a table with all metrics
        report.append("| Simulation | Volatility | Avg Daily Return | Sharpe Ratio | Max Drawdown | Win Rate (%) |")
        report.append("|------------|------------|------------------|--------------|--------------|--------------|")
        for _, row in risk_df.iterrows():
            report.append(f"| {row['simulation']} | ${row.get('volatility', 0):,.2f} | ${row.get('avg_daily_return', 0):,.2f} | {row.get('sharpe_ratio', 0):.3f} | ${row.get('max_drawdown', 0):,.2f} | {row.get('win_rate', 0):.1f} |")
        report.append("")

    # Sector Performance Comparison
    if data['sector_comparison'] is not None and not data['sector_comparison'].empty:
        report.append("## Sector Performance Comparison")
        report.append("")

        sector_df = data['sector_comparison']
        sim_cols = [col for col in sector_df.columns if col != 'sector']

        # Create table header
        header = "| Sector | " + " | ".join(sim_cols) + " |"
        report.append(header)
        separator = "|--------|" + "|".join(["---" for _ in sim_cols]) + "|"
        report.append(separator)

        # Add rows
        for _, row in sector_df.iterrows():
            values = " | ".join([f"${row[col]:,.2f}" for col in sim_cols])
            report.append(f"| {row['sector']} | {values} |")
        report.append("")

        # Highlight key differences
        if 'sector' in insights and insights['sector']:
            report.append("### Key Sector Differences")
            report.append("")

            # Sort sectors by difference magnitude
            sector_diffs = []
            for sector, info in insights['sector'].items():
                sector_diffs.append((sector, info['largest_difference']))
            sector_diffs.sort(key=lambda x: abs(x[1]), reverse=True)

            for sector, diff in sector_diffs[:5]:  # Top 5 differences
                info = insights['sector'][sector]
                report.append(f"- **{sector}**: {info['best_simulation']} outperformed {info['worst_simulation']} by ${info['largest_difference']:,.2f}")
            report.append("")

    # Sector Sharpe Ratio Comparison
    if data['sector_sharpe_comparison'] is not None and not data['sector_sharpe_comparison'].empty:
        report.append("## Sector Sharpe Ratio Comparison")
        report.append("")
        report.append("Sharpe ratios measure risk-adjusted performance (higher is better). Annualized with √252 factor, assuming risk-free rate = 0.")
        report.append("")

        sharpe_df = data['sector_sharpe_comparison']
        sim_cols = [col for col in sharpe_df.columns if col != 'sector']

        # Create table header
        header = "| Sector | " + " | ".join(sim_cols) + " |"
        report.append(header)
        separator = "|--------|" + "|".join(["---" for _ in sim_cols]) + "|"
        report.append(separator)

        # Add rows
        for _, row in sharpe_df.iterrows():
            values = " | ".join([f"{row[col]:.3f}" for col in sim_cols])
            report.append(f"| {row['sector']} | {values} |")
        report.append("")

        # Highlight key insights
        if 'sector_sharpe' in insights and insights['sector_sharpe']:
            report.append("### Key Sharpe Ratio Insights")
            report.append("")

            # Find sectors with largest Sharpe ratio differences
            sharpe_diffs = []
            for sector, info in insights['sector_sharpe'].items():
                sharpe_diffs.append((sector, info['largest_difference']))
            sharpe_diffs.sort(key=lambda x: abs(x[1]), reverse=True)

            for sector, diff in sharpe_diffs[:3]:  # Top 3 differences
                info = insights['sector_sharpe'][sector]
                report.append(f"- **{sector}**: {info['best_simulation']} has best Sharpe ratio ({info['best_value']:.3f}) vs {info['worst_simulation']} ({info['worst_value']:.3f})")
            report.append("")

            # Top 5 overall Sharpe ratios
            if 'sector_sharpe_overall' in insights:
                overall = insights['sector_sharpe_overall']
                report.append("### Top 5 Risk-Adjusted Performances")
                report.append("")
                for i, (sector, sim, value) in enumerate(overall['top_5'], 1):
                    report.append(f"{i}. **{sector}** ({sim}): {value:.3f}")
                report.append("")

    # Correlation Analysis
    if data['correlations'] is not None and not data['correlations'].empty:
        report.append("## Correlation Analysis")
        report.append("")

        report.append("| Simulation Pair | Correlation |")
        report.append("|-----------------|-------------|")
        for _, row in data['correlations'].iterrows():
            corr_value = float(row['correlation'])
            # Color code based on correlation strength
            if corr_value > 0.7:
                strength = "Strong positive"
            elif corr_value > 0.3:
                strength = "Moderate positive"
            elif corr_value > -0.3:
                strength = "Weak"
            elif corr_value > -0.7:
                strength = "Moderate negative"
            else:
                strength = "Strong negative"

            report.append(f"| {row['pair']} | {corr_value:.3f} ({strength}) |")
        report.append("")

    # Visualizations
    if data['visualizations']:
        report.append("## Generated Visualizations")
        report.append("")

        report.append("The following comparative visualizations have been generated:")
        report.append("")

        viz_dir = Path(output_dir)
        for viz_file in sorted(data['visualizations']):
            report.append(f"- **{viz_file}** - `{viz_dir / viz_file}`")
        report.append("")

    # Key Insights
    report.append("## Key Insights")
    report.append("")

    if 'total_pnl' in insights:
        tnl = insights['total_pnl']
        report.append(f"1. **Performance Leadership**: {tnl['best_simulation']} achieved the highest total P&L (${tnl['best_value']:,.2f}), outperforming {tnl['worst_simulation']} by ${tnl['range']:,.2f}.")
        if 'comparisons' in tnl and tnl['comparisons']:
            for comp in tnl['comparisons']:
                if comp['difference'] > 0:
                    report.append(f"2. **{comp['pair']}**: {comp['pair'].split(' vs ')[0]} outperformed {comp['pair'].split(' vs ')[1]} by {comp['percentage']:.1f}%.")

    if 'risk_metrics' in insights:
        risk = insights['risk_metrics']
        if 'sharpe_ratio' in risk:
            sr = risk['sharpe_ratio']
            report.append(f"3. **Risk-Adjusted Performance**: {sr['best_simulation']} achieved the best Sharpe ratio ({sr['best_value']:.3f}), indicating superior risk-adjusted returns.")
        if 'volatility' in risk:
            vol = risk['volatility']
            report.append(f"4. **Risk Profile**: {vol['best_simulation']} exhibited the lowest volatility (${vol['best_value']:,.2f}), suggesting a more stable performance.")

    if 'sector' in insights and insights['sector']:
        # Find sector with largest absolute difference
        max_diff_sector = max(insights['sector'].items(), key=lambda x: abs(x[1]['largest_difference']))[0]
        max_diff_info = insights['sector'][max_diff_sector]
        report.append(f"5. **Sector Divergence**: The largest performance difference occurred in {max_diff_sector} sector, where {max_diff_info['best_simulation']} outperformed {max_diff_info['worst_simulation']} by ${max_diff_info['largest_difference']:,.2f}.")

    if 'sector_sharpe' in insights and insights['sector_sharpe']:
        # Find sector with largest Sharpe ratio difference
        sharpe_diffs = [(sector, info['largest_difference']) for sector, info in insights['sector_sharpe'].items()]
        if sharpe_diffs:
            max_sharpe_diff_sector = max(sharpe_diffs, key=lambda x: abs(x[1]))[0]
            max_sharpe_info = insights['sector_sharpe'][max_sharpe_diff_sector]
            report.append(f"6. **Risk-Adjusted Sector Performance**: {max_sharpe_info['best_simulation']} achieved the best Sharpe ratio in {max_sharpe_diff_sector} sector ({max_sharpe_info['best_value']:.3f}), indicating superior risk-adjusted returns in that sector.")

    if 'correlations' in insights:
        corr = insights['correlations']
        report.append(f"7. **Return Correlation**: Simulation pairs show an average correlation of {corr['average']:.3f}, indicating {'similar' if corr['average'] > 0.5 else 'divergent'} return patterns.")

    report.append("")

    # Recommendations
    report.append("## Recommendations")
    report.append("")

    if 'total_pnl' in insights:
        tnl = insights['total_pnl']
        report.append(f"1. **Primary Strategy**: Consider adopting the {tnl['best_simulation']} strategy as it demonstrated superior overall performance.")
        report.append(f"2. **Risk Management**: Monitor the risk metrics of {tnl['worst_simulation']} to understand factors contributing to underperformance.")

    if 'risk_metrics' in insights and 'sharpe_ratio' in insights['risk_metrics']:
        sr = insights['risk_metrics']['sharpe_ratio']
        if sr['best_simulation'] != tnl['best_simulation']:
            report.append(f"3. **Risk-Adjusted Focus**: While {tnl['best_simulation']} achieved higher total P&L, {sr['best_simulation']} offers better risk-adjusted returns (Sharpe ratio).")

    if 'sector' in insights and insights['sector']:
        report.append(f"4. **Sector Analysis**: Investigate sector-level differences to understand drivers of performance divergence.")
        report.append(f"5. **Portfolio Construction**: Consider blending strategies based on sector strengths to optimize overall portfolio performance.")

    if 'sector_sharpe' in insights and insights['sector_sharpe']:
        report.append(f"6. **Risk-Adjusted Sector Focus**: Review sector Sharpe ratios to identify which simulations deliver superior risk-adjusted returns in specific sectors for targeted strategy improvements.")

    report.append("")

    # Write to file
    report_path = Path(output_dir) / 'comparison_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report))

    print(f"Comparison report saved to: {report_path}")
    return report

def generate_html_report(markdown_report, output_dir='outputs/comparison'):
    """Convert markdown report to simple HTML"""
    html_report = []
    html_report.append("<!DOCTYPE html>")
    html_report.append("<html lang='en'>")
    html_report.append("<head>")
    html_report.append("<meta charset='UTF-8'>")
    html_report.append("<meta name='viewport' content='width=device-width, initial-scale=1.0'>")
    html_report.append("<title>Simulation Comparison Report</title>")
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

    # Convert markdown lines to simple HTML
    for line in markdown_report:
        if line.startswith("# "):
            html_report.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_report.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html_report.append(f"<h3>{line[4:]}</h3>")
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

    html_path = Path(output_dir) / 'comparison_report.html'
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(html_report))

    print(f"HTML comparison report saved to: {html_path}")

def main():
    parser = argparse.ArgumentParser(description='Generate comprehensive comparison report from simulation analysis results')
    parser.add_argument('--comparison-dir', '-c', default='outputs/comparison',
                        help='Directory containing comparison results (default: outputs/comparison)')
    parser.add_argument('--output-dir', '-o', default='outputs/comparison',
                        help='Directory to save reports (default: outputs/comparison)')

    args = parser.parse_args()

    print("="*60)
    print("GENERATING COMPARISON REPORT")
    print("="*60)

    # Load comparison data
    print("Loading comparison data...")
    data = load_comparison_data(args.comparison_dir)

    # Check if we have any data
    if all(v is None or (isinstance(v, list) and len(v) == 0) for v in data.values()):
        print(f"ERROR: No comparison data found in {args.comparison_dir}")
        print("Please run compare_simulations.py first to generate comparison results")
        return

    # Generate insights
    print("Generating insights...")
    insights = generate_comparison_insights(data)

    # Generate markdown report
    print("Generating markdown report...")
    markdown_report = generate_markdown_report(data, insights, args.output_dir)

    # Generate HTML report
    print("Generating HTML report...")
    generate_html_report(markdown_report, args.output_dir)

    print("\n" + "="*60)
    print("COMPARISON REPORT GENERATION COMPLETE")
    print("="*60)
    print(f"Reports saved to: {args.output_dir}")
    print("  - comparison_report.md")
    print("  - comparison_report.html")
    print("="*60)

if __name__ == '__main__':
    main()