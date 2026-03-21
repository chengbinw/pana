import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# Set style for plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def load_simulation_data(simulation, output_base_dir='outputs'):
    """Load analysis results for a single simulation"""
    sim_dir = Path(output_base_dir) / simulation / 'pnl_results'

    if not sim_dir.exists():
        print(f"Warning: Results directory not found for simulation '{simulation}' at {sim_dir}")
        return None, None, None

    try:
        sector_daily_path = sim_dir / 'sector_daily_pnl.csv'
        sector_summary_path = sim_dir / 'sector_summary.csv'
        daily_total_path = sim_dir / 'daily_total_pnl.csv'

        if not sector_daily_path.exists():
            print(f"Warning: sector_daily_pnl.csv not found for '{simulation}'")
            return None, None, None

        sector_daily = pd.read_csv(sector_daily_path, parse_dates=['date'])
        sector_summary = pd.read_csv(sector_summary_path)
        daily_total = pd.read_csv(daily_total_path, parse_dates=['date'])

        # Add simulation identifier
        sector_daily['simulation'] = simulation
        sector_summary['simulation'] = simulation
        daily_total['simulation'] = simulation

        print(f"Loaded data for simulation '{simulation}':")
        print(f"  - Sector daily: {sector_daily.shape} rows")
        print(f"  - Sector summary: {sector_summary.shape} rows")
        print(f"  - Daily total: {daily_total.shape} rows")

        return sector_daily, sector_summary, daily_total

    except Exception as e:
        print(f"Error loading data for '{simulation}': {e}")
        return None, None, None

def align_dates_across_simulations(sector_daily_dict):
    """Align dates across simulations to ensure fair comparison"""
    # Find common date range
    all_dates = []
    for sim, data in sector_daily_dict.items():
        if data is not None and not data.empty:
            all_dates.append(set(data['date']))

    if not all_dates:
        return sector_daily_dict

    common_dates = set.intersection(*all_dates)
    print(f"Found {len(common_dates)} common dates across simulations")

    # Filter each simulation to common dates
    aligned_dict = {}
    for sim, data in sector_daily_dict.items():
        if data is not None and not data.empty:
            aligned_data = data[data['date'].isin(common_dates)].copy()
            aligned_dict[sim] = aligned_data
        else:
            aligned_dict[sim] = data

    return aligned_dict

