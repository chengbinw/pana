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

def load_simulation_data(simulation, output_base_dir='outputs', year=None):
    """Load analysis results for a single simulation including sector and bizsector data
    If year is provided, filter data to that year and compute summaries from filtered daily data"""
    sim_dir = Path(output_base_dir) / simulation / 'pnl_results'

    if not sim_dir.exists():
        print(f"Warning: Results directory not found for simulation '{simulation}' at {sim_dir}")
        return None, None, None, None, None

    try:
        sector_daily_path = sim_dir / 'sector_daily_pnl.csv'
        sector_summary_path = sim_dir / 'sector_summary.csv'
        daily_total_path = sim_dir / 'daily_total_pnl.csv'
        bizsector_daily_path = sim_dir / 'bizsector_daily_pnl.csv'
        bizsector_summary_path = sim_dir / 'bizsector_summary.csv'

        if not sector_daily_path.exists():
            print(f"Warning: sector_daily_pnl.csv not found for '{simulation}'")
            return None, None, None, None, None

        sector_daily = pd.read_csv(sector_daily_path, parse_dates=['date'])
        daily_total = pd.read_csv(daily_total_path, parse_dates=['date'])

        # Load bizsector data if available
        bizsector_daily = None
        if bizsector_daily_path.exists():
            bizsector_daily = pd.read_csv(bizsector_daily_path, parse_dates=['date'])
        else:
            print(f"  Note: Bizsector data not found for '{simulation}', skipping bizsector comparison")

        # Filter by year if specified
        if year is not None:
            year = int(year)  # Ensure year is Python int
            sector_daily = sector_daily[sector_daily['date'].dt.year == year].copy()
            daily_total = daily_total[daily_total['date'].dt.year == year].copy()
            if bizsector_daily is not None:
                bizsector_daily = bizsector_daily[bizsector_daily['date'].dt.year == year].copy()
            # Compute summaries from filtered daily data
            sector_summary = compute_sector_summary_from_daily(sector_daily)
            if bizsector_daily is not None and not bizsector_daily.empty:
                bizsector_summary = compute_bizsector_summary_from_daily(bizsector_daily)
            else:
                bizsector_summary = None
        else:
            # Load precomputed summaries
            sector_summary = pd.read_csv(sector_summary_path)
            if bizsector_daily is not None:
                bizsector_summary = pd.read_csv(bizsector_summary_path)
            else:
                bizsector_summary = None

        # Add simulation identifier
        sector_daily['simulation'] = simulation
        sector_summary['simulation'] = simulation
        daily_total['simulation'] = simulation
        if bizsector_daily is not None:
            bizsector_daily['simulation'] = simulation
        if bizsector_summary is not None:
            bizsector_summary['simulation'] = simulation

        print(f"Loaded data for simulation '{simulation}':")
        print(f"  - Sector daily: {sector_daily.shape} rows")
        print(f"  - Sector summary: {sector_summary.shape} rows")
        print(f"  - Daily total: {daily_total.shape} rows")
        if bizsector_daily is not None:
            print(f"  - Bizsector daily: {bizsector_daily.shape} rows")
        if bizsector_summary is not None:
            print(f"  - Bizsector summary: {bizsector_summary.shape} rows")

        return sector_daily, sector_summary, daily_total, bizsector_daily, bizsector_summary

    except Exception as e:
        print(f"Error loading data for '{simulation}': {e}")
        return None, None, None, None, None

def compute_sector_summary_from_daily(sector_daily):
    """Compute sector summary from daily P&L data"""
    if sector_daily is None or sector_daily.empty:
        return pd.DataFrame()

    # Group by sector
    sector_summary = sector_daily.groupby('sector').agg({
        'total_pnl': 'sum',
        'symbol_count': 'mean',
        'total_exposure': 'mean'
    }).reset_index()

    # Calculate Sharpe ratio per sector
    sharpe_ratios = []
    for sector in sector_daily['sector'].unique():
        sector_data = sector_daily[sector_daily['sector'] == sector]
        daily_pnl = sector_data['total_pnl']
        if len(daily_pnl) < 2:
            sharpe = 0
        else:
            mean_return = daily_pnl.mean()
            std_return = daily_pnl.std()
            if std_return != 0:
                sharpe = mean_return / std_return * np.sqrt(252)
            else:
                sharpe = 0
        sharpe_ratios.append({'sector': sector, 'sharpe_ratio': sharpe})

    sharpe_df = pd.DataFrame(sharpe_ratios)
    sector_summary = pd.merge(sector_summary, sharpe_df, on='sector', how='left')
    return sector_summary

