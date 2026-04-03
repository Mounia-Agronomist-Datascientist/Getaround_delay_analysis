"""
GETAROUND THRESHOLD OPTIMIZER
=================================
Interactive dashboard to determine the optimal minimum buffer time
between consecutive car rentals to minimize conflicts while preserving revenue.

Author: Mounia Tonazzini
Date: January 2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import custom functions
from src.metrics import *

# ============================================================================
# PAGE CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Getaround Threshold Optimizer",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    h1 {
        color: #1f77b4;
    }
    .reportview-container .main .block-container {
        max-width: 1200px;
    }
    </style>
    """, unsafe_allow_html=True)

# ============================================================================
# LOAD AND CACHE DATA
# ============================================================================

@st.cache_data
def load_data():
    """Load and prepare data with caching for performance"""
    try:
        # Adjust this path to your data location
        data_path ="DATA/raw_data/get_around_delay_analysis.xlsx"
        
        # Load raw data
        raw_df = pd.read_excel(data_path)
        
        # Filter and prepare
        df = raw_df[
            (raw_df['state'] == 'ended') & 
            (raw_df['delay_at_checkout_in_minutes'].notna())
        ].copy()
        
        # Calculate risk levels
        df = calculate_risk_level(df)
        
        return raw_df, df
    
    except FileNotFoundError:
        st.error("Data file not found! Please check the path in app.py")
        st.stop()
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

# Load data
raw_df, df = load_data()

# ============================================================================
# SIDEBAR - FILTERS AND SETTINGS
# ============================================================================

st.sidebar.title("⚙️ Settings")
st.sidebar.markdown("---")

# Threshold selector
st.sidebar.subheader("🎯 Threshold Selection")
threshold = st.sidebar.slider(
    "Minimum buffer time (minutes)",
    min_value=0,
    max_value=240,
    value=90,
    step=15,
    help="Select the minimum time required between consecutive rentals"
)

st.sidebar.markdown("---")

# Checkin type filter
st.sidebar.subheader("📱 Check-in Type Filter")
checkin_filter = st.sidebar.radio(
    "Analyze by check-in type:",
    options=["All", "Mobile Only", "Connect Only"],
    index=0
)

# Map selection to actual values
checkin_type_map = {
    "All": None,
    "Mobile Only": "mobile",
    "Connect Only": "connect"
}
selected_checkin = checkin_type_map[checkin_filter]

st.sidebar.markdown("---")

# Advanced options
with st.sidebar.expander("🔧 Advanced Options"):
    show_raw_data = st.checkbox("Show raw data table", value=False)
    show_methodology = st.checkbox("Show methodology", value=False)
    
st.sidebar.markdown("---")
st.sidebar.info("""
    **How to use:**
    1. Adjust the threshold slider
    2. View real-time impact on KPIs
    3. Compare mobile vs connect
    4. Make data-driven decisions!
""")

# ============================================================================
# MAIN DASHBOARD
# ============================================================================

# Header
st.title("Getaround Threshold Optimizer")
st.markdown("""
    **Determine the optimal minimum buffer time between consecutive rentals**  
    Balance conflict resolution with rental volume to maximize customer satisfaction and revenue.
""")

st.markdown("---")

# ============================================================================
# SECTION 1: KEY PERFORMANCE INDICATORS
# ============================================================================

st.header("Key Performance Indicators")

# Calculate metrics for selected threshold
metrics = calculate_threshold_impact(df, threshold, selected_checkin)

# Display KPIs in columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="Conflicts Resolved",
        value=f"{metrics['pct_resolved']:.1f}%",
        delta=f"{metrics['conflicts_resolved']} conflicts",
        help="Percentage of critical conflicts that would be prevented"
    )

with col2:
    st.metric(
        label="Rentals Blocked",
        value=f"{metrics['pct_blocked']:.2f}%",
        delta=f"{metrics['rentals_blocked']} rentals",
        delta_color="inverse",
        help="Percentage of rentals that would be prevented by the threshold"
    )

with col3:
    st.metric(
        label="⚖️ Efficiency Ratio",
        value=f"{metrics['efficiency']:.2f}",
        help="Number of conflicts resolved per rental blocked (higher is better)"
    )

with col4:
    total_critical = metrics['total_critical']
    remaining_conflicts = total_critical - metrics['conflicts_resolved']
    st.metric(
        label="Remaining Conflicts",
        value=remaining_conflicts,
        delta=f"{(remaining_conflicts/total_critical*100):.1f}% of total",
        delta_color="inverse",
        help="Critical conflicts that would still occur with this threshold"
    )