def calculate_comparison_metrics(sector_daily_dict, sector_summary_dict, daily_total_dict):
    """Calculate comparative metrics across simulations"""
    comparison_metrics = {}

    # 1. Total P&L comparison
    total_pnl_comparison = []
    for sim, summary in sector_summary_dict.items():
        if summary is not None and not summary.empty:
            total_pnl = summary['total_pnl'].sum()
            total_pnl_comparison.append({
                'simulation': sim,
                'total_pnl': total_pnl
            })

    total_pnl_df = pd.DataFrame(total_pnl_comparison)
    if len(total_pnl_df) >= 2:
        # Calculate differences and percentages
        base_sim = total_pnl_df.iloc[0]['simulation']
        base_pnl = total_pnl_df.iloc[0]['total_pnl']

        for i in range(1, len(total_pnl_df)):
            sim = total_pnl_df.iloc[i]['simulation']
            sim_pnl = total_pnl_df.iloc[i]['total_pnl']
            diff = sim_pnl - base_pnl
            pct_diff = (diff / abs(base_pnl)) * 100 if base_pnl != 0 else np.nan

            comparison_metrics[f'pnl_diff_{sim}_vs_{base_sim}'] = diff
            comparison_metrics[f'pnl_pct_diff_{sim}_vs_{base_sim}'] = pct_diff

    # 2. Sector performance comparison
    sector_comparison = {}
    all_sectors = set()

    # Collect all sectors across simulations
    for sim, summary in sector_summary_dict.items():
        if summary is not None and not summary.empty:
            all_sectors.update(summary['sector'].unique())

    # Compare sector performance
    for sector in all_sectors:
        sector_data = {}
        for sim, summary in sector_summary_dict.items():
            if summary is not None and not summary.empty:
                sector_row = summary[summary['sector'] == sector]
                if not sector_row.empty:
                    sector_data[sim] = sector_row.iloc[0]['total_pnl']
                else:
                    sector_data[sim] = 0

        sector_comparison[sector] = sector_data

    # 3. Risk metrics comparison
    risk_metrics = []
    for sim, daily in sector_daily_dict.items():
        if daily is not None and not daily.empty:
            # Calculate daily returns (using total_pnl)
            daily_returns = daily.groupby('date')['total_pnl'].sum()

            # Volatility (standard deviation of daily returns)
            volatility = daily_returns.std()

            # Average daily return
            avg_daily_return = daily_returns.mean()

            # Sharpe ratio (assuming risk-free rate = 0 for simplicity)
            sharpe_ratio = avg_daily_return / volatility if volatility != 0 else 0

            # Maximum drawdown
            cumulative = daily_returns.cumsum()
            running_max = cumulative.cummax()
            drawdown = cumulative - running_max
            max_drawdown = drawdown.min()

            # Win rate (days with positive return)
            win_rate = (daily_returns > 0).sum() / len(daily_returns) * 100

            risk_metrics.append({
                'simulation': sim,
                'volatility': volatility,
                'avg_daily_return': avg_daily_return,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate
            })

    risk_metrics_df = pd.DataFrame(risk_metrics)

    # 4. Correlation analysis between daily returns
    correlation_data = {}
    if len(sector_daily_dict) >= 2:
        # Get common dates first
        aligned_dict = align_dates_across_simulations(sector_daily_dict)

        # Extract daily returns for each simulation
        daily_returns_dict = {}
        for sim, daily in aligned_dict.items():
            if daily is not None and not daily.empty:
                daily_returns = daily.groupby('date')['total_pnl'].sum()
                daily_returns_dict[sim] = daily_returns

        # Calculate pairwise correlations
        if len(daily_returns_dict) >= 2:
            sim_names = list(daily_returns_dict.keys())
            for i in range(len(sim_names)):
                for j in range(i+1, len(sim_names)):
                    sim1, sim2 = sim_names[i], sim_names[j]
                    returns1 = daily_returns_dict[sim1]
                    returns2 = daily_returns_dict[sim2]

                    # Ensure same length (should be due to alignment)
                    min_len = min(len(returns1), len(returns2))
                    if min_len > 1:
                        corr = returns1.iloc[:min_len].corr(returns2.iloc[:min_len])
                        correlation_data[f'{sim1}_vs_{sim2}'] = corr

    return {
        'total_pnl_comparison': total_pnl_df,
        'sector_comparison': sector_comparison,
        'risk_metrics': risk_metrics_df,
        'correlations': correlation_data,
        'comparison_metrics': comparison_metrics
    }

