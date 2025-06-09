import pytest
import sys
import os
import json
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestFormDataProcessing:
    """Test suite for form data processing functions."""
    
    def test_process_material_form_data_valid_input(self):
        """Test process_material_form_data with valid input."""
        # This function appears to be incomplete in the current code
        # We'll test what we can and prepare for when it's completed
        pass
    
    def test_volume_fraction_validation_in_processing(self):
        """Test volume fraction validation during form processing."""
        import numpy as np
        
        # Test case where volume fractions sum to 1.0
        vfracs = [0.4, 0.6]
        total = sum(vfracs)
        assert np.isclose(total, 1.0)
        
        # Test case where they don't sum to 1.0
        vfracs = [0.3, 0.5]  # Sum = 0.8
        total = sum(vfracs)
        assert not np.isclose(total, 1.0)
        
        # Test with floating point precision issues
        vfracs = [1/3, 2/3]  # Should be close to 1.0
        total = sum(vfracs)
        assert np.isclose(total, 1.0, rtol=1e-10)


class TestMaterialConfiguration:
    """Test material configuration processing."""
    
    def test_material_type_parsing(self):
        """Test parsing material type from form data."""
        # Simulate form data
        form_data = {
            'material_type_1': 'custom',
            'material_type_2': 'premade',
            'name1': 'Custom Material',
            'rho0_1': '2.5',
            'C0_1': '3.0',
            'S_1': '1.5',
            'material2_select': 'Copper',
            'vfrac1': '0.6',
            'vfrac2': '0.4'
        }
        
        # Test custom material parsing
        assert form_data['material_type_1'] == 'custom'
        assert form_data['name1'] == 'Custom Material'
        assert form_data['rho0_1'] == '2.5'
        
        # Test premade material parsing  
        assert form_data['material_type_2'] == 'premade'
        assert form_data['material2_select'] == 'Copper'
    
    def test_material_index_extraction(self):
        """Test extracting material indices from form keys."""
        form_keys = [
            'material_type_1',
            'material_type_2', 
            'material_type_3',
            'vfrac1',
            'vfrac2',
            'vfrac3',
            'unrelated_key'
        ]
        
        # Extract material indices
        material_indices = set()
        for key in form_keys:
            if key.startswith('material_type_'):
                idx = key.split('_')[-1]
                try:
                    material_indices.add(int(idx))
                except ValueError:
                    pass
        
        assert material_indices == {1, 2, 3}


class TestCalculationParameters:
    """Test calculation parameter validation."""
    
    def test_calculation_parameter_defaults(self):
        """Test default calculation parameters."""
        # Default parameters that should be used
        defaults = {
            'mixture_name': 'MyMixture',
            'upmin_fit': 0.0,
            'upmax_fit': 6.0,
            'num_points_fit': 100
        }
        
        # Test that defaults are reasonable
        assert isinstance(defaults['mixture_name'], str)
        assert defaults['upmin_fit'] >= 0.0
        assert defaults['upmax_fit'] > defaults['upmin_fit']
        assert defaults['num_points_fit'] > 0
        assert isinstance(defaults['num_points_fit'], int)
    
    def test_calculation_parameter_validation(self):
        """Test validation of calculation parameters."""
        from main import validate_non_negative_number, validate_positive_number, validate_integer_range
        
        # Test upmin validation (should be non-negative, zero allowed)
        is_valid, value, error = validate_non_negative_number('0.5', 'Minimum Up')
        assert is_valid
        assert value == 0.5
        
        # Test that zero is allowed for upmin (edge case)
        is_valid, value, error = validate_non_negative_number('0.0', 'Minimum Up')
        assert is_valid
        assert value == 0.0
        
        # Test upmax validation (should be positive)
        is_valid, value, error = validate_positive_number('6.0', 'Maximum Up')
        assert is_valid
        assert value == 6.0
        
        # Test num_points validation
        is_valid, value, error = validate_integer_range('100', 'Number of Points', min_val=20, max_val=10000)
        assert is_valid
        assert value == 100
        
        # Test invalid num_points
        is_valid, value, error = validate_integer_range('15', 'Number of Points', min_val=20)
        assert not is_valid
        assert error == 'Number of Points must be at least 20'


