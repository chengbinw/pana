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

def load_combined_data(data_path=None):
    """Load the combined positions data"""
    if data_path is None:
        data_path = Path('combined_positions_with_industry.csv')
    else:
        data_path = Path(data_path)

    if not data_path.exists():
        print(f"Combined data file not found at {data_path}. Run combine_data.py first.")
        return None

    print(f"Loading combined data from {data_path}...")
    df = pd.read_csv(data_path, parse_dates=['date'])
    print(f"Data shape: {df.shape}")
    return df

def calculate_sector_pnl(df):
    """Calculate daily P&L by sector"""
    # Group by date and sector
    sector_daily = df.groupby(['date', 'sector']).agg({
        'pl': 'sum',  # Total P&L
        'Quantity': 'sum',  # Net quantity
        'RSymbol': 'nunique',  # Number of unique symbols
        'Mark': 'mean',  # Average mark price (weighted?)
        'CMark': 'mean'  # Average cost mark
    }).reset_index()

    # Calculate additional metrics
    sector_daily = sector_daily.rename(columns={
        'RSymbol': 'symbol_count',
        'pl': 'total_pnl'
    })

    # Calculate absolute exposure (Mark * Quantity)
    # Note: Need to handle at position level then aggregate
    df['exposure'] = df['Mark'] * df['Quantity']
    exposure_by_sector = df.groupby(['date', 'sector'])['exposure'].sum().reset_index()
    exposure_by_sector = exposure_by_sector.rename(columns={'exposure': 'total_exposure'})

    # Merge exposure back
    sector_daily = pd.merge(sector_daily, exposure_by_sector, on=['date', 'sector'], how='left')

    # Calculate P&L as percentage of exposure (avoid division by zero)
    sector_daily['pnl_pct'] = np.where(
        sector_daily['total_exposure'] != 0,
        sector_daily['total_pnl'] / abs(sector_daily['total_exposure']) * 100,
        0
    )

    return sector_daily

def calculate_bizsector_pnl(df):
    """Calculate daily P&L by bizsector"""
    # Group by date and bizsector
    bizsector_daily = df.groupby(['date', 'bizsector']).agg({
        'pl': 'sum',  # Total P&L
        'Quantity': 'sum',  # Net quantity
        'RSymbol': 'nunique',  # Number of unique symbols
        'Mark': 'mean',  # Average mark price (weighted?)
        'CMark': 'mean'  # Average cost mark
    }).reset_index()

    # Calculate additional metrics
    bizsector_daily = bizsector_daily.rename(columns={
        'RSymbol': 'symbol_count',
        'pl': 'total_pnl'
    })

    # Calculate absolute exposure (Mark * Quantity)
    # Note: Need to handle at position level then aggregate
    df['exposure'] = df['Mark'] * df['Quantity']
    exposure_by_bizsector = df.groupby(['date', 'bizsector'])['exposure'].sum().reset_index()
    exposure_by_bizsector = exposure_by_bizsector.rename(columns={'exposure': 'total_exposure'})

    # Merge exposure back
    bizsector_daily = pd.merge(bizsector_daily, exposure_by_bizsector, on=['date', 'bizsector'], how='left')

    # Calculate P&L as percentage of exposure (avoid division by zero)
    bizsector_daily['pnl_pct'] = np.where(
        bizsector_daily['total_exposure'] != 0,
        bizsector_daily['total_pnl'] / abs(bizsector_daily['total_exposure']) * 100,
        0
    )

    return bizsector_daily

def calculate_cumulative_pnl(sector_daily):
    """Calculate cumulative P&L over time by sector"""
    # Sort by date and sector
    sector_daily = sector_daily.sort_values(['sector', 'date'])

    # Calculate cumulative P&L within each sector
    sector_daily['cumulative_pnl'] = sector_daily.groupby('sector')['total_pnl'].cumsum()

    # Calculate rolling metrics
    sector_daily['rolling_7d_pnl'] = sector_daily.groupby('sector')['total_pnl'].rolling(7, min_periods=1).sum().reset_index(0, drop=True)
    sector_daily['rolling_30d_pnl'] = sector_daily.groupby('sector')['total_pnl'].rolling(30, min_periods=1).sum().reset_index(0, drop=True)

    return sector_daily

