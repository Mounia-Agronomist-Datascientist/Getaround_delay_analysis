"""
Getaround Delay Analysis - Metrics Module
==========================================

This module contains all calculation and analysis functions
for the Getaround threshold optimization project.

"""

import pandas as pd
import numpy as np
import plotly.express as px
from typing import Dict, List, Optional, Tuple, Any
from plotly.graph_objects import Figure


def load_and_prepare_data(
    filepath: str, 
    include_canceled: bool = True) -> pd.DataFrame:
    """
    Load and prepare Getaround data.
    
    Parameters:
        filepath : str
            Path to the Excel file
        include_canceled : bool, default=True
            If True, keep canceled rentals (missing delays are meaningful, they will be NaN).
            If False, keep only ended rentals with delay info.
            
    Returns:
        pd.DataFrame : Cleaned data ready for analysis
    """
    df = pd.read_excel(filepath)
    
    if include_canceled:
        df_clean = df.copy()
    else:
        # Keep only ended rentals with complete delay info
        df_clean = df[
            (df['state'] == 'ended') & 
            (df['delay_at_checkout_in_minutes'].notna())
        ].copy()
    
    return df_clean

def separate_rental_groups(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Separate rentals into two groups based on whether they have a predecessor.
    
    Returns:
        tuple : (consecutive_rentals_df, first_rentals_df)
            - consecutive_rentals_df: rentals that follow another rental
            (have time_delta_with_previous_rental_in_minutes)
            - first_rentals_df: rentals without a predecessor (isolated or first in chain)
    """
    is_consecutive = df['time_delta_with_previous_rental_in_minutes'].notna()
    
    consecutive = df[is_consecutive].copy()
    first = df[~is_consecutive].copy()
    
    return consecutive, first


def calculate_risk_level(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate risk level for each rental.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with 'delay_at_checkout_in_minutes' 
        and 'time_delta_with_previous_rental_in_minutes' columns
        
    Returns:
    --------
    pd.DataFrame : DataFrame with 'risk_level' column added
    """
    df = df.copy()
    
    def assign_risk_level(row: pd.Series) -> str:
        """
        Assign risk level based on delay and buffer time.
        
        Categories:
        - No consecutive rental: isolated rental (no previous_id)
        - Critical: delay > time_delta (driver will definitely wait/cancel)
        - High: delay > 0 AND time_delta < 120 min (tight schedule)
        - Medium: delay > 0 AND 120 <= time_delta < 240 min
        - Low: delay <= 0 OR time_delta >= 240 min
        """
        if pd.isna(row.get('time_delta_with_previous_rental_in_minutes')):
            return 'No consecutive rental'
        
        delay = row.get('delay_at_checkout_in_minutes', 0)
        time_delta = row['time_delta_with_previous_rental_in_minutes']
        
        if delay > time_delta:
            return 'Critical (delay > buffer)'
        elif delay > 0 and time_delta < 120:
            return 'High (delay + buffer < 2h)'
        elif delay > 0 and 120 <= time_delta < 240:
            return 'Medium (delay + buffer 2-4h)'
        else:
            return 'Low (on-time or large buffer)'
    
    df['risk_level'] = df.apply(assign_risk_level, axis=1)
    return df



def calculate_threshold_impact(
    df: pd.DataFrame, 
    threshold: int, 
    checkin_type: Optional[str] = None) -> Dict[str, float]:
    """
    Calculate the impact of a given threshold on conflicts and rentals.
    
    Note: This correctly includes canceled rentals in the denominator,
    as these represent the real impact on user experience.
    """
    if 'risk_level' not in df.columns:
        raise ValueError("Column 'risk_level' is required. Run calculate_risk_level() first.")
    
    subset = df.copy()
    if checkin_type is not None:
        subset = subset[subset['checkin_type'] == checkin_type]
    
    # Total rentals = ALL consecutive rentals (canceled + ended)
    total_rentals = len(subset[
        subset['time_delta_with_previous_rental_in_minutes'].notna()
    ])
    
    # Critical conflicts = ended rentals where delay > time_delta
    total_critical = len(subset[
        (subset['state'] == 'ended') &
        (subset['risk_level'] == 'Critical (delay > buffer)')
    ])
    
    # Conflicts resolved by threshold
    resolved = len(subset[
        (subset['state'] == 'ended') &
        (subset['risk_level'] == 'Critical (delay > buffer)') & 
        (subset['time_delta_with_previous_rental_in_minutes'] < threshold)
    ])
    
    # Rentals blocked
    blocked = len(subset[
        subset['time_delta_with_previous_rental_in_minutes'] < threshold
    ])
 
    # Percentage calculations
    pct_resolved = (resolved / total_critical * 100) if total_critical > 0 else 0
    pct_blocked = (blocked / total_rentals * 100) if total_rentals > 0 else 0
    efficiency = (resolved / blocked) if blocked > 0 else 0
    
    return {
        'threshold': threshold,
        'checkin_type': checkin_type if checkin_type else 'all',
        'total_rentals': total_rentals,
        'total_critical': total_critical,
        'conflicts_resolved': resolved,
        'pct_resolved': round(pct_resolved, 2),
        'rentals_blocked': blocked,
        'pct_blocked': round(pct_blocked, 2),
        'efficiency': round(efficiency, 3)
    }


def simulate_thresholds(
    df: pd.DataFrame,
    thresholds: List[int] = [0, 30, 60, 90, 120, 150, 180, 240]
) -> pd.DataFrame:
    """
    Simulate the impact of multiple thresholds on mobile and connect.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with prepared data
    thresholds : list of int
        List of thresholds to test (in minutes)
        
    Returns:
    --------
    pd.DataFrame : Simulation results with one row per (threshold, checkin_type)
    
    Example:
    --------
    >>> results = simulate_thresholds(df, thresholds=[30, 60, 90])
    >>> print(results[['threshold', 'checkin_type', 'efficiency']])
    """
    results = []
    
    # Global test (all types combined)
    for t in thresholds:
        result = calculate_threshold_impact(df, t, checkin_type=None)
        results.append(result)
    
    # Test by checkin type
    for checkin_type in ['mobile', 'connect']:
        for t in thresholds:
            result = calculate_threshold_impact(df, t, checkin_type=checkin_type)
            results.append(result)
    
    return pd.DataFrame(results)


def plot_threshold_efficiency(
    df: pd.DataFrame,
    thresholds: List[int] = [0, 30, 60, 90, 120, 150, 180, 240],
    show_global: bool = True
) -> Figure:
    """
    Generate an interactive chart of threshold efficiency.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with prepared data
    thresholds : list of int
        List of thresholds to test
    show_global : bool
        If True, include the global curve (all types combined)
        
    Returns:
    --------
    plotly.graph_objects.Figure : Interactive chart
    """
    results_df = simulate_thresholds(df, thresholds)
    
    # Filter if we don't want to show the global view
    if not show_global:
        results_df = results_df[results_df['checkin_type'] != 'all']
    
    fig = px.line(
        results_df,
        x='threshold',
        y='efficiency',
        color='checkin_type',
        title='📊 Threshold Efficiency by Check-in Type',
        labels={
            'threshold': 'Minimum Threshold (minutes)',
            'efficiency': 'Ratio: Conflicts Resolved / Rentals Blocked',
            'checkin_type': 'Check-in Type'
        },
        markers=True
    )
    
    fig.update_layout(
        hovermode='x unified',
        legend=dict(
            title="Check-in Type",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def plot_delay_vs_buffer(
    df: pd.DataFrame,
    title: str = "Delay vs Buffer Time",
    xlim: Tuple[int, int] = (0, 900)
) -> Figure:
    """
    Interactive scatter plot: time_delta vs delay, colored by risk level.
    
    PREREQUISITE: df must have 'risk_level' column.
    If missing, it will be calculated automatically.
    """
    if 'risk_level' not in df.columns:
        df = calculate_risk_level(df)

    df_plot = df[
        (df['time_delta_with_previous_rental_in_minutes'].notna()) &
        (df['delay_at_checkout_in_minutes'].notna())
    ].copy()
    
    color_map = {
        'Critical (delay > buffer)': '#e74c3c',  # Red
        'High (delay + buffer < 2h)': '#f39c12',  # Orange
        'Medium (delay + buffer 2-4h)': '#95a5a6',  # Gray
        'Low (on-time or large buffer)': '#27ae60'  # Green
    }
    
    fig = px.scatter(
        df_plot,
        x='time_delta_with_previous_rental_in_minutes',
        y='delay_at_checkout_in_minutes',
        color='risk_level',
        color_discrete_map=color_map,
        title=title,
        labels={
            'time_delta_with_previous_rental_in_minutes': 'Buffer Time (minutes)',
            'delay_at_checkout_in_minutes': 'Delay at Checkout (minutes)'
        },
        hover_data=['checkin_type', 'state']
    )
    
    # Add critical line
    fig.add_shape(
        type="line",
        x0=0, x1=xlim[1],
        y0=0, y1=xlim[1],
        line=dict(color="#e74c3c", dash="dash", width=2),
        name="Critical line (delay = buffer)"
    )
    
    return fig


def plot_impact_comparison(
    df: pd.DataFrame,
    threshold: int
) -> Tuple[px.bar, Dict[str, float]]:
    """
    Compare the impact of a threshold between mobile and connect.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with prepared data
    threshold : int
        Threshold to analyze
        
    Returns:
    --------
    tuple : (plotly chart, metrics dictionary)
    """
    # Calculate metrics for each type
    mobile_metrics = calculate_threshold_impact(df, threshold, 'mobile')
    connect_metrics = calculate_threshold_impact(df, threshold, 'connect')
    
    # Prepare data for the chart
    comparison_data = pd.DataFrame([
        {
            'Type': 'Mobile',
            'Metric': 'Conflicts Resolved (%)',
            'Value': mobile_metrics['pct_resolved']
        },
        {
            'Type': 'Connect',
            'Metric': 'Conflicts Resolved (%)',
            'Value': connect_metrics['pct_resolved']
        },
        {
            'Type': 'Mobile',
            'Metric': 'Rentals Blocked (%)',
            'Value': mobile_metrics['pct_blocked']
        },
        {
            'Type': 'Connect',
            'Metric': 'Rentals Blocked (%)',
            'Value': connect_metrics['pct_blocked']
        }
    ])
    
    fig = px.bar(
        comparison_data,
        x='Type',
        y='Value',
        color='Metric',
        barmode='group',
        title=f'Impact of {threshold}-minute Threshold',
        labels={'Value': 'Percentage (%)'}
    )
    
    summary = {
        'mobile': mobile_metrics,
        'connect': connect_metrics
    }
    
    return fig, summary


def get_optimal_threshold(
    df: pd.DataFrame,
    thresholds: List[int] = [0, 30, 60, 90, 120, 150, 180, 240],
    metric: str = 'efficiency'
) -> Dict[str, Any]:
    """
    Identify the optimal threshold according to a given criterion.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with prepared data
    thresholds : list of int
        List of thresholds to test
    metric : str
        Optimization metric: 'efficiency', 'pct_resolved', or 'pct_blocked'
        
    Returns:
    --------
    dict : Information about the optimal threshold
    """
    results_df = simulate_thresholds(df, thresholds)
    
    # Filter to have only the global view
    global_results = results_df[results_df['checkin_type'] == 'all']
    
    # Find the optimal according to the metric
    optimal_row = global_results.loc[global_results[metric].idxmax()]
    
    return {
        'optimal_threshold': int(optimal_row['threshold']),
        'metric_used': metric,
        'metric_value': optimal_row[metric],
        'conflicts_resolved': optimal_row['conflicts_resolved'],
        'pct_resolved': optimal_row['pct_resolved'],
        'rentals_blocked': optimal_row['rentals_blocked'],
        'pct_blocked': optimal_row['pct_blocked'],
        'efficiency': optimal_row['efficiency']
    }


def generate_summary_report(df: pd.DataFrame, threshold: int) -> str:
    """
    Generate a text report summarizing the impact of a threshold.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with prepared data
    threshold : int
        Threshold to analyze
        
    Returns:
    --------
    str : Formatted text report
    """
    metrics = calculate_threshold_impact(df, threshold)
    
    report = f"""
    📊 IMPACT REPORT - {threshold}-MINUTE THRESHOLD
    {'='*60}
    
    🎯 BENEFITS
    • Critical conflicts resolved: {metrics['conflicts_resolved']} / {metrics['total_critical']}
    • Resolution rate: {metrics['pct_resolved']:.1f}%
    
    💰 COSTS
    • Rentals blocked: {metrics['rentals_blocked']} / {metrics['total_rentals']}
    • Impact on volume: {metrics['pct_blocked']:.2f}%
    
    ⚖️ EFFICIENCY
    • Benefit/cost ratio: {metrics['efficiency']:.2f}
    • For each rental blocked, we resolve {metrics['efficiency']:.2f} conflicts
    
    {'='*60}
    """
    
    return report


# Utility function for exploratory data analysis
def get_data_summary(df: pd.DataFrame) -> Dict[str, any]:
    """
    Return a summary of the data for EDA.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame to analyze
        
    Returns:
    --------
    dict : Descriptive statistics
    """
    return {
        'total_rentals': len(df),
        'checkin_types': df['checkin_type'].value_counts().to_dict(),
        'median_delay': df['delay_at_checkout_in_minutes'].median(),
        'mean_delay': df['delay_at_checkout_in_minutes'].mean(),
        'pct_late': (df['delay_at_checkout_in_minutes'] > 0).sum() / len(df) * 100,
        'consecutive_rentals': df['time_delta_with_previous_rental_in_minutes'].notna().sum(),
        'pct_consecutive': df['time_delta_with_previous_rental_in_minutes'].notna().sum() / len(df) * 100
    }