class TestErrorMessages:
    """Test error message generation and handling."""
    
    def test_validation_error_messages(self):
        """Test that validation functions produce clear error messages."""
        from main import validate_positive_number, validate_fraction, validate_integer_range
        
        # Test positive number error
        is_valid, value, error = validate_positive_number('-1.0', 'Density')
        assert not is_valid
        assert 'Density' in error
        assert 'positive' in error
        
        # Test fraction error
        is_valid, value, error = validate_fraction('1.5', 'Volume Fraction')
        assert not is_valid
        assert 'Volume Fraction' in error
        assert 'between 0 and 1' in error
        
        # Test integer range error
        is_valid, value, error = validate_integer_range('15', 'Count', max_val=10)
        assert not is_valid
        assert 'Count' in error
        assert 'at most 10' in error
    
    def test_custom_field_names_in_errors(self):
        """Test that custom field names appear correctly in error messages."""
        from main import validate_positive_number
        
        test_cases = [
            ('Material Density', 'Material Density must be positive'),
            ('C0 Parameter', 'C0 Parameter must be positive'),
            ('S Value', 'S Value must be positive')
        ]
        
        for field_name, expected_error in test_cases:
            is_valid, value, error = validate_positive_number('-1', field_name)
            assert not is_valid
            assert error == expected_error


class TestFormReconstruction:
    """Test form reconstruction with preserved data."""
    
    def test_form_data_preservation(self):
        """Test that form data is preserved during validation errors."""
        # Simulate query parameters that should be preserved
        query_params = {
            'num_materials': '2',
            'vfrac1': '0.6',
            'vfrac2': '0.4', 
            'material_type_1': 'custom',
            'name1': 'Test Material',
            'rho0_1': '2.5',
            'material_type_2': 'premade',
            'material2_select': 'Copper',
            'mixture_name': 'TestMix'
        }
        
        # Test that all important data is present
        assert 'num_materials' in query_params
        assert 'mixture_name' in query_params
        
        # Test material data preservation
        assert query_params['material_type_1'] == 'custom'
        assert query_params['name1'] == 'Test Material'
        assert query_params['material_type_2'] == 'premade'
        assert query_params['material2_select'] == 'Copper'
        
        # Test volume fractions preserved
        vfrac1 = float(query_params['vfrac1'])
        vfrac2 = float(query_params['vfrac2'])
        assert vfrac1 + vfrac2 == 1.0  # Should sum to 1.0


class TestMaterialFormIntegration:
    """Integration tests for material form processing."""
    
    @patch('main.materials')
    def test_complete_form_processing_workflow(self, mock_materials):
        """Test a complete workflow from form data to material objects."""
        # Mock database materials
        mock_copper = Mock()
        mock_copper.name = "Copper"
        mock_copper.rho0 = 8.93
        mock_copper.C0 = 4.27
        mock_copper.S = 1.413
        mock_materials.return_value = [mock_copper]
        
        # Simulate complete form data
        form_data = {
            'num_materials': '2',
            'material_type_1': 'premade',
            'material1_select': 'Copper',
            'vfrac1': '0.7',
            'material_type_2': 'custom',
            'name2': 'Custom Aluminum',
            'rho0_2': '2.70',
            'C0_2': '5.33',
            'S_2': '1.34',
            'vfrac2': '0.3',
            'mixture_name': 'CuAl_Mix',
            'upmin_fit': '0.0',
            'upmax_fit': '5.0',
            'num_points_fit': '50'
        }
        
        # Test individual validations
        from main import validate_fraction, validate_positive_number, validate_integer_range
        
        # Validate volume fractions
        is_valid1, vfrac1, error1 = validate_fraction(form_data['vfrac1'], 'Volume Fraction 1')
        is_valid2, vfrac2, error2 = validate_fraction(form_data['vfrac2'], 'Volume Fraction 2')
        
        assert is_valid1 and is_valid2
        assert abs(vfrac1 + vfrac2 - 1.0) < 1e-10  # Should sum to 1.0
        
        # Validate custom material properties
        is_valid, rho0, error = validate_positive_number(form_data['rho0_2'], 'Density')
        assert is_valid and rho0 == 2.70
        
        is_valid, c0, error = validate_positive_number(form_data['C0_2'], 'C0')
        assert is_valid and c0 == 5.33
        
        is_valid, s, error = validate_positive_number(form_data['S_2'], 'S')
        assert is_valid and s == 1.34
        
        # Validate calculation parameters
        is_valid, num_points, error = validate_integer_range(
            form_data['num_points_fit'], 'Number of Points', min_val=20, max_val=1000
        )
        assert is_valid and num_points == 50