def calculate_cumulative_pnl_bizsector(bizsector_daily):
    """Calculate cumulative P&L over time by bizsector"""
    # Sort by date and bizsector
    bizsector_daily = bizsector_daily.sort_values(['bizsector', 'date'])

    # Calculate cumulative P&L within each bizsector
    bizsector_daily['cumulative_pnl'] = bizsector_daily.groupby('bizsector')['total_pnl'].cumsum()

    # Calculate rolling metrics
    bizsector_daily['rolling_7d_pnl'] = bizsector_daily.groupby('bizsector')['total_pnl'].rolling(7, min_periods=1).sum().reset_index(0, drop=True)
    bizsector_daily['rolling_30d_pnl'] = bizsector_daily.groupby('bizsector')['total_pnl'].rolling(30, min_periods=1).sum().reset_index(0, drop=True)

    return bizsector_daily

def generate_summary_statistics(df, sector_daily):
    """Generate summary statistics and insights"""
    print("\n" + "="*60)
    print("P&L ANALYSIS SUMMARY")
    print("="*60)

    # Overall statistics
    total_pnl = df['pl'].sum()
    total_positions = len(df)
    avg_daily_pnl = sector_daily.groupby('date')['total_pnl'].sum().mean()

    print(f"\nOverall Statistics:")
    print(f"  Total P&L across all positions: ${total_pnl:,.2f}")
    print(f"  Average daily P&L: ${avg_daily_pnl:,.2f}")
    print(f"  Total positions analyzed: {total_positions:,}")

    # Sector performance summary
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

    sector_summary = sector_summary.sort_values('total_pnl', ascending=False)

    print(f"\nSector Performance (Total P&L):")
    for _, row in sector_summary.iterrows():
        print(f"  {row['sector']:30} ${row['total_pnl']:12,.2f} (avg exposure: ${row['total_exposure']:,.0f}, Sharpe: {row['sharpe_ratio']:.2f})")

    print(f"\nSector Sharpe Ratios (annualized, risk-free rate=0):")
    sector_summary_sharpe = sector_summary.sort_values('sharpe_ratio', ascending=False)
    for _, row in sector_summary_sharpe.iterrows():
        print(f"  {row['sector']:30} {row['sharpe_ratio']:6.2f}")

    # Best and worst days
    daily_total = sector_daily.groupby('date')['total_pnl'].sum().reset_index()
    best_day = daily_total.loc[daily_total['total_pnl'].idxmax()]
    worst_day = daily_total.loc[daily_total['total_pnl'].idxmin()]

    print(f"\nBest Day: {best_day['date'].date()} - P&L: ${best_day['total_pnl']:,.2f}")
    print(f"Worst Day: {worst_day['date'].date()} - P&L: ${worst_day['total_pnl']:,.2f}")

    # Sector consistency
    sector_volatility = sector_daily.groupby('sector')['total_pnl'].std().reset_index()
    sector_volatility = sector_volatility.rename(columns={'total_pnl': 'pnl_std'})
    sector_volatility = sector_volatility.sort_values('pnl_std')

    print(f"\nSector P&L Volatility (Standard Deviation):")
    for _, row in sector_volatility.iterrows():
        print(f"  {row['sector']:30} ${row['pnl_std']:12,.2f}")

    return sector_summary, daily_total

