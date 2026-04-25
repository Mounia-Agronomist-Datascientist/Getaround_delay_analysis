"""
GETAROUND DELAY ANALYSIS DASHBOARD
===================================

Interactive dashboard to determine the optimal minimum buffer time
between consecutive car rentals to minimize conflicts while preserving revenue.

Uses metrics.py module for all calculations.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sys
sys.path.insert(0, '../src/')

from src.metrics import (
    load_and_prepare_data,
    separate_rental_groups,
    calculate_risk_level,
    calculate_threshold_impact,
    simulate_thresholds,
    get_data_summary,
    get_optimal_threshold,
    generate_summary_report,
    plot_threshold_efficiency,
    plot_delay_vs_buffer,
)

# ============================================================================
# PAGE CONFIGURATION & THEME
# ============================================================================

st.set_page_config(
    page_title="GetAround - Delay Analysis",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Light theme CSS with Getaround colors
st.markdown("""
<style>
    /* Getaround brand colors */
    :root {
        --getaround-primary: #00A699;    /* Teal/Cyan - main brand */
        --getaround-dark: #0F4C3F;       /* Dark teal */
        --getaround-light: #E8F5F3;      /* Light teal background */
        --accent: #FF6B6B;               /* Red for warnings */
    }
    
    /* Main app background */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Header styling */
    header[data-testid="stHeader"] {
        background-color: #ffffff;
        border-bottom: 2px solid #00A699;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }
    
    /* Hero section */
    .hero {
        background: linear-gradient(135deg, #00A699 0%, #00c9b7 100%);
        border-radius: 12px;
        padding: 2.5rem;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0, 166, 153, 0.15);
    }
    
    .hero h1 {
        color: #ffffff;
        font-size: 2.5rem;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    
    .hero p {
        color: rgba(255, 255, 255, 0.9);
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    .badge {
        display: inline-block;
        background: rgba(255, 255, 255, 0.25);
        color: #ffffff;
        padding: 6px 16px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        border: 1px solid rgba(255, 255, 255, 0.4);
        margin-top: 10px;
    }
    
    /* Section titles */
    .section-title {
        color: #423C3D;
        border-bottom: 3px solid #00A699;
        padding-bottom: 10px;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
        font-size: 1.3rem;
        font-weight: 600;
    }
    
    /* Section titles little */
    .section-title-little {
        color: #423C3D;
        padding-bottom: 10px;
        margin-top: 2.5rem;
        margin-bottom: 1rem;
        font-size: 1.25rem;
        font-weight: 600;
    }
    
    /* Metrics cards */
    div[data-testid="stMetric"] {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-left: 4px solid #00A699;
        border-radius: 8px;
        padding: 16px;
        transition: box-shadow 0.2s;
    }
    
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 4px 8px rgba(0, 166, 153, 0.1);
    }
    
    div[data-testid="stMetric"] label {
        color: #666666;
        font-size: 0.85rem;
        font-weight: 500;
    }
    
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #00A699;
        font-size: 1.8rem;
        font-weight: 700;
    }
    
    /* Dividers */
    hr {
        border: none;
        border-top: 1px solid #e0e0e0;
        margin: 2rem 0;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        color: #999999;
        font-size: 0.85rem;
        margin-top: 3rem;
        padding-top: 2rem;
        border-top: 1px solid #e0e0e0;
    }
    
    /* Text styling */
    p, li {
        color: #333333;
        line-height: 1.6;
    }
    
    /* Links */
    a {
        color: #00A699;
        text-decoration: none;
    }
    
    a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)


# Color palette for specific charts
COLORS = {
    'low': '#27ae60',        # Green
    'medium': '#f39c12',     # Orange
    'high': '#e67e22',       # Dark orange
    'critical': '#e74c3c',   # Red
    'mobile': "#D59A41",     # Light orange
    'connect': "#D8EC90",    # Light green
    'all':"#B22B06"          # Dark red
}

# ============================================================================
# HEADER
# ============================================================================

st.markdown("""
<div class="hero">
    <h1>GetAround — Delay Analysis</h1>
    <p>Decision support dashboard: What minimum threshold should be set between two rentals?</p>
    <span class="badge">Complete analysis with business metrics</span>
</div>
""", unsafe_allow_html=True)

# ============================================================================
# LOAD DATA (CACHED)
# ============================================================================