st.markdown("---")

# ============================================================================
# SECTION 2: THRESHOLD EFFICIENCY ANALYSIS
# ============================================================================

st.header("Threshold Efficiency Analysis")

tab1, tab2 = st.tabs(["Efficiency Curve", "Detailed Comparison"])

with tab1:
    st.markdown("""
        **Find the optimal threshold:** The "elbow" point represents the best balance 
        between conflicts resolved and rentals blocked.
    """)
    
    # Generate efficiency plot
    thresholds_range = [0, 30, 60, 90, 120, 150, 180, 240]
    fig_efficiency = plot_threshold_efficiency(df, thresholds=thresholds_range, show_global=True)
    
    # Add vertical line for selected threshold
    fig_efficiency.add_vline(
        x=threshold, 
        line_dash="dash", 
        line_color="red",
        annotation_text=f"Selected: {threshold}min",
        annotation_position="top"
    )
    
    st.plotly_chart(fig_efficiency, use_container_width=True)

with tab2:
    st.markdown("**Compare different thresholds side by side:**")
    
    # Simulate multiple thresholds
    results_df = simulate_thresholds(df, thresholds=thresholds_range)
    
    # Filter by selected checkin type
    if selected_checkin:
        display_df = results_df[results_df['checkin_type'] == selected_checkin]
    else:
        display_df = results_df[results_df['checkin_type'] == 'all']
    
    # Format and display table
    display_df = display_df[[
        'threshold', 'conflicts_resolved', 'pct_resolved', 
        'rentals_blocked', 'pct_blocked', 'efficiency'
    ]].copy()
    
    # Rename columns for better display
    display_df.columns = [
        'Threshold (min)', 'Conflicts Resolved', 'Resolution %', 
        'Rentals Blocked', 'Impact %', 'Efficiency'
    ]
    
    # Highlight the selected threshold row
    def highlight_row(row):
        if row['Threshold (min)'] == threshold:
            return ['background-color: #ffeb9c'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        display_df.style.apply(highlight_row, axis=1).format({
            'Resolution %': '{:.2f}%',
            'Impact %': '{:.2f}%',
            'Efficiency': '{:.2f}'
        }),
        use_container_width=True
    )

st.markdown("---")

# ============================================================================
# SECTION 3: MOBILE VS CONNECT COMPARISON
# ============================================================================

st.header("📱 Mobile vs Connect Comparison")

col1, col2 = st.columns(2)

# Calculate metrics for each type
mobile_metrics = calculate_threshold_impact(df, threshold, 'mobile')
connect_metrics = calculate_threshold_impact(df, threshold, 'connect')

with col1:
    st.subheader("📱 Mobile Check-in")
    
    # Create metrics
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.metric("Conflicts Resolved", f"{mobile_metrics['pct_resolved']:.1f}%")
        st.metric("Efficiency", f"{mobile_metrics['efficiency']:.2f}")
    with subcol2:
        st.metric("Rentals Blocked", f"{mobile_metrics['pct_blocked']:.2f}%")
        st.metric("Total Rentals", f"{mobile_metrics['total_rentals']:,}")

with col2:
    st.subheader("🔌 Connect Check-in")
    
    # Create metrics
    subcol1, subcol2 = st.columns(2)
    with subcol1:
        st.metric("Conflicts Resolved", f"{connect_metrics['pct_resolved']:.1f}%")
        st.metric("Efficiency", f"{connect_metrics['efficiency']:.2f}")
    with subcol2:
        st.metric("Rentals Blocked", f"{connect_metrics['pct_blocked']:.2f}%")
        st.metric("Total Rentals", f"{connect_metrics['total_rentals']:,}")

# Comparison chart
st.markdown("### Visual Comparison")

comparison_data = pd.DataFrame({
    'Check-in Type': ['Mobile', 'Mobile', 'Connect', 'Connect'],
    'Metric': ['Conflicts Resolved (%)', 'Rentals Blocked (%)', 
               'Conflicts Resolved (%)', 'Rentals Blocked (%)'],
    'Value': [
        mobile_metrics['pct_resolved'],
        mobile_metrics['pct_blocked'],
        connect_metrics['pct_resolved'],
        connect_metrics['pct_blocked']
    ]
})