def generate_comparison_visualizations(comparison_results, simulations, sector_daily_dict, output_dir):
    """Generate comparative visualizations"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nGenerating comparison visualizations in '{output_dir}'...")

    # 1. Total P&L Comparison Bar Chart
    if 'total_pnl_comparison' in comparison_results and not comparison_results['total_pnl_comparison'].empty:
        plt.figure(figsize=(10, 6))
        df = comparison_results['total_pnl_comparison']
        colors = plt.cm.Set3(np.linspace(0, 1, len(df)))

        bars = plt.bar(df['simulation'], df['total_pnl'], color=colors)
        plt.title('Total P&L Comparison Across Simulations', fontsize=14, fontweight='bold')
        plt.xlabel('Simulation')
        plt.ylabel('Total P&L ($)')

        # Add value labels
        for bar in bars:
            height = bar.get_height()
            plt.text(bar.get_x() + bar.get_width()/2., height,
                    f'${height:,.0f}', ha='center', va='bottom' if height >= 0 else 'top',
                    fontsize=10)

        plt.tight_layout()
        plt.savefig(output_dir / 'total_pnl_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()

    # 2. Sector Performance Side-by-Side Bar Chart
    if 'sector_comparison' in comparison_results and comparison_results['sector_comparison']:
        sector_comp = comparison_results['sector_comparison']
        sectors = list(sector_comp.keys())

        if sectors and len(simulations) >= 2:
            # Prepare data for grouped bar chart
            x = np.arange(len(sectors))
            width = 0.8 / len(simulations)

            plt.figure(figsize=(14, 8))

            for i, sim in enumerate(simulations):
                values = [sector_comp[sector].get(sim, 0) for sector in sectors]
                plt.bar(x + i*width - width*(len(simulations)-1)/2, values,
                       width=width, label=sim, alpha=0.8)

            plt.title('Sector P&L Comparison Across Simulations', fontsize=14, fontweight='bold')
            plt.xlabel('Sector')
            plt.ylabel('Total P&L ($)')
            plt.xticks(x, sectors, rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            plt.savefig(output_dir / 'sector_pnl_comparison.png', dpi=150, bbox_inches='tight')
            plt.close()

    # 3. Cumulative P&L Overlay Line Chart
    if len(simulations) >= 2 and sector_daily_dict:
        plt.figure(figsize=(12, 6))

        # Align dates across simulations
        aligned_dict = align_dates_across_simulations(sector_daily_dict)

        # Plot cumulative P&L for each simulation
        colors = plt.cm.tab10(np.linspace(0, 1, len(simulations)))

        for idx, sim in enumerate(simulations):
            if sim in aligned_dict and aligned_dict[sim] is not None and not aligned_dict[sim].empty:
                # Get daily total P&L for this simulation
                daily_data = aligned_dict[sim]
                daily_total = daily_data.groupby('date')['total_pnl'].sum().sort_index()

                # Calculate cumulative P&L
                cumulative_pnl = daily_total.cumsum()

                # Plot
                plt.plot(cumulative_pnl.index, cumulative_pnl.values,
                        label=sim, color=colors[idx], linewidth=2, alpha=0.8)

        plt.title('Cumulative P&L Comparison Across Simulations', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Cumulative P&L ($)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'cumulative_pnl_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()

    # 4. Risk Metrics Radar Chart (or grouped bar chart)
    if 'risk_metrics' in comparison_results and not comparison_results['risk_metrics'].empty:
        df = comparison_results['risk_metrics']

        # Create subplots for different risk metrics
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        axes = axes.flatten()

        metrics = ['volatility', 'avg_daily_return', 'sharpe_ratio',
                  'max_drawdown', 'win_rate']
        titles = ['Volatility (Std Dev)', 'Avg Daily Return', 'Sharpe Ratio',
                 'Max Drawdown', 'Win Rate (%)']

        for idx, (metric, title) in enumerate(zip(metrics, titles)):
            if idx < len(axes):
                ax = axes[idx]
                if metric in df.columns:
                    ax.bar(df['simulation'], df[metric], color=plt.cm.Set3(np.linspace(0, 1, len(df))))
                    ax.set_title(title, fontsize=12)
                    ax.set_xlabel('Simulation')
                    ax.tick_params(axis='x', rotation=45)

        # Remove any unused subplots
        for idx in range(len(metrics), len(axes)):
            fig.delaxes(axes[idx])

        fig.suptitle('Risk Metrics Comparison Across Simulations', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_dir / 'risk_metrics_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()

    # 5. Correlation Heatmap
    if 'correlations' in comparison_results and comparison_results['correlations']:
        correlations = comparison_results['correlations']

        if correlations:
            # Create correlation matrix
            sim_pairs = list(correlations.keys())
            corr_values = list(correlations.values())

            # For simplicity, create a simple bar chart of correlations
            plt.figure(figsize=(10, 6))
            x_pos = np.arange(len(sim_pairs))
            colors = ['green' if v > 0 else 'red' for v in corr_values]

            bars = plt.bar(x_pos, corr_values, color=colors, alpha=0.7)
            plt.title('Daily Returns Correlation Between Simulations', fontsize=14, fontweight='bold')
            plt.xlabel('Simulation Pair')
            plt.ylabel('Correlation Coefficient')
            plt.xticks(x_pos, sim_pairs, rotation=45, ha='right')
            plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

            # Add value labels
            for bar, value in zip(bars, corr_values):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height/2,
                        f'{value:.3f}', ha='center', va='center',
                        fontsize=9, color='white' if abs(height) > 0.15 else 'black')

            plt.tight_layout()
            plt.savefig(output_dir / 'returns_correlation.png', dpi=150, bbox_inches='tight')
            plt.close()

    print(f"Generated {len(list(output_dir.glob('*.png')))} visualization files")

def save_comparison_results(comparison_results, output_dir):
    """Save comparison results to CSV files"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving comparison results to '{output_dir}'...")

    # Save total P&L comparison
    if 'total_pnl_comparison' in comparison_results and not comparison_results['total_pnl_comparison'].empty:
        comparison_results['total_pnl_comparison'].to_csv(output_dir / 'total_pnl_comparison.csv', index=False)

    # Save risk metrics
    if 'risk_metrics' in comparison_results and not comparison_results['risk_metrics'].empty:
        comparison_results['risk_metrics'].to_csv(output_dir / 'risk_metrics_comparison.csv', index=False)

    # Save sector comparison as JSON (since it's nested)
    if 'sector_comparison' in comparison_results and comparison_results['sector_comparison']:
        import json
        sector_comp = comparison_results['sector_comparison']

        # Convert to serializable format
        serializable_sector_comp = {}
        for sector, sim_data in sector_comp.items():
            serializable_sector_comp[str(sector)] = {str(k): float(v) for k, v in sim_data.items()}

        with open(output_dir / 'sector_comparison.json', 'w') as f:
            json.dump(serializable_sector_comp, f, indent=2)

    # Save correlation data
    if 'correlations' in comparison_results and comparison_results['correlations']:
        pd.Series(comparison_results['correlations']).to_csv(output_dir / 'correlations.csv', header=['correlation'])

    # Save summary metrics
    if 'comparison_metrics' in comparison_results and comparison_results['comparison_metrics']:
        pd.Series(comparison_results['comparison_metrics']).to_csv(output_dir / 'comparison_metrics.csv', header=['value'])

    print(f"Saved {len(list(output_dir.glob('*.csv')))} + {len(list(output_dir.glob('*.json')))} result files")

