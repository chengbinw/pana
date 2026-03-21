import pandas as pd
import numpy as np
import os
import re
import argparse
from pathlib import Path

def extract_date_from_filename(filename, simulation='TWOFISH'):
    """Extract date from filename pattern: ePos_{simulation}_YYYYMMDD_EOD.csv"""
    # Escape simulation name for regex (in case it contains special characters)
    sim_escaped = re.escape(simulation)
    pattern = fr'ePos_{sim_escaped}_(\d{{8}})_EOD\.csv$'
    match = re.search(pattern, filename)
    if match:
        date_str = match.group(1)
        # Convert to datetime
        return pd.to_datetime(date_str, format='%Y%m%d')
    return None

def combine_position_files(pos_dir='pos', simulation='TWOFISH'):
    """Combine all position CSV files in directory for given simulation"""
    pos_path = Path(pos_dir)
    all_data = []

    # Try different filename prefixes to find position files
    prefixes_to_try = [simulation]
    if simulation != 'TWOFISH':
        prefixes_to_try.append('TWOFISH')

    pos_files = []
    prefix_used = None

    for prefix in prefixes_to_try:
        pos_files = list(pos_path.glob(f'ePos_{prefix}_*.csv'))
        if pos_files:
            prefix_used = prefix
            print(f"Found {len(pos_files)} position files using prefix '{prefix}'")
            break

    if not pos_files:
        print(f"Found 0 position files for simulation '{simulation}' (tried prefixes: {', '.join(prefixes_to_try)})")
        print("No data loaded")
        return None

    print(f"Using filename prefix: {prefix_used}")

    for i, file_path in enumerate(pos_files):
        if i % 50 == 0:
            print(f"Processing file {i+1}/{len(pos_files)}: {file_path.name}")

        # Extract date from filename using the actual prefix found
        date = extract_date_from_filename(file_path.name, prefix_used)
        if date is None:
            print(f"Warning: Could not extract date from {file_path.name}")
            continue

        try:
            # Read CSV file
            df = pd.read_csv(file_path)

            # Add date column
            df['date'] = date

            # Add filename for reference
            df['filename'] = file_path.name

            all_data.append(df)
        except Exception as e:
            print(f"Error reading {file_path.name}: {e}")

    if not all_data:
        print("No data loaded")
        return None

    # Combine all DataFrames
    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Combined data shape: {combined_df.shape}")

    return combined_df

def load_industry_data(industry_path='pos'):
    """Load industry mapping data

    Args:
        industry_path: Path to industry CSV file, or directory containing Industry.csv
    """
    industry_path = Path(industry_path)
    if industry_path.is_dir():
        industry_path = industry_path / 'Industry.csv'

    if not industry_path.exists():
        print(f"Industry file not found at {industry_path}")
        # Try alternative locations
        alternative_paths = [
            Path('Industry.csv'),           # Current directory
            Path('pos/Industry.csv'),       # pos subdirectory
            Path('../Industry.csv'),        # Parent directory
        ]

        for alt_path in alternative_paths:
            if alt_path.exists():
                industry_path = alt_path
                print(f"  Found industry file at alternative location: {industry_path}")
                break
        else:
            print(f"Industry file not found. Also tried:")
            for alt_path in alternative_paths:
                print(f"  - {alt_path}")
            return None

    industry_df = pd.read_csv(industry_path)
    print(f"Industry data shape: {industry_df.shape}")

    # Create sector code from first 2 digits of industry code
    industry_df['sector_code'] = industry_df['newIndustry'].astype(str).str[:2]

    # Map common sector codes based on user info (50 = energy)
    sector_map = {
        '50': 'Energy',
        '51': 'Materials',
        '52': 'Industrials',
        '53': 'Consumer Discretionary',
        '54': 'Consumer Staples',
        '55': 'Financials',
        '56': 'Health Care',
        '57': 'Information Technology',
        '58': 'Communication Services',
        '59': 'Utilities',
        '60': 'Real Estate'
    }

    industry_df['sector'] = industry_df['sector_code'].map(sector_map)
    industry_df['sector'] = industry_df['sector'].fillna('Other')

    return industry_df

def merge_with_industry(position_df, industry_df):
    """Merge position data with industry information"""
    if position_df is None or industry_df is None:
        return None

    # Merge on RSymbol (position) and symbol (industry)
    # Note: Need to check column names
    print("Position columns:", position_df.columns.tolist())
    print("Industry columns:", industry_df.columns.tolist())

    # Check which column contains the symbol in position data
    # Based on sample data, it looks like 'RSymbol' contains symbols like 'A.N', 'AAPL.O'
    merged_df = pd.merge(
        position_df,
        industry_df,
        left_on='RSymbol',
        right_on='symbol',
        how='left'
    )

    print(f"Merged data shape: {merged_df.shape}")
    print(f"Rows without industry match: {merged_df['symbol'].isna().sum()}")

    return merged_df

def main():
    parser = argparse.ArgumentParser(description='Combine position files with industry data')
    parser.add_argument('--simulation', '-s', default='TWOFISH',
                        help='Simulation name (default: TWOFISH)')
    parser.add_argument('--pos-dir', '-p', default='pos',
                        help='Directory containing position files (default: pos)')
    parser.add_argument('--output-dir', '-o', default='outputs',
                        help='Base output directory (default: outputs)')
    parser.add_argument('--industry-file',
                        help='Path to industry mapping CSV (default: pos_dir/Industry.csv)')

    args = parser.parse_args()

    # Create simulation-specific output directory
    sim_output_dir = Path(args.output_dir) / args.simulation
    sim_output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"COMBINING POSITION DATA FOR SIMULATION: {args.simulation}")
    print("=" * 60)

    print(f"\nStep 1: Combining position files...")
    position_df = combine_position_files(args.pos_dir, args.simulation)

    print(f"\nStep 2: Loading industry data...")
    industry_path = args.industry_file if args.industry_file else Path(args.pos_dir) / 'Industry.csv'
    industry_df = load_industry_data(industry_path)

    print(f"\nStep 3: Merging data...")
    merged_df = merge_with_industry(position_df, industry_df)

    if merged_df is not None:
        # Save to CSV in simulation output directory
        output_path = sim_output_dir / 'combined_positions_with_industry.csv'
        merged_df.to_csv(output_path, index=False)
        print(f"\nSaved combined data to: {output_path}")


        # Basic statistics
        print("\n=== Basic Statistics ===")
        print(f"Total rows: {len(merged_df)}")
        print(f"Date range: {merged_df['date'].min()} to {merged_df['date'].max()}")
        print(f"Unique symbols: {merged_df['RSymbol'].nunique()}")
        print(f"Unique sectors: {merged_df['sector'].nunique()}")

        # Show sector distribution
        if 'sector' in merged_df.columns:
            sector_counts = merged_df['sector'].value_counts()
            print("\nSector distribution:")
            for sector, count in sector_counts.items():
                print(f"  {sector}: {count} rows")

    return merged_df

if __name__ == '__main__':
    main()