@st.cache_data(ttl=3600)
def load_and_process_data():
    """Load and process data using metrics.py functions"""
    try:
        df = load_and_prepare_data("DATA/raw_data/get_around_delay_analysis.xlsx", include_canceled=True)
        consecutive, first = separate_rental_groups(df)
        df_risk = calculate_risk_level(consecutive)
        return df, consecutive, first, df_risk
    except FileNotFoundError as e:
        st.error(f"File not found: {e}")
        st.error("Expected file: DATA/raw_data/get_around_delay_analysis.xlsx")
        st.error("From: Streamlit_dashbord_GetAround/")
        return None, None, None, None
 
df, consecutive, first, df_risk = load_and_process_data()
if df is None:
    st.error("Data couldn't be loaded!")
    st.stop()

# Ensure correct data types
df_risk = df_risk.astype({
    "delay_at_checkout_in_minutes": "float64",
    "time_delta_with_previous_rental_in_minutes": "float64"
})

# ============================================================================
# PART 1: GLOBAL DATA OVERVIEW
# ============================================================================

st.markdown(
    '<h3 class="section-title">Part 1: Global Dataset Overview</h3>',
    unsafe_allow_html=True
)

st.markdown("""
This section presents statistics on the entire dataset before filtering.
Understanding the global context helps identify the scope of the delay problem.
""")

# Display global metrics
col1, col2, col3, col4 = st.columns(4)

# Hide the delta arrow
st.markdown("""
<style>
[data-testid="stMetricDelta"] svg {
    display: none;
}
</style>
""", unsafe_allow_html=True)


with col1:
    st.metric(
        "Total Rentals",
        f"{len(df):,}",
        "All rentals in dataset"
    )

with col2:
    late_count = (df['delay_at_checkout_in_minutes'] > 0).sum()
    late_pct = (late_count / len(df)) * 100
    st.metric(
        "Late Checkouts",
        f"{late_pct:.1f}%",
        f"{late_count:,} rentals"
    )

with col3:
    st.metric(
        "Median Delay",
        f"{df['delay_at_checkout_in_minutes'].median():.0f} min",
        "All rentals"
    )

with col4:
    st.metric(
        "Check-in Types",
        "Mobile + Connect",
        f"Mobile: {(df['checkin_type']=='mobile').sum():,} | Connect: {(df['checkin_type']=='connect').sum():,}"
    )

st.divider()

# Global distribution charts
col1, col2 = st.columns(2)

with col1:
    # Check-in type distribution
    checkin_dist = df['checkin_type'].value_counts()
    labels_checkin = checkin_dist.index.tolist()
    values_checkin = checkin_dist.values.tolist()
    
    colors_checkin = {
        'mobile': COLORS['mobile'],      
        'connect': COLORS['connect']     
    }
    slice_colors_checkin = [colors_checkin.get(label, '#cccccc') for label in labels_checkin]
    
    fig_checkin = go.Figure(data=[go.Pie(
        labels=labels_checkin,
        values=values_checkin,
        marker=dict(colors=slice_colors_checkin),
        textinfo='percent',
        textposition='inside',
        hoverinfo='label+value+percent'
    )])
    fig_checkin.update_layout(
        title="Check-in Type Distribution",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8f9fa",
        font=dict(color="#333333"),
        legend=dict(font=dict(color="#333333"))
    )
    st.plotly_chart(fig_checkin, use_container_width=True)

with col2:
    # State distribution (canceled vs ended)
    state_dist = df['state'].value_counts()
    labels_state = state_dist.index.tolist()
    values_state = state_dist.values.tolist()
    
    colors_state = {
        'ended': '#27ae60',       # Green
        'canceled': '#e74c3c'     # Red
    }
    slice_colors_state = [colors_state.get(label, '#cccccc') for label in labels_state]
    
    fig_state = go.Figure(data=[go.Pie(
        labels=labels_state,
        values=values_state,
        marker=dict(colors=slice_colors_state),
        textinfo='percent',
        textposition='inside',
        hoverinfo='label+value+percent'
    )])
    fig_state.update_layout(
        title="Rental State Distribution",
        paper_bgcolor="#ffffff",
        plot_bgcolor="#f8f9fa",
        font=dict(color="#333333"),
        legend=dict(font=dict(color="#333333"))
    )
    st.plotly_chart(fig_state, use_container_width=True)

