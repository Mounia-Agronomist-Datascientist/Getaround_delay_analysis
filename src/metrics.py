"""
Getaround Delay Analysis - Metrics Module
==========================================

This module contains all calculation and analysis functions
for the Getaround threshold optimization project.

Author: Mounia
Date: January 2026
"""

import pandas as pd
import numpy as np
import plotly.express as px
from typing import Dict, List, Optional, Tuple


def load_and_prepare_data(filepath: str) -> pd.DataFrame:
    """
    Load and prepare Getaround data.
    
    Parameters:
    -----------
    filepath : str
        Path to the Excel file
        
    Returns:
    --------
    pd.DataFrame : Cleaned data ready for analysis
    """
    df = pd.read_excel(filepath)
    
    # Filter only completed rentals with delay information available
    df_clean = df[
        (df['state'] == 'ended') & 
        (df['delay_at_checkout_in_minutes'].notna())
    ].copy()
    
    return df_clean


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
    
    def assign_risk(row):
        if pd.isna(row['time_delta_with_previous_rental_in_minutes']):
            return 'No conflict (isolated rental)'
        elif row['delay_at_checkout_in_minutes'] > row['time_delta_with_previous_rental_in_minutes']:
            return 'Critical (delay > time delta)'
        elif row['delay_at_checkout_in_minutes'] > 0:
            return 'Moderate (late but buffer absorbed)'
        else:
            return 'Low (on time or early)'
    
    df['risk_level'] = df.apply(assign_risk, axis=1)
    return df


def calculate_threshold_impact(
    df: pd.DataFrame, 
    threshold: int, 
    checkin_type: Optional[str] = None
) -> Dict[str, float]:
    """
    Calculate the impact of a given threshold on conflicts and rentals.
    
    Parameters:
    -----------
    df : pd.DataFrame
        DataFrame with prepared data
    threshold : int
        Minimum threshold in minutes between two rentals
    checkin_type : str, optional
        'mobile' or 'connect' to filter. None = all types
        
    Returns:
    --------
    dict : Dictionary containing the following metrics:
        - threshold: applied threshold
        - total_rentals: total number of rentals
        - total_critical: total number of critical conflicts
        - conflicts_resolved: number of conflicts resolved by the threshold
        - pct_resolved: % of critical conflicts resolved
        - rentals_blocked: number of rentals that would be blocked
        - pct_blocked: % of rentals blocked out of total
        - efficiency: ratio (conflicts resolved / rentals blocked)
        
    Example:
    --------
    >>> metrics = calculate_threshold_impact(df, threshold=90)
    >>> print(f"Conflicts resolved: {metrics['pct_resolved']:.1f}%")
    """
    # Filter by type if specified
    subset = df.copy()
    if checkin_type is not None:
        subset = subset[subset['checkin_type'] == checkin_type]
    
    # Basic calculations
    total_rentals = len(subset)
    total_critical = len(subset[subset['risk_level'] == 'Critical (delay > time delta)'])
    
    # Conflicts that would be resolved with this threshold
    resolved = len(subset[
        (subset['risk_level'] == 'Critical (delay > time delta)') & 
        (subset['time_delta_with_previous_rental_in_minutes'] < threshold)
    ])
    
    # Rentals that would be blocked with this threshold
    blocked = len(subset[
        subset['time_delta_with_previous_rental_in_minutes'].notna() &
        (subset['time_delta_with_previous_rental_in_minutes'] < threshold)
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
) -> px.line:
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
) -> Dict[str, any]:
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