def main():
    parser = argparse.ArgumentParser(description='Compare P&L analysis results across multiple simulations')
    parser.add_argument('simulations', nargs='+',
                        help='Simulation names to compare (e.g., TWOFISH BLOWFISH)')
    parser.add_argument('--output-base-dir', '-o', default='outputs',
                        help='Base output directory containing simulation results (default: outputs)')
    parser.add_argument('--comparison-dir', '-c', default='comparison',
                        help='Directory to save comparison results (default: outputs/comparison)')

    args = parser.parse_args()

    print("="*60)
    print("COMPARING SIMULATION RESULTS")
    print("="*60)
    print(f"Simulations to compare: {', '.join(args.simulations)}")
    print(f"Results directory: {args.output_base_dir}")
    print(f"Comparison output: {args.comparison_dir}")
    print()

    # Load data for each simulation
    sector_daily_dict = {}
    sector_summary_dict = {}
    daily_total_dict = {}

    for sim in args.simulations:
        print(f"Loading data for simulation '{sim}'...")
        sector_daily, sector_summary, daily_total = load_simulation_data(sim, args.output_base_dir)

        if sector_daily is not None:
            sector_daily_dict[sim] = sector_daily
            sector_summary_dict[sim] = sector_summary
            daily_total_dict[sim] = daily_total
        else:
            print(f"  Warning: Could not load data for '{sim}', skipping")

    if len(sector_daily_dict) < 2:
        print("\nERROR: Need at least 2 simulations with valid data to compare")
        print(f"Successfully loaded {len(sector_daily_dict)} simulation(s)")
        return

    print(f"\nSuccessfully loaded data for {len(sector_daily_dict)} simulation(s)")

    # Calculate comparison metrics
    print("\nCalculating comparison metrics...")
    comparison_results = calculate_comparison_metrics(sector_daily_dict, sector_summary_dict, daily_total_dict)

    # Generate visualizations
    comparison_output_dir = Path(args.output_base_dir) / args.comparison_dir
    generate_comparison_visualizations(comparison_results, list(sector_daily_dict.keys()), sector_daily_dict, comparison_output_dir)

    # Save results
    save_comparison_results(comparison_results, comparison_output_dir)

    print("\n" + "="*60)
    print("COMPARISON COMPLETE")
    print("="*60)
    print(f"Results saved to: {comparison_output_dir}")
    print(f"Visualizations: {comparison_output_dir}/*.png")
    print(f"Data files: {comparison_output_dir}/*.csv")
    print("="*60)

if __name__ == '__main__':
    main()