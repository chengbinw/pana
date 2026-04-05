#!/bin/bash

# Financial Position Analysis Pipeline Runner
# This script runs the complete analysis pipeline for one or more simulations
# Usage:
#   ./run_analysis.sh                         # Run default simulation (TWOFISH)
#   ./run_analysis.sh TWOFISH                 # Run specific simulation
#   ./run_analysis.sh TWOFISH BLOWFISH        # Run multiple simulations
#   ./run_analysis.sh TWOFISH BLOWFISH BYE    # Run multiple simulations (3+)
#   ./run_analysis.sh TWOFISH BLOWFISH --compare  # Run multiple and compare
#   ./run_analysis.sh TWOFISH BLOWFISH BYE --compare  # Run multiple and compare (3+)
#   ./run_analysis.sh --help                  # Show help

set -e  # Exit on any error

# Default values
SIMULATIONS=("TWOFISH")
COMPARE_MODE=false
YEAR=""
ALL_YEARS=false
POS_DIR="pos"
POS_DIR_BASE=""
OUTPUT_BASE_DIR="outputs"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Financial Position Analysis Pipeline"
            echo "Usage: $0 [SIMULATION...] [--compare] [--year YEAR] [--all-years] [--pos-dir DIR] [--pos-dir-base DIR] [--output-dir DIR]"
            echo ""
            echo "Arguments:"
            echo "  SIMULATION...    One or more simulation names, comma-separated or space-separated (default: TWOFISH)"
            echo "  --compare        Run comparison after analyzing all simulations"
            echo "  --year YEAR      Filter comparison to specific year (e.g., 2022)"
            echo "  --all-years      Generate separate comparison reports for each year"
            echo "  --pos-dir DIR    Directory containing position files (default: pos)"
            echo "  --pos-dir-base DIR Base directory with simulation subdirectories"
            echo "                   (if set, uses DIR/SIMULATION/pos for each simulation)"
            echo "  --output-dir DIR Base output directory (default: outputs)"
            echo "  --help, -h       Show this help message"
            exit 0
            ;;
        --compare)
            COMPARE_MODE=true
            shift
            ;;
        --year)
            YEAR="$2"
            shift 2
            ;;
        --all-years)
            ALL_YEARS=true
            shift
            ;;
        --pos-dir)
            POS_DIR="$2"
            shift 2
            ;;
        --pos-dir-base)
            POS_DIR_BASE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_BASE_DIR="$2"
            shift 2
            ;;
        -*)
            echo "Error: Unknown option $1"
            echo "Use --help for usage information"
            exit 1
            ;;
        *)
            # Assume it's a simulation name - support comma-separated list
            IFS=',' read -ra sim_parts <<< "$1"
            for sim_part in "${sim_parts[@]}"; do
                # Trim whitespace
                sim_clean=$(echo "$sim_part" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
                if [ -n "$sim_clean" ]; then
                    SIMULATIONS+=("$sim_clean")
                fi
            done
            shift
            ;;
    esac
done

# Remove the default TWOFISH if user provided simulations
if [ ${#SIMULATIONS[@]} -gt 1 ]; then
    SIMULATIONS=("${SIMULATIONS[@]:1}")
fi

echo "========================================"
echo "Financial Position Analysis Pipeline"
echo "========================================"
echo "Starting at: $(date)"
echo ""
echo "Configuration:"
echo "  Simulations: ${SIMULATIONS[*]}"
if [ -n "$POS_DIR_BASE" ]; then
    echo "  Position directory base: $POS_DIR_BASE (simulation subdirectories: BASE/SIM/pos)"
else
    echo "  Position directory: $POS_DIR"
fi
echo "  Output directory: $OUTPUT_BASE_DIR"
echo "  Compare mode: $COMPARE_MODE"
if [ -n "$YEAR" ]; then
    echo "  Year filter: $YEAR"
fi
if [ "$ALL_YEARS" = true ]; then
    echo "  All years: true (separate reports per year)"
fi
echo ""

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "ERROR: Python is not installed or not in PATH"
    echo "Please install Python 3.6 or higher"
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

# Check if required packages are installed
echo "Checking for required Python packages..."
python -c "import pandas, numpy, matplotlib, seaborn, pathlib" && \
    echo "✓ All required packages are installed" || {
    echo "ERROR: Missing required Python packages"
    echo "Please install with: pip install pandas numpy matplotlib seaborn"
    exit 1
}

# Create output base directory
mkdir -p "$OUTPUT_BASE_DIR"

# Function to run pipeline for a single simulation
run_simulation_pipeline() {
    local sim="$1"
    local pos_dir="$2"
    local output_base_dir="$3"

    echo ""
    echo "========================================"
    echo "Analyzing simulation: $sim"
    echo "========================================"

    # Step 1: Combine data
    echo ""
    echo "Step 1: Combining position files with industry data"
    echo "----------------------------------------"

    # Check if output already exists
    local sim_output_dir="$output_base_dir/$sim"
    local combined_file="$sim_output_dir/combined_positions_with_industry.csv"

    if [ -f "$combined_file" ]; then
        echo "Note: Combined data already exists for $sim"
        echo "It will be overwritten with new data"
        read -p "Continue? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping $sim"
            return 1
        fi
    fi

    echo "Running combine_data.py for $sim..."
    python combine_data.py --simulation "$sim" --pos-dir "$pos_dir" --output-dir "$output_base_dir"
    if [ $? -ne 0 ]; then
        echo "ERROR: combine_data.py failed for $sim"
        return 1
    fi

    # Step 2: P&L Analysis
    echo ""
    echo "Step 2: Calculating P&L by sector and generating visualizations"
    echo "----------------------------------------"

    local plots_dir="$sim_output_dir/pnl_plots"
    local results_dir="$sim_output_dir/pnl_results"

    if [ -d "$plots_dir" ] || [ -d "$results_dir" ]; then
        echo "Note: Previous analysis results exist for $sim"
        echo "They will be overwritten with new results"
        read -p "Continue? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping P&L analysis for $sim"
            return 1
        fi
    fi

    echo "Running pnl_analysis.py for $sim..."
    python pnl_analysis.py --simulation "$sim" --output-dir "$output_base_dir"
    if [ $? -ne 0 ]; then
        echo "ERROR: pnl_analysis.py failed for $sim"
        return 1
    fi

    # Step 3: Generate reports
    echo ""
    echo "Step 3: Generating comprehensive reports"
    echo "----------------------------------------"

    local report_md="${sim}_analysis_report.md"
    local report_html="${sim}_analysis_report.html"

    if [ -f "$report_md" ] || [ -f "$report_html" ]; then
        echo "Note: Previous reports exist for $sim"
        echo "They will be overwritten with new reports"
        read -p "Continue? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping report generation for $sim"
            return 1
        fi
    fi

    echo "Running generate_report.py for $sim..."
    python generate_report.py --simulation "$sim" --output-dir "$output_base_dir"
    if [ $? -ne 0 ]; then
        echo "ERROR: generate_report.py failed for $sim"
        return 1
    fi

    echo ""
    echo "✓ Completed analysis for $sim"
    echo "  Output directory: $sim_output_dir"
    echo "  Report: ${sim}_analysis_report.{md,html}"
    return 0
}

# Run pipeline for each simulation
echo ""
echo "========================================"
echo "Starting analysis for ${#SIMULATIONS[@]} simulation(s)"
echo "========================================"

FAILED_SIMS=()
for sim in "${SIMULATIONS[@]}"; do
    # Determine position directory based on POS_DIR_BASE
    if [ -n "$POS_DIR_BASE" ]; then
        sim_pos_dir="$POS_DIR_BASE/$sim/pos"
    else
        sim_pos_dir="$POS_DIR"
    fi

    echo "Processing simulation '$sim' using position directory: $sim_pos_dir"

    if run_simulation_pipeline "$sim" "$sim_pos_dir" "$OUTPUT_BASE_DIR"; then
        echo "✓ Successfully analyzed $sim"
    else
        echo "✗ Failed to analyze $sim"
        FAILED_SIMS+=("$sim")
    fi
done

# Run comparison if requested and at least 2 simulations succeeded
if [ "$COMPARE_MODE" = true ]; then
    echo ""
    echo "========================================"
    echo "Running comparison analysis"
    echo "========================================"

    # Count successful simulations
    SUCCESSFUL_SIMS=()
    for sim in "${SIMULATIONS[@]}"; do
        if [[ ! " ${FAILED_SIMS[*]} " =~ " ${sim} " ]]; then
            SUCCESSFUL_SIMS+=("$sim")
        fi
    done

    if [ ${#SUCCESSFUL_SIMS[@]} -lt 2 ]; then
        echo "Warning: Need at least 2 successful simulations for comparison"
        echo "Skipping comparison (failed simulations: ${FAILED_SIMS[*]})"
    else
        echo "Comparing simulations: ${SUCCESSFUL_SIMS[*]}"

        # Function to run comparison for a specific year
        run_comparison_for_year() {
            local year="$1"
            local year_suffix="$2"
            local comparison_dir="$OUTPUT_BASE_DIR/comparison$year_suffix"

            echo "  Year: $year"
            echo "  Comparison directory: $comparison_dir"

            # Run comparison
            if [ -n "$year" ] && [ "$year" != "all" ]; then
                python compare_simulations.py "${SUCCESSFUL_SIMS[@]}" --output-base-dir "$OUTPUT_BASE_DIR" --year "$year"
            else
                python compare_simulations.py "${SUCCESSFUL_SIMS[@]}" --output-base-dir "$OUTPUT_BASE_DIR"
            fi

            if [ $? -ne 0 ]; then
                echo "  ERROR: compare_simulations.py failed for year $year"
                return 1
            fi

            # Generate comparison report
            python generate_comparison_report.py --comparison-dir "$comparison_dir" --output-dir "$comparison_dir"
            if [ $? -ne 0 ]; then
                echo "  ERROR: generate_comparison_report.py failed for year $year"
                return 1
            fi

            echo "  ✓ Comparison completed for year $year"
            echo "    Report: $comparison_dir/comparison_report.{md,html}"
            return 0
        }

        # Determine which years to compare
        if [ "$ALL_YEARS" = true ]; then
            echo "Running separate comparisons for each year..."
            # Get years from data (we'll run compare_simulations.py with --all-years)
            # compare_simulations.py --all-years will handle year detection and separate comparisons
            python compare_simulations.py "${SUCCESSFUL_SIMS[@]}" --output-base-dir "$OUTPUT_BASE_DIR" --all-years
            if [ $? -ne 0 ]; then
                echo "ERROR: compare_simulations.py failed for all-years mode"
            else
                echo "✓ All-years comparison completed"
                # Generate reports for each year
                # Note: compare_simulations.py with --all-years creates directories but doesn't generate reports
                # We need to generate reports for each year directory
                # Enable nullglob to handle case where no comparison_* directories exist
                shopt -s nullglob
                year_dirs=("$OUTPUT_BASE_DIR"/comparison_*)
                shopt -u nullglob

                if [ ${#year_dirs[@]} -eq 0 ]; then
                    echo "  Warning: No year comparison directories found"
                else
                    for year_dir in "${year_dirs[@]}"; do
                        # Extract year from directory name (comparison_2022 -> 2022)
                        year=$(basename "$year_dir" | sed 's/comparison_//')
                        echo "  Generating report for year $year..."
                        python generate_comparison_report.py --comparison-dir "$year_dir" --output-dir "$year_dir"
                        if [ $? -ne 0 ]; then
                            echo "    ERROR: generate_comparison_report.py failed for year $year"
                        else
                            echo "    ✓ Report generated for year $year"
                        fi
                    done
                fi
            fi
        else
            # Single year comparison (either specific year or all years combined)
            if [ -n "$YEAR" ]; then
                # Specific year
                run_comparison_for_year "$YEAR" "_$YEAR"
            else
                # All years combined (default)
                run_comparison_for_year "all" ""
            fi
        fi
    fi
fi

# Summary
echo ""
echo "========================================"
echo "Pipeline completed!"
echo "========================================"
echo "Summary:"
echo "  Total simulations: ${#SIMULATIONS[@]}"
echo "  Successful: $((${#SIMULATIONS[@]} - ${#FAILED_SIMS[@]}))"
echo "  Failed: ${#FAILED_SIMS[@]}"
if [ ${#FAILED_SIMS[@]} -gt 0 ]; then
    echo "  Failed simulations: ${FAILED_SIMS[*]}"
fi

echo ""
echo "Output structure:"
echo "  $OUTPUT_BASE_DIR/"
for sim in "${SIMULATIONS[@]}"; do
    if [[ ! " ${FAILED_SIMS[*]} " =~ " ${sim} " ]]; then
        echo "    ├── $sim/"
        echo "    │   ├── combined_positions_with_industry.csv"
        echo "    │   ├── pnl_results/"
        echo "    │   ├── pnl_plots/"
        echo "    │   └── ${sim}_analysis_report.{md,html}"
    fi
done
if [ "$COMPARE_MODE" = true ] && [ ${#SUCCESSFUL_SIMS[@]} -ge 2 ]; then
    # Determine which comparison directories were created
    if [ "$ALL_YEARS" = true ]; then
        # Show each year directory that exists (pattern comparison_*)
        # Enable nullglob to handle case where no comparison_* directories exist
        shopt -s nullglob
        year_dirs=("$OUTPUT_BASE_DIR"/comparison_*)
        shopt -u nullglob

        years_shown=false
        for year_dir in "${year_dirs[@]}"; do
            # Extract year from directory name
            year=$(basename "$year_dir" | sed 's/comparison_//')
            if [ "$years_shown" = false ]; then
                echo "    └── comparison_$year/"
                echo "        ├── comparison_plots/"
                echo "        ├── comparison_data/"
                echo "        └── comparison_report.{md,html}"
                years_shown=true
            else
                echo "    ├── comparison_$year/"
                echo "    │   ├── comparison_plots/"
                echo "    │   ├── comparison_data/"
                echo "    │   └── comparison_report.{md,html}"
            fi
        done
        # If no year directories exist (shouldn't happen), show default
        if [ "$years_shown" = false ]; then
            echo "    └── comparison/"
            echo "        ├── comparison_plots/"
            echo "        ├── comparison_data/"
            echo "        └── comparison_report.{md,html}"
        fi
    elif [ -n "$YEAR" ]; then
        # Specific year comparison
        echo "    └── comparison_$YEAR/"
        echo "        ├── comparison_plots/"
        echo "        ├── comparison_data/"
        echo "        └── comparison_report.{md,html}"
    else
        # Default comparison (all years combined)
        echo "    └── comparison/"
        echo "        ├── comparison_plots/"
        echo "        ├── comparison_data/"
        echo "        └── comparison_report.{md,html}"
    fi
fi

echo ""
echo "Completed at: $(date)"
echo "========================================"

# Exit with error if any simulations failed
if [ ${#FAILED_SIMS[@]} -gt 0 ]; then
    exit 1
fi