def generate_bizsector_summary_statistics(df, bizsector_daily):
    """Generate summary statistics and insights for bizsector"""
    print("\n" + "="*60)
    print("P&L ANALYSIS SUMMARY BY BIZSECTOR")
    print("="*60)

    # Overall statistics (same as sector)
    total_pnl = df['pl'].sum()
    total_positions = len(df)
    avg_daily_pnl = bizsector_daily.groupby('date')['total_pnl'].sum().mean()

    print(f"\nOverall Statistics:")
    print(f"  Total P&L across all positions: ${total_pnl:,.2f}")
    print(f"  Average daily P&L: ${avg_daily_pnl:,.2f}")
    print(f"  Total positions analyzed: {total_positions:,}")

    # Bizsector performance summary
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

    bizsector_summary = bizsector_summary.sort_values('total_pnl', ascending=False)

    print(f"\nBizsector Performance (Total P&L):")
    for _, row in bizsector_summary.iterrows():
        print(f"  {row['bizsector']:30} ${row['total_pnl']:12,.2f} (avg exposure: ${row['total_exposure']:,.0f}, Sharpe: {row['sharpe_ratio']:.2f})")

    print(f"\nBizsector Sharpe Ratios (annualized, risk-free rate=0):")
    bizsector_summary_sharpe = bizsector_summary.sort_values('sharpe_ratio', ascending=False)
    for _, row in bizsector_summary_sharpe.iterrows():
        print(f"  {row['bizsector']:30} {row['sharpe_ratio']:6.2f}")

    # Best and worst days (same as sector)
    daily_total = bizsector_daily.groupby('date')['total_pnl'].sum().reset_index()
    best_day = daily_total.loc[daily_total['total_pnl'].idxmax()]
    worst_day = daily_total.loc[daily_total['total_pnl'].idxmin()]

    print(f"\nBest Day: {best_day['date'].date()} - P&L: ${best_day['total_pnl']:,.2f}")
    print(f"Worst Day: {worst_day['date'].date()} - P&L: ${worst_day['total_pnl']:,.2f}")

    # Bizsector consistency
    bizsector_volatility = bizsector_daily.groupby('bizsector')['total_pnl'].std().reset_index()
    bizsector_volatility = bizsector_volatility.rename(columns={'total_pnl': 'pnl_std'})
    bizsector_volatility = bizsector_volatility.sort_values('pnl_std')

    print(f"\nBizsector P&L Volatility (Standard Deviation):")
    for _, row in bizsector_volatility.iterrows():
        print(f"  {row['bizsector']:30} ${row['pnl_std']:12,.2f}")

    return bizsector_summary, daily_total