fig_comparison = px.bar(
    comparison_data,
    x='Check-in Type',
    y='Value',
    color='Metric',
    barmode='group',
    title=f'Impact Comparison at {threshold}-minute Threshold',
    labels={'Value': 'Percentage (%)'},
    color_discrete_map={
        'Conflicts Resolved (%)': '#2ecc71',
        'Rentals Blocked (%)': '#e74c3c'
    }
)

st.plotly_chart(fig_comparison, use_container_width=True)

st.markdown("---")

# ============================================================================
# SECTION 4: DATASET OVERVIEW
# ============================================================================

st.header("Dataset Overview")

# Get summary statistics
summary = get_data_summary(df)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Rentals Analyzed", f"{summary['total_rentals']:,}")
    st.metric("Consecutive Rentals", 
              f"{summary['consecutive_rentals']:,}",
              delta=f"{summary['pct_consecutive']:.1f}% of total")

with col2:
    st.metric("Median Delay", f"{summary['median_delay']:.0f} min")
    st.metric("Mean Delay", f"{summary['mean_delay']:.0f} min")

with col3:
    st.metric("Late Returns", f"{summary['pct_late']:.1f}%")
    
    # Checkin type breakdown
    st.markdown("**Check-in Types:**")
    for checkin, count in summary['checkin_types'].items():
        pct = (count / summary['total_rentals'] * 100)
        st.write(f"• {checkin.capitalize()}: {pct:.1f}%")

# Risk level distribution
st.markdown("### Risk Level Distribution")

risk_dist = df['risk_level'].value_counts()
risk_pct = (risk_dist / len(df) * 100).round(1)

fig_risk = px.pie(
    values=risk_dist.values,
    names=risk_dist.index,
    title='Distribution of Risk Levels',
    color_discrete_sequence=px.colors.sequential.RdBu
)

st.plotly_chart(fig_risk, use_container_width=True)

st.markdown("---")

# ============================================================================
# SECTION 5: STRATEGIC RECOMMENDATION
# ============================================================================

st.header("Strategic Recommendation")

# Determine optimal threshold (highest efficiency)
optimal = calculate_threshold_impact(df, 90)  # You can make this dynamic

st.success(f"""
    **Recommended Threshold: 90 minutes**
    
    Based on the analysis of {summary['total_rentals']:,} rentals:
    
    **Benefits:**
    - Resolves **{optimal['pct_resolved']:.1f}%** of all critical conflicts
    - Efficiency ratio of **{optimal['efficiency']:.2f}** (conflicts resolved per rental blocked)
    - Absorbs the median delay of **{summary['median_delay']:.0f} minutes**
    
    **Trade-offs:**
    - Blocks only **{optimal['pct_blocked']:.2f}%** of total rental volume
    - Minimal revenue impact with maximum conflict prevention
    
    **Why 90 minutes?**
    - Represents the "elbow point" in the efficiency curve
    - Universal applicability across both Mobile and Connect check-ins
    - Balances customer satisfaction with operational efficiency
""")

# Export recommendation
if st.button("Generate Full Report"):
    report = generate_summary_report(df, threshold)
    st.text(report)
    st.download_button(
        label="Download Report",
        data=report,
        file_name=f"getaround_threshold_report_{threshold}min.txt",
        mime="text/plain"
    )

st.markdown("---")

# ============================================================================
# OPTIONAL SECTIONS
# ============================================================================

# Show raw data if requested
if show_raw_data:
    with st.expander("View Raw Data"):
        st.dataframe(df.head(100), use_container_width=True)
        st.caption(f"Showing first 100 rows of {len(df):,} total rentals")

# Show methodology if requested
if show_methodology:
    with st.expander("Methodology"):
        st.markdown("""
        ### How We Calculate Impact
        
        **Risk Level Classification:**
        - **Critical**: Delay > Time delta (next customer impacted)
        - **Moderate**: Late but buffer absorbed the delay
        - **Low**: On time or early
        - **No conflict**: Isolated rental (no next rental)
        
        **Threshold Impact:**
        1. **Conflicts Resolved**: Number of critical conflicts that would be prevented
        2. **Rentals Blocked**: Rentals that wouldn't be accepted due to insufficient buffer
        3. **Efficiency**: Ratio of conflicts resolved to rentals blocked
        
        **Optimization Goal:**
        Find the threshold that maximizes conflicts resolved while minimizing rentals blocked.
        """)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #888;'>
        <p>Getaround Threshold Optimizer | Built with Streamlit | Data Science Project 2026</p>
    </div>
    """, unsafe_allow_html=True)
