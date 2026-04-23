"""
ESSENTIAL tests for metrics.py

Installation:
    pip install pytest pandas

Execution:
    pytest tests/test_metrics.py -v
"""

import pytest
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, 'src/')

from metrics import (
    load_and_prepare_data,
    separate_rental_groups,
    calculate_risk_level,
    calculate_threshold_impact,
    simulate_thresholds,
)


# FIXTURES =========================================================================

@pytest.fixture
def sample_data():
    """Small test DataFrame covering different cases"""
    return pd.DataFrame({
        'car_id': [1, 1, 2, 2, 3],
        'state': ['ended', 'ended', 'canceled', 'ended', 'ended'],
        'delay_at_checkout_in_minutes': [30.0, 150.0, np.nan, -10.0, 45.0],
        'time_delta_with_previous_rental_in_minutes': [np.nan, 120.0, 90.0, 200.0, np.nan],
        'checkin_type': ['mobile', 'mobile', 'connect', 'connect', 'mobile']
    })


@pytest.fixture
def consecutive_rentals(sample_data):
    """DataFrame containing ONLY consecutive rentals"""
    consecutive, _ = separate_rental_groups(sample_data)
    return consecutive


@pytest.fixture
def df_with_risk(consecutive_rentals):
    """Consecutive rentals DataFrame WITH risk_level calculated"""
    return calculate_risk_level(consecutive_rentals)



# ESSENTIAL TESTS ====================================================================

class TestCalculateRiskLevel:
    """Test the calculate_risk_level() function"""
    
    def test_adds_risk_level_column(self, consecutive_rentals):
        """Verify that the 'risk_level' column is created"""
        result = calculate_risk_level(consecutive_rentals)
        assert 'risk_level' in result.columns, "Missing 'risk_level' column"
    
    def test_returns_dataframe(self, consecutive_rentals):
        """Verify that the function returns a DataFrame"""
        result = calculate_risk_level(consecutive_rentals)
        assert isinstance(result, pd.DataFrame), "The function does not return a DataFrame"
    

    def test_critical_case(self):
        """Verify that delay > time_delta is categorized as 'Critical'"""
        df = pd.DataFrame({
            'delay_at_checkout_in_minutes': [150.0],
            'time_delta_with_previous_rental_in_minutes': [100.0]
        })
        result = calculate_risk_level(df)
        
        assert result['risk_level'].iloc[0] == 'Critical (delay > buffer)', \
            "Delay > buffer should be 'Critical', got: " + result['risk_level'].iloc[0]


class TestCalculateThresholdImpact:
    """Test the calculate_threshold_impact() function"""
    
    def test_requires_risk_level(self, consecutive_rentals):
        """Verify that the function raises an error if risk_level is missing"""
        with pytest.raises(ValueError, match="risk_level"):
            calculate_threshold_impact(consecutive_rentals, threshold=90)
    
    def test_returns_dict_with_required_keys(self, df_with_risk):
        """Verify that the function returns a dictionary with the correct keys"""
        result = calculate_threshold_impact(df_with_risk, threshold=90)
        
        required_keys = {
            'threshold', 'checkin_type', 'total_rentals', 'total_critical',
            'conflicts_resolved', 'pct_resolved', 'rentals_blocked', 
            'pct_blocked', 'efficiency'
        }
        
        assert set(result.keys()) == required_keys, \
            f"Missing keys: {required_keys - set(result.keys())}"


class TestWorkflow:
    """Test the complete workflow"""
    
    def test_full_workflow(self, sample_data, tmp_path):
        """Test the full workflow: load → separate → risk → threshold"""
        # Save test data
        filepath = tmp_path / "test.xlsx"
        sample_data.to_excel(filepath, index=False)
        
        # 1. Load
        df = load_and_prepare_data(str(filepath))
        assert len(df) > 0, "No data loaded"
        
        # 2. Separate
        consecutive, first = separate_rental_groups(df)
        assert len(consecutive) > 0, "No consecutive rentals found"
        
        # 3. Compute risk
        df_risk = calculate_risk_level(consecutive)
        assert 'risk_level' in df_risk.columns, "risk_level column missing"
        
        # 4. Simulate thresholds
        results = simulate_thresholds(df_risk, thresholds=[30, 60, 90])
        assert len(results) > 0, "No simulation results returned"



# EXECUTION =================================================================

if __name__ == '__main__':
    # Run with: python -m pytest test_metrics_simple.py -v
    pytest.main([__file__, '-v', '--tb=short'])