def create_visualizations(sector_daily, sector_summary, daily_total, simulation='TWOFISH', output_base_dir='outputs'):
    """Create visualizations for P&L analysis"""
    # Create simulation-specific output directory for plots
    output_dir = Path(output_base_dir) / simulation / 'pnl_plots'
    output_dir.mkdir(parents=True, exist_ok=True)
    print("\nGenerating visualizations...")


    # 1. Daily P&L by Sector (Heatmap)
    plt.figure(figsize=(14, 8))
    pivot_data = sector_daily.pivot(index='date', columns='sector', values='total_pnl')

    # Resample to weekly for cleaner heatmap
    pivot_weekly = pivot_data.resample('W').sum()

    plt.imshow(pivot_weekly.T, aspect='auto', cmap='RdYlGn',
               interpolation='nearest', vmin=-100000, vmax=100000)
    plt.colorbar(label='Weekly P&L ($)')
    plt.title(f'Weekly P&L Heatmap by Sector ({simulation})', fontsize=14, fontweight='bold')
    plt.ylabel('Sector')
    plt.xlabel('Week')

    # Set ticks
    plt.yticks(range(len(pivot_weekly.columns)), pivot_weekly.columns, fontsize=9)

    # Show every 4th week on x-axis
    week_indices = range(0, len(pivot_weekly), max(1, len(pivot_weekly)//8))
    plt.xticks(week_indices, [pivot_weekly.index[i].strftime('%Y-%m-%d')
                              for i in week_indices], rotation=45)

    plt.tight_layout()
    plt.savefig(output_dir / 'weekly_pnl_heatmap.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 2. Cumulative P&L by Sector
    plt.figure(figsize=(12, 6))
    for sector in sector_daily['sector'].unique():
        sector_data = sector_daily[sector_daily['sector'] == sector].copy()
        sector_data = sector_data.sort_values('date')
        plt.plot(sector_data['date'], sector_data['cumulative_pnl'],
                label=sector, linewidth=2, alpha=0.8)

    plt.title(f'Cumulative P&L by Sector Over Time ({simulation})', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Cumulative P&L ($)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'cumulative_pnl_by_sector.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 3. Sector Performance Bar Chart
    plt.figure(figsize=(10, 6))
    colors = plt.cm.Set3(np.linspace(0, 1, len(sector_summary)))
    bars = plt.bar(sector_summary['sector'], sector_summary['total_pnl'], color=colors)
    plt.title(f'Total P&L by Sector ({simulation})', fontsize=14, fontweight='bold')
    plt.xlabel('Sector')
    plt.ylabel('Total P&L ($)')
    plt.xticks(rotation=45, ha='right')

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'${height:,.0f}', ha='center', va='bottom' if height >= 0 else 'top',
                fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / 'total_pnl_by_sector.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 4. Daily Total P&L
    plt.figure(figsize=(12, 6))
    plt.plot(daily_total['date'], daily_total['total_pnl'],
             color='steelblue', linewidth=2, alpha=0.8)
    plt.fill_between(daily_total['date'], daily_total['total_pnl'],
                     where=daily_total['total_pnl'] >= 0, color='green', alpha=0.3)
    plt.fill_between(daily_total['date'], daily_total['total_pnl'],
                     where=daily_total['total_pnl'] < 0, color='red', alpha=0.3)

    plt.title(f'Daily Total P&L ({simulation})', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Daily P&L ($)')
    plt.grid(True, alpha=0.3)

    # Add horizontal line at y=0
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(output_dir / 'daily_total_pnl.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 5. Sector Exposure Over Time
    plt.figure(figsize=(12, 6))
    for sector in sector_daily['sector'].unique():
        sector_data = sector_daily[sector_daily['sector'] == sector].copy()
        sector_data = sector_data.sort_values('date')
        plt.plot(sector_data['date'], abs(sector_data['total_exposure']),
                label=sector, linewidth=2, alpha=0.7)

    plt.title(f'Sector Exposure (Absolute) Over Time ({simulation})', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Total Exposure ($)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.yscale('log')  # Log scale for better visibility
    plt.tight_layout()
    plt.savefig(output_dir / 'sector_exposure_over_time.png', dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Visualizations saved to '{output_dir}/' directory")

def create_bizsector_visualizations(bizsector_daily, bizsector_summary, daily_total, simulation='TWOFISH', output_base_dir='outputs'):
    """Create visualizations for P&L analysis by bizsector"""
    # Create simulation-specific output directory for bizsector plots
    output_dir = Path(output_base_dir) / simulation / 'bizsector_plots'
    output_dir.mkdir(parents=True, exist_ok=True)
    print("\nGenerating bizsector visualizations...")


    # 1. Daily P&L by Bizsector (Heatmap)
    plt.figure(figsize=(14, 8))
    pivot_data = bizsector_daily.pivot(index='date', columns='bizsector', values='total_pnl')

    # Resample to weekly for cleaner heatmap
    pivot_weekly = pivot_data.resample('W').sum()

    plt.imshow(pivot_weekly.T, aspect='auto', cmap='RdYlGn',
               interpolation='nearest', vmin=-100000, vmax=100000)
    plt.colorbar(label='Weekly P&L ($)')
    plt.title(f'Weekly P&L Heatmap by Bizsector ({simulation})', fontsize=14, fontweight='bold')
    plt.ylabel('Bizsector')
    plt.xlabel('Week')

    # Set ticks
    plt.yticks(range(len(pivot_weekly.columns)), pivot_weekly.columns, fontsize=9)

    # Show every 4th week on x-axis
    week_indices = range(0, len(pivot_weekly), max(1, len(pivot_weekly)//8))
    plt.xticks(week_indices, [pivot_weekly.index[i].strftime('%Y-%m-%d')
                              for i in week_indices], rotation=45)

    plt.tight_layout()
    plt.savefig(output_dir / 'weekly_pnl_heatmap_bizsector.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 2. Cumulative P&L by Bizsector
    plt.figure(figsize=(12, 6))
    for bizsector in bizsector_daily['bizsector'].unique():
        bizsector_data = bizsector_daily[bizsector_daily['bizsector'] == bizsector].copy()
        bizsector_data = bizsector_data.sort_values('date')
        plt.plot(bizsector_data['date'], bizsector_data['cumulative_pnl'],
                label=bizsector, linewidth=2, alpha=0.8)

    plt.title(f'Cumulative P&L by Bizsector Over Time ({simulation})', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Cumulative P&L ($)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'cumulative_pnl_by_bizsector.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 3. Bizsector Performance Bar Chart
    plt.figure(figsize=(10, 6))
    colors = plt.cm.Set3(np.linspace(0, 1, len(bizsector_summary)))
    bars = plt.bar(bizsector_summary['bizsector'], bizsector_summary['total_pnl'], color=colors)
    plt.title(f'Total P&L by Bizsector ({simulation})', fontsize=14, fontweight='bold')
    plt.xlabel('Bizsector')
    plt.ylabel('Total P&L ($)')
    plt.xticks(rotation=45, ha='right')

    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'${height:,.0f}', ha='center', va='bottom' if height >= 0 else 'top',
                fontsize=9)

    plt.tight_layout()
    plt.savefig(output_dir / 'total_pnl_by_bizsector.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 4. Daily Total P&L (same as sector)
    plt.figure(figsize=(12, 6))
    plt.plot(daily_total['date'], daily_total['total_pnl'],
             color='steelblue', linewidth=2, alpha=0.8)
    plt.fill_between(daily_total['date'], daily_total['total_pnl'],
                     where=daily_total['total_pnl'] >= 0, color='green', alpha=0.3)
    plt.fill_between(daily_total['date'], daily_total['total_pnl'],
                     where=daily_total['total_pnl'] < 0, color='red', alpha=0.3)

    plt.title(f'Daily Total P&L ({simulation})', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Daily P&L ($)')
    plt.grid(True, alpha=0.3)

    # Add horizontal line at y=0
    plt.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    plt.tight_layout()
    plt.savefig(output_dir / 'daily_total_pnl.png', dpi=150, bbox_inches='tight')
    plt.close()

    # 5. Bizsector Exposure Over Time
    plt.figure(figsize=(12, 6))
    for bizsector in bizsector_daily['bizsector'].unique():
        bizsector_data = bizsector_daily[bizsector_daily['bizsector'] == bizsector].copy()
        bizsector_data = bizsector_data.sort_values('date')
        plt.plot(bizsector_data['date'], abs(bizsector_data['total_exposure']),
                label=bizsector, linewidth=2, alpha=0.7)

    plt.title(f'Bizsector Exposure (Absolute) Over Time ({simulation})', fontsize=14, fontweight='bold')
    plt.xlabel('Date')
    plt.ylabel('Total Exposure ($)')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3)
    plt.yscale('log')  # Log scale for better visibility
    plt.tight_layout()
    plt.savefig(output_dir / 'bizsector_exposure_over_time.png', dpi=150, bbox_inches='tight')
    plt.close()

    print(f"Bizsector visualizations saved to '{output_dir}/' directory")

def save_results(sector_daily, sector_summary, daily_total, simulation='TWOFISH', output_base_dir='outputs'):
    """Save analysis results to CSV files"""
    output_dir = Path(output_base_dir) / simulation / 'pnl_results'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save sector daily data
    sector_daily.to_csv(output_dir / 'sector_daily_pnl.csv', index=False)

    # Save sector summary
    sector_summary.to_csv(output_dir / 'sector_summary.csv', index=False)

    # Save daily total
    daily_total.to_csv(output_dir / 'daily_total_pnl.csv', index=False)

    print(f"\nAnalysis results saved to '{output_dir}/' directory:")

def save_bizsector_results(bizsector_daily, bizsector_summary, daily_total, simulation='TWOFISH', output_base_dir='outputs'):
    """Save bizsector analysis results to CSV files"""
    output_dir = Path(output_base_dir) / simulation / 'pnl_results'
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save bizsector daily data
    bizsector_daily.to_csv(output_dir / 'bizsector_daily_pnl.csv', index=False)

    # Save bizsector summary
    bizsector_summary.to_csv(output_dir / 'bizsector_summary.csv', index=False)

    # Save daily total (same as sector daily total)
    daily_total.to_csv(output_dir / 'daily_total_pnl.csv', index=False)

    print(f"\nBizsector analysis results saved to '{output_dir}/' directory:")

def main():
    parser = argparse.ArgumentParser(description='P&L analysis by sector')
    parser.add_argument('--simulation', '-s', default='TWOFISH',
                        help='Simulation name (default: TWOFISH)')
    parser.add_argument('--input-file', '-i',
                        help='Path to combined positions CSV file (default: outputs/{simulation}/combined_positions_with_industry.csv)')
    parser.add_argument('--output-dir', '-o', default='outputs',
                        help='Base output directory (default: outputs)')

    args = parser.parse_args()

    # Determine input file path
    if args.input_file:
        input_path = args.input_file
    else:
        input_path = Path(args.output_dir) / args.simulation / 'combined_positions_with_industry.csv'

    print("="*60)
    print(f"P&L ANALYSIS BY SECTOR - {args.simulation}")
    print("="*60)

    # Load data
    df = load_combined_data(input_path)
    if df is None:
        # Fallback to legacy location for backward compatibility
        if args.simulation == 'TWOFISH' and args.output_dir == 'outputs':
            print("Trying legacy location: combined_positions_with_industry.csv")
            df = load_combined_data('combined_positions_with_industry.csv')
        if df is None:
            return

    # Calculate sector P&L
    print("\nCalculating sector P&L...")
    sector_daily = calculate_sector_pnl(df)

    # Calculate cumulative metrics
    print("Calculating cumulative metrics...")
    sector_daily = calculate_cumulative_pnl(sector_daily)

    # Generate summary statistics
    sector_summary, daily_total = generate_summary_statistics(df, sector_daily)

    # Create visualizations
    create_visualizations(sector_daily, sector_summary, daily_total,
                          simulation=args.simulation, output_base_dir=args.output_dir)

    # Save results
    save_results(sector_daily, sector_summary, daily_total,
                 simulation=args.simulation, output_base_dir=args.output_dir)

    # Calculate bizsector P&L
    print("\n" + "="*60)
    print(f"P&L ANALYSIS BY BIZSECTOR - {args.simulation}")
    print("="*60)

    print("\nCalculating bizsector P&L...")
    bizsector_daily = calculate_bizsector_pnl(df)

    print("Calculating cumulative metrics...")
    bizsector_daily = calculate_cumulative_pnl_bizsector(bizsector_daily)

    print("Generating summary statistics...")
    bizsector_summary, daily_total_biz = generate_bizsector_summary_statistics(df, bizsector_daily)

    # Create bizsector visualizations
    create_bizsector_visualizations(bizsector_daily, bizsector_summary, daily_total_biz,
                                  simulation=args.simulation, output_base_dir=args.output_dir)

    # Save bizsector results
    save_bizsector_results(bizsector_daily, bizsector_summary, daily_total_biz,
                          simulation=args.simulation, output_base_dir=args.output_dir)

    print("\n" + "="*60)
    print(f"ANALYSIS COMPLETE FOR {args.simulation}")
    print("="*60)

if __name__ == '__main__':
    main()