st.divider()


# ============================================================================
# PART 2: CONSECUTIVE RENTALS ANALYSIS
# ============================================================================

st.markdown(
    '<h3 class="section-title">Part 2: Consecutive Rentals - Risk Analysis</h3>',
    unsafe_allow_html=True
)

st.markdown(f"""
This section focuses on **consecutive rentals** ({len(df_risk):,} rentals) — 
rentals that follow another rental and are at risk of cascading delays.
These are the rentals where a threshold policy would have impact.
""")

# Sidebar controls for this section
st.sidebar.markdown("### Simulation Parameters")

selected_threshold = st.sidebar.slider(
    "Minimum threshold (minutes)", 
    min_value=0, 
    max_value=720, 
    value=30, 
    step=10,
    help="Minimum time required between two consecutive rentals"
)

st.sidebar.markdown("---")

# Get optimal threshold
optimal = get_optimal_threshold(df_risk, metric='efficiency')
st.sidebar.markdown(f"""
### Recommended Threshold
**{optimal['optimal_threshold']} minutes**

- Resolved cases: {optimal['pct_resolved']:.1f}%
- Blocked rentals: {optimal['pct_blocked']:.2f}%
- Efficiency ratio: {optimal['efficiency']:.2f}
""")

# Consecutive rentals metrics
st.markdown(
    '<h3 class="section-title-little">Consecutive Rentals Overview</h3>',
    unsafe_allow_html=True
)

summary = get_data_summary(df_risk)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Consecutive Rentals",
        f"{summary['total_rentals']:,}",
        f"{(summary['total_rentals']/len(df))*100:.1f}% of total"
    )

with col2:
    st.metric(
        "Late Checkouts",
        f"{summary['pct_late']:.1f}%",
        f"Median: {summary['median_delay']:.0f} min"
    )

with col3:
    critical_count = (df_risk['risk_level'] == 'Critical (delay > buffer)').sum()
    st.metric(
        "Critical Conflicts",
        f"{critical_count}",
        "Delay exceeds buffer time"
    )

with col4:
    st.metric(
        "Optimal Threshold",
        f"{optimal['optimal_threshold']} min",
        f"Efficiency: {optimal['efficiency']:.2f}"
    )

# Risk level distribution (Pie chart)
st.markdown(
    '<h3 class="section-title-little">Risk Level Distribution</h3>',
    unsafe_allow_html=True
)

risk_dist = df_risk['risk_level'].value_counts()
labels_risk = risk_dist.index.tolist()
values_risk = risk_dist.values.tolist()

colors_risk = {
    "Low (on-time or large buffer)": "#27ae60",      # Green
    "Critical (delay > buffer)": "#e74c3c",          # Red
    "Medium (delay + buffer 2-4h)": "#f39c12",       # Orange
    "High (delay + buffer < 2h)": "#95a5a6"          # Gray
}
slice_colors_risk = [colors_risk.get(label, '#cccccc') for label in labels_risk]

fig_risk = go.Figure(data=[go.Pie(
    labels=labels_risk,
    values=values_risk,
    marker=dict(colors=slice_colors_risk),
    textinfo='percent',
    textposition='inside',
    hoverinfo='label+value+percent',
    pull=[0.05 if label == "Critical (delay > buffer)" else 0 for label in labels_risk]
)])
fig_risk.update_layout(
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8f9fa",
    font=dict(color="#333333"),
    legend=dict(font=dict(color="#333333"))
)
st.plotly_chart(fig_risk, use_container_width=True)

st.divider()

# ============================================================================
# SECTION 1: THRESHOLD SIMULATION CHARTS
# ============================================================================

st.markdown(
    '<h3 class="section-title-little">Threshold Efficiency Analysis</h3>',
    unsafe_allow_html=True
)

# Simulate thresholds
results_df = simulate_thresholds(df_risk)

# Create efficiency chart
fig_efficiency = go.Figure()

colors_efficiency = {'all': COLORS['all'], 'mobile': COLORS['mobile'], 'connect': COLORS['connect']}

