#!/bin/bash

# Financial Position Analysis Pipeline Runner (Auto mode)
# This script runs the complete analysis pipeline for one or more simulations without prompts
# Usage:
#   ./run_analysis_auto.sh                         Run default simulation (TWOFISH)
#   ./run_analysis_auto.sh TWOFISH                 Run specific simulation
#   ./run_analysis_auto.sh TWOFISH BLOWFISH        Run multiple simulations
#   ./run_analysis_auto.sh TWOFISH BLOWFISH --compare  Run multiple and compare
#   ./run_analysis_auto.sh --help                  Show help

set -e  # Exit on any error

# Default values
SIMULATIONS=("TWOFISH")
COMPARE_MODE=false
POS_DIR="pos"
POS_DIR_BASE=""
OUTPUT_BASE_DIR="outputs"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            echo "Financial Position Analysis Pipeline (Auto Mode)"
            echo "Usage: $0 [SIMULATION...] [--compare] [--pos-dir DIR] [--pos-dir-base DIR] [--output-dir DIR]"
            echo ""
            echo "Arguments:"
            echo "  SIMULATION...    One or more simulation names (default: TWOFISH)"
            echo "  --compare        Run comparison after analyzing all simulations"
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
            # Assume it's a simulation name
            SIMULATIONS+=("$1")
            shift
            ;;
    esac
done

# Remove the default TWOFISH if user provided simulations
if [ ${#SIMULATIONS[@]} -gt 1 ]; then
    SIMULATIONS=("${SIMULATIONS[@]:1}")
fi

echo "========================================"
echo "Financial Position Analysis Pipeline (Auto Mode)"
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

# Function to run pipeline for a single simulation (auto mode - no prompts)
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

    local sim_output_dir="$output_base_dir/$sim"
    local combined_file="$sim_output_dir/combined_positions_with_industry.csv"

    if [ -f "$combined_file" ]; then
        echo "Note: Overwriting existing combined data for $sim"
        rm -f "$combined_file"
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
        echo "Note: Overwriting previous analysis results for $sim"
        rm -rf "$plots_dir" "$results_dir" 2>/dev/null || true
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
        echo "Note: Overwriting previous reports for $sim"
        rm -f "$report_md" "$report_html" 2>/dev/null || true
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

        # Run comparison
        python compare_simulations.py "${SUCCESSFUL_SIMS[@]}" --output-base-dir "$OUTPUT_BASE_DIR"
        if [ $? -ne 0 ]; then
            echo "ERROR: compare_simulations.py failed"
        else
            # Generate comparison report
            python generate_comparison_report.py --comparison-dir "$OUTPUT_BASE_DIR/comparison" --output-dir "$OUTPUT_BASE_DIR/comparison"
            if [ $? -ne 0 ]; then
                echo "ERROR: generate_comparison_report.py failed"
            else
                echo "✓ Comparison completed"
                echo "  Comparison directory: $OUTPUT_BASE_DIR/comparison"
                echo "  Report: $OUTPUT_BASE_DIR/comparison/comparison_report.{md,html}"
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
    echo "    └── comparison/"
    echo "        ├── comparison_plots/"
    echo "        ├── comparison_data/"
    echo "        └── comparison_report.{md,html}"
fi

echo ""
echo "Completed at: $(date)"
echo "========================================"

# Exit with error if any simulations failed
if [ ${#FAILED_SIMS[@]} -gt 0 ]; then
    exit 1
fi