def compute_bizsector_summary_from_daily(bizsector_daily):
    """Compute bizsector summary from daily P&L data"""
    if bizsector_daily is None or bizsector_daily.empty:
        return pd.DataFrame()

    # Group by bizsector
    bizsector_summary = bizsector_daily.groupby('bizsector').agg({
        'total_pnl': 'sum',
        'symbol_count': 'mean',
        'total_exposure': 'mean'
    }).reset_index()

    # Calculate Sharpe ratio per bizsector
    sharpe_ratios = []
    for bizsector in bizsector_daily['bizsector'].unique():
        bizsector_data = bizsector_daily[bizsector_daily['bizsector'] == bizsector]
        daily_pnl = bizsector_data['total_pnl']
        if len(daily_pnl) < 2:
            sharpe = 0
        else:
            mean_return = daily_pnl.mean()
            std_return = daily_pnl.std()
            if std_return != 0:
                sharpe = mean_return / std_return * np.sqrt(252)
            else:
                sharpe = 0
        sharpe_ratios.append({'bizsector': bizsector, 'sharpe_ratio': sharpe})

    sharpe_df = pd.DataFrame(sharpe_ratios)
    bizsector_summary = pd.merge(bizsector_summary, sharpe_df, on='bizsector', how='left')
    return bizsector_summary

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

def calculate_comparison_metrics(sector_daily_dict, sector_summary_dict, daily_total_dict,
                                 bizsector_daily_dict=None, bizsector_summary_dict=None):
    """Calculate comparative metrics across simulations including sector and bizsector levels"""
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

    # 3. Sector Sharpe ratio comparison
    sector_sharpe_comparison = {}
    all_sectors = set()
    for sim, summary in sector_summary_dict.items():
        if summary is not None and not summary.empty:
            all_sectors.update(summary['sector'].unique())

    for sector in all_sectors:
        sector_data = {}
        for sim, summary in sector_summary_dict.items():
            if summary is not None and not summary.empty:
                sector_row = summary[summary['sector'] == sector]
                if not sector_row.empty:
                    sector_data[sim] = sector_row.iloc[0]['sharpe_ratio']
                else:
                    sector_data[sim] = 0
        sector_sharpe_comparison[sector] = sector_data

    # 4. Bizsector performance comparison (if data available)
    bizsector_comparison = {}
    bizsector_sharpe_comparison = {}

    if bizsector_summary_dict is not None and any(v is not None and not v.empty for v in bizsector_summary_dict.values()):
        all_bizsectors = set()
        # Collect all bizsectors across simulations
        for sim, summary in bizsector_summary_dict.items():
            if summary is not None and not summary.empty:
                all_bizsectors.update(summary['bizsector'].unique())

        # Compare bizsector performance
        for bizsector in all_bizsectors:
            bizsector_data = {}
            for sim, summary in bizsector_summary_dict.items():
                if summary is not None and not summary.empty:
                    bizsector_row = summary[summary['bizsector'] == bizsector]
                    if not bizsector_row.empty:
                        bizsector_data[sim] = bizsector_row.iloc[0]['total_pnl']
                    else:
                        bizsector_data[sim] = 0
            bizsector_comparison[bizsector] = bizsector_data

        # Bizsector Sharpe ratio comparison
        all_bizsectors = set()
        for sim, summary in bizsector_summary_dict.items():
            if summary is not None and not summary.empty:
                all_bizsectors.update(summary['bizsector'].unique())

        for bizsector in all_bizsectors:
            bizsector_data = {}
            for sim, summary in bizsector_summary_dict.items():
                if summary is not None and not summary.empty:
                    bizsector_row = summary[summary['bizsector'] == bizsector]
                    if not bizsector_row.empty:
                        bizsector_data[sim] = bizsector_row.iloc[0]['sharpe_ratio']
                    else:
                        bizsector_data[sim] = 0
            bizsector_sharpe_comparison[bizsector] = bizsector_data

    # 5. Risk metrics comparison
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

    # 6. Correlation analysis between daily returns
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
        'sector_sharpe_comparison': sector_sharpe_comparison,
        'bizsector_comparison': bizsector_comparison,
        'bizsector_sharpe_comparison': bizsector_sharpe_comparison,
        'risk_metrics': risk_metrics_df,
        'correlations': correlation_data,
        'comparison_metrics': comparison_metrics
    }