for checkin_type in ['all', 'mobile', 'connect']:
    data = results_df[results_df['checkin_type'] == checkin_type].sort_values('threshold')
    
    fig_efficiency.add_trace(go.Scatter(
        x=data['threshold'].tolist(),
        y=data['efficiency'].tolist(),
        mode='lines+markers',
        name=checkin_type.capitalize(),
        line=dict(width=3, color=colors_efficiency[checkin_type]),
        marker=dict(size=8, color=colors_efficiency[checkin_type]),
        hovertemplate='<b>%{fullData.name}</b><br>Threshold: %{x} min<br>Efficiency: %{y:.3f}<extra></extra>'
    ))
 
fig_efficiency.update_layout(
    xaxis_title='Minimum Threshold (minutes)',
    yaxis_title='Efficiency Ratio (Conflicts Resolved / Rentals Blocked)',
    height=500,
    paper_bgcolor="#ffffff",
    plot_bgcolor="#f8f9fa",
    font=dict(color="#333333"),
    title_font_color="#00A699",
    xaxis=dict(gridcolor="#e0e0e0", zerolinecolor="#e0e0e0"),
    yaxis=dict(gridcolor="#e0e0e0", zerolinecolor="#e0e0e0"),
    legend=dict(font=dict(color="#333333")),
    hovermode="x unified"
)
 
st.plotly_chart(fig_efficiency, use_container_width=True)
 
st.divider()


# ============================================================================
# SECTION 2: IMPACT ANALYSIS WITH THRESHOLD SLIDER AND METRICS
# ============================================================================

st.markdown(
    '<h3 class="section-title">Impact Analysis - Threshold Slider</h3>',
    unsafe_allow_html=True
)

# Slider for threshold selection
threshold_slider = st.slider(
    "Select threshold for impact analysis",
    min_value=0,
    max_value=240,
    value=selected_threshold,
    step=10,
    key="threshold_slider"
)

st.divider()

# Calculate impact for selected threshold
impact_all = calculate_threshold_impact(df_risk, threshold_slider, checkin_type=None)
impact_mobile = calculate_threshold_impact(df_risk, threshold_slider, checkin_type='mobile')
impact_connect = calculate_threshold_impact(df_risk, threshold_slider, checkin_type='connect')

# Display metrics in 4 columns
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Conflicts Resolved (All)",
        f"{impact_all['conflicts_resolved']}/{impact_all['total_critical']}",
        f"{impact_all['pct_resolved']:.1f}%"
    )

with col2:
    st.metric(
        "Rentals Blocked (Mobile)",
        f"{impact_mobile['rentals_blocked']}/{impact_mobile['total_rentals']}",
        f"{impact_mobile['pct_blocked']:.2f}%"
    )

with col3:
    st.metric(
        "Rentals Blocked (Connect)",
        f"{impact_connect['rentals_blocked']}/{impact_connect['total_rentals']}",
        f"{impact_connect['pct_blocked']:.2f}%"
    )

with col4:
    st.metric(
        "Efficiency Ratio (All)",
        f"{impact_all['efficiency']:.3f}",
        f"Mobile: {impact_mobile['efficiency']:.3f}"
    )

st.divider()


# ============================================================================
# SECTION 2: RECOMMENDATION
# ============================================================================

st.markdown(
    '<h3 class="section-title">Recommendation</h3>',
    unsafe_allow_html=True
)

recommendation = f"""
\nBased on the analysis of {df_risk.shape[0]} consecutive rentals:

RECOMMENDED THRESHOLD: {optimal['optimal_threshold']} minutes

Benefits:
- Resolves {optimal['pct_resolved']:.1f}% of critical conflicts
- Impacts only {optimal['pct_blocked']:.2f}% of rentals
- Efficiency ratio: {optimal['efficiency']:.2f}

This threshold provides the best balance between:
1. Reducing cascading delays (conflict resolution)
2. Minimizing impact on rental volume

Implementation:
- Set minimum {optimal['optimal_threshold']}-minute buffer between consecutive rentals
- Apply to all check-in types (mobile + connect)
- Monitor and adjust based on customer feedback
"""

st.success(recommendation)

# ============================================================================
# FOOTER
# ============================================================================


st.markdown("""
<div class="footer">
<p><strong>Data Source</strong>: GetAround car-sharing dataset | 
<strong>Analysis Date</strong>: April 2026 | 
<strong>Author</strong>: Mounia Tonazzini | 
<strong>Portfolio Project</strong>: Data Science Bootcamp - Jedha</p>
</div>
""", unsafe_allow_html=True)