def generate_comparison_visualizations(comparison_results, simulations, sector_daily_dict, output_dir, year=None):
    """Generate comparative visualizations

    Parameters:
    - comparison_results: Dictionary with comparison metrics
    - simulations: List of simulation names
    - sector_daily_dict: Dictionary of daily sector data per simulation
    - output_dir: Directory to save visualizations
    - year: Optional year for yearly reports, adds year to titles
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nGenerating comparison visualizations in '{output_dir}'...")

    # Add year suffix to titles if year is specified
    year_suffix = f" (Year {year})" if year is not None else ""

    # 1. Total P&L Comparison Bar Chart
    if 'total_pnl_comparison' in comparison_results and not comparison_results['total_pnl_comparison'].empty:
        plt.figure(figsize=(10, 6))
        df = comparison_results['total_pnl_comparison']
        colors = plt.cm.Set3(np.linspace(0, 1, len(df)))

        bars = plt.bar(df['simulation'], df['total_pnl'], color=colors)
        plt.title(f'Total P&L Comparison Across Simulations{year_suffix}', fontsize=14, fontweight='bold')
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

            plt.title(f'Sector P&L Comparison Across Simulations{year_suffix}', fontsize=14, fontweight='bold')
            plt.xlabel('Sector')
            plt.ylabel('Total P&L ($)')
            plt.xticks(x, sectors, rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            plt.savefig(output_dir / 'sector_pnl_comparison.png', dpi=150, bbox_inches='tight')
            plt.close()

    # 3. Sector Sharpe Ratio Comparison
    if 'sector_sharpe_comparison' in comparison_results and comparison_results['sector_sharpe_comparison']:
        sector_sharpe_comp = comparison_results['sector_sharpe_comparison']
        sectors = list(sector_sharpe_comp.keys())

        if sectors and len(simulations) >= 2:
            # Prepare data for grouped bar chart
            x = np.arange(len(sectors))
            width = 0.8 / len(simulations)

            plt.figure(figsize=(14, 8))

            for i, sim in enumerate(simulations):
                values = [sector_sharpe_comp[sector].get(sim, 0) for sector in sectors]
                plt.bar(x + i*width - width*(len(simulations)-1)/2, values,
                       width=width, label=sim, alpha=0.8)

            plt.title(f'Sector Sharpe Ratio Comparison Across Simulations{year_suffix}', fontsize=14, fontweight='bold')
            plt.xlabel('Sector')
            plt.ylabel('Sharpe Ratio (annualized)')
            plt.xticks(x, sectors, rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            plt.savefig(output_dir / 'sector_sharpe_comparison.png', dpi=150, bbox_inches='tight')
            plt.close()

    # Bizsector Performance Side-by-Side Bar Chart
    if 'bizsector_comparison' in comparison_results and comparison_results['bizsector_comparison']:
        bizsector_comp = comparison_results['bizsector_comparison']
        bizsectors = list(bizsector_comp.keys())

        if bizsectors and len(simulations) >= 2:
            # Prepare data for grouped bar chart
            x = np.arange(len(bizsectors))
            width = 0.8 / len(simulations)

            plt.figure(figsize=(16, 10))

            for i, sim in enumerate(simulations):
                values = [bizsector_comp[bizsector].get(sim, 0) for bizsector in bizsectors]
                plt.bar(x + i*width - width*(len(simulations)-1)/2, values,
                       width=width, label=sim, alpha=0.8)

            plt.title(f'Bizsector P&L Comparison Across Simulations{year_suffix}', fontsize=14, fontweight='bold')
            plt.xlabel('Bizsector')
            plt.ylabel('Total P&L ($)')
            plt.xticks(x, bizsectors, rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            plt.savefig(output_dir / 'bizsector_pnl_comparison.png', dpi=150, bbox_inches='tight')
            plt.close()

    # Bizsector Sharpe Ratio Comparison
    if 'bizsector_sharpe_comparison' in comparison_results and comparison_results['bizsector_sharpe_comparison']:
        bizsector_sharpe_comp = comparison_results['bizsector_sharpe_comparison']
        bizsectors = list(bizsector_sharpe_comp.keys())

        if bizsectors and len(simulations) >= 2:
            # Prepare data for grouped bar chart
            x = np.arange(len(bizsectors))
            width = 0.8 / len(simulations)

            plt.figure(figsize=(16, 10))

            for i, sim in enumerate(simulations):
                values = [bizsector_sharpe_comp[bizsector].get(sim, 0) for bizsector in bizsectors]
                plt.bar(x + i*width - width*(len(simulations)-1)/2, values,
                       width=width, label=sim, alpha=0.8)

            plt.title(f'Bizsector Sharpe Ratio Comparison Across Simulations{year_suffix}', fontsize=14, fontweight='bold')
            plt.xlabel('Bizsector')
            plt.ylabel('Sharpe Ratio (annualized)')
            plt.xticks(x, bizsectors, rotation=45, ha='right')
            plt.legend()
            plt.tight_layout()
            plt.savefig(output_dir / 'bizsector_sharpe_comparison.png', dpi=150, bbox_inches='tight')
            plt.close()

    # 4. Cumulative P&L Overlay Line Chart
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

        plt.title(f'Cumulative P&L Comparison Across Simulations{year_suffix}', fontsize=14, fontweight='bold')
        plt.xlabel('Date')
        plt.ylabel('Cumulative P&L ($)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_dir / 'cumulative_pnl_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()

    # 5. Risk Metrics Radar Chart (or grouped bar chart)
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

        fig.suptitle(f'Risk Metrics Comparison Across Simulations{year_suffix}', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(output_dir / 'risk_metrics_comparison.png', dpi=150, bbox_inches='tight')
        plt.close()

    # 6. Correlation Heatmap
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
            plt.title(f'Daily Returns Correlation Between Simulations{year_suffix}', fontsize=14, fontweight='bold')
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

    # Save sector Sharpe comparison as JSON (since it's nested)
    if 'sector_sharpe_comparison' in comparison_results and comparison_results['sector_sharpe_comparison']:
        import json
        sector_sharpe_comp = comparison_results['sector_sharpe_comparison']

        # Convert to serializable format
        serializable_sector_sharpe_comp = {}
        for sector, sim_data in sector_sharpe_comp.items():
            serializable_sector_sharpe_comp[str(sector)] = {str(k): float(v) for k, v in sim_data.items()}

        with open(output_dir / 'sector_sharpe_comparison.json', 'w') as f:
            json.dump(serializable_sector_sharpe_comp, f, indent=2)

    # Save bizsector comparison as JSON (since it's nested)
    if 'bizsector_comparison' in comparison_results and comparison_results['bizsector_comparison']:
        import json
        bizsector_comp = comparison_results['bizsector_comparison']

        # Convert to serializable format
        serializable_bizsector_comp = {}
        for bizsector, sim_data in bizsector_comp.items():
            serializable_bizsector_comp[str(bizsector)] = {str(k): float(v) for k, v in sim_data.items()}

        with open(output_dir / 'bizsector_comparison.json', 'w') as f:
            json.dump(serializable_bizsector_comp, f, indent=2)

    # Save bizsector Sharpe comparison as JSON (since it's nested)
    if 'bizsector_sharpe_comparison' in comparison_results and comparison_results['bizsector_sharpe_comparison']:
        import json
        bizsector_sharpe_comp = comparison_results['bizsector_sharpe_comparison']

        # Convert to serializable format
        serializable_bizsector_sharpe_comp = {}
        for bizsector, sim_data in bizsector_sharpe_comp.items():
            serializable_bizsector_sharpe_comp[str(bizsector)] = {str(k): float(v) for k, v in sim_data.items()}

        with open(output_dir / 'bizsector_sharpe_comparison.json', 'w') as f:
            json.dump(serializable_bizsector_sharpe_comp, f, indent=2)

    # Save correlation data
    if 'correlations' in comparison_results and comparison_results['correlations']:
        pd.Series(comparison_results['correlations']).to_csv(output_dir / 'correlations.csv', header=['correlation'])

    # Save summary metrics
    if 'comparison_metrics' in comparison_results and comparison_results['comparison_metrics']:
        pd.Series(comparison_results['comparison_metrics']).to_csv(output_dir / 'comparison_metrics.csv', header=['value'])

    print(f"Saved {len(list(output_dir.glob('*.csv')))} + {len(list(output_dir.glob('*.json')))} result files")

def get_years_in_data(simulations, output_base_dir):
    """Get unique years present across all simulations"""
    years = set()
    for sim in simulations:
        sim_dir = Path(output_base_dir) / sim / 'pnl_results'
        sector_daily_path = sim_dir / 'sector_daily_pnl.csv'
        if not sector_daily_path.exists():
            print(f"Warning: sector_daily_pnl.csv not found for '{sim}', skipping year detection")
            continue
        try:
            df = pd.read_csv(sector_daily_path, parse_dates=['date'])
            years.update(int(y) for y in df['date'].dt.year.unique())
        except Exception as e:
            print(f"Error reading data for '{sim}': {e}")
    if not years:
        # Fallback: assume recent years
        print("Warning: No years detected, using default range 2022-2026")
        years = {2022, 2023, 2024, 2025, 2026}
    return sorted(years)

def run_comparison_for_year(simulations, output_base_dir, comparison_dir, year=None):
    """Run comparison for a specific year (or all years if year is None)"""
    # Adjust comparison directory name if year is specified
    if year is not None:
        comparison_dir = f"{comparison_dir}_{year}"

    # Load data for each simulation with year filter
    sector_daily_dict = {}
    sector_summary_dict = {}
    daily_total_dict = {}
    bizsector_daily_dict = {}
    bizsector_summary_dict = {}

    for sim in simulations:
        print(f"Loading data for simulation '{sim}'...")
        sector_daily, sector_summary, daily_total, bizsector_daily, bizsector_summary = load_simulation_data(sim, output_base_dir, year)

        if sector_daily is not None:
            sector_daily_dict[sim] = sector_daily
            sector_summary_dict[sim] = sector_summary
            daily_total_dict[sim] = daily_total
            # Store bizsector data if available (may be None)
            if bizsector_daily is not None:
                bizsector_daily_dict[sim] = bizsector_daily
                bizsector_summary_dict[sim] = bizsector_summary
        else:
            print(f"  Warning: Could not load data for '{sim}', skipping")

    if len(sector_daily_dict) < 2:
        print(f"\nERROR: Need at least 2 simulations with valid data to compare")
        print(f"Successfully loaded {len(sector_daily_dict)} simulation(s)")
        return False

    print(f"\nSuccessfully loaded data for {len(sector_daily_dict)} simulation(s)")

    # Calculate comparison metrics
    print("\nCalculating comparison metrics...")
    comparison_results = calculate_comparison_metrics(
        sector_daily_dict, sector_summary_dict, daily_total_dict,
        bizsector_daily_dict, bizsector_summary_dict
    )

    # Generate visualizations
    comparison_output_dir = Path(output_base_dir) / comparison_dir
    generate_comparison_visualizations(comparison_results, list(sector_daily_dict.keys()), sector_daily_dict, comparison_output_dir, year)

    # Save results
    save_comparison_results(comparison_results, comparison_output_dir)

    print(f"\nComparison results saved to: {comparison_output_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description='Compare P&L analysis results across multiple simulations')
    parser.add_argument('simulations', nargs='+',
                        help='Simulation names to compare (e.g., TWOFISH BLOWFISH or TWOFISH,BLOWFISH)')
    parser.add_argument('--output-base-dir', '-o', default='outputs',
                        help='Base output directory containing simulation results (default: outputs)')
    parser.add_argument('--comparison-dir', '-c', default='comparison',
                        help='Directory to save comparison results (default: outputs/comparison)')
    parser.add_argument('--year', '-y', type=int, default=None,
                        help='Filter data to specific year (e.g., 2022). If not provided, uses all years')
    parser.add_argument('--all-years', action='store_true',
                        help='Generate separate comparison reports for each year present in data')

    args = parser.parse_args()

    # Process simulations: support comma-separated list in addition to space-separated
    simulations = []
    for sim in args.simulations:
        if ',' in sim:
            simulations.extend([s.strip() for s in sim.split(',') if s.strip()])
        else:
            simulations.append(sim.strip())
    args.simulations = simulations

    print("="*60)
    print("COMPARING SIMULATION RESULTS")
    print("="*60)
    print(f"Simulations to compare: {', '.join(args.simulations)}")
    print(f"Results directory: {args.output_base_dir}")
    print(f"Comparison output: {args.comparison_dir}")
    if args.year is not None:
        print(f"Year filter: {args.year}")
    if args.all_years:
        print("Generating separate reports for each year")
    print()

    # Handle different year modes
    if args.year is not None:
        # Single year comparison
        run_comparison_for_year(args.simulations, args.output_base_dir, args.comparison_dir, args.year)
    elif args.all_years:
        # Generate separate comparisons for each year
        years = get_years_in_data(args.simulations, args.output_base_dir)
        print(f"Found years in data: {years}")
        for year in years:
            print(f"\n{'='*60}")
            print(f"COMPARISON FOR YEAR {year}")
            print(f"{'='*60}")
            run_comparison_for_year(args.simulations, args.output_base_dir, args.comparison_dir, year)
        print(f"\n{'='*60}")
        print("ALL YEARLY COMPARISONS COMPLETE")
        print(f"{'='*60}")
    else:
        # Default: compare all years combined
        run_comparison_for_year(args.simulations, args.output_base_dir, args.comparison_dir, year=None)

if __name__ == '__main__':
    main()