import pytest
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import validate_positive_number, validate_fraction, validate_integer_range, validate_non_negative_number


class TestValidatePositiveNumber:
    """Test suite for validate_positive_number function."""
    
    def test_valid_positive_numbers(self):
        """Test valid positive numbers."""
        # Integer as string
        is_valid, value, error = validate_positive_number("5", "test_field")
        assert is_valid == True
        assert value == 5.0
        assert error == ""
        
        # Float as string
        is_valid, value, error = validate_positive_number("3.14", "test_field")
        assert is_valid == True
        assert value == 3.14
        assert error == ""
        
        # Very small positive number
        is_valid, value, error = validate_positive_number("0.001", "test_field")
        assert is_valid == True
        assert value == 0.001
        assert error == ""
        
        # Large number
        is_valid, value, error = validate_positive_number("1000000", "test_field")
        assert is_valid == True
        assert value == 1000000.0
        assert error == ""
    
    def test_zero_and_negative_numbers(self):
        """Test zero and negative numbers (should fail)."""
        # Zero
        is_valid, value, error = validate_positive_number("0", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be positive"
        
        # Negative integer
        is_valid, value, error = validate_positive_number("-5", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be positive"
        
        # Negative float
        is_valid, value, error = validate_positive_number("-3.14", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be positive"
    
    def test_invalid_strings(self):
        """Test invalid string inputs."""
        # Non-numeric string
        is_valid, value, error = validate_positive_number("abc", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be a valid number"
        
        # Empty string
        is_valid, value, error = validate_positive_number("", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be a valid number"
        
        # Mixed string
        is_valid, value, error = validate_positive_number("5abc", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be a valid number"
        
        # Special characters
        is_valid, value, error = validate_positive_number("$5.00", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be a valid number"
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Scientific notation
        is_valid, value, error = validate_positive_number("1e-5", "test_field")
        assert is_valid == True
        assert value == 1e-5
        assert error == ""
        
        # Leading/trailing whitespace (should fail with current implementation)
        is_valid, value, error = validate_positive_number(" 5.0 ", "test_field")
        assert is_valid == True  # float() handles whitespace
        assert value == 5.0
        assert error == ""
    
    def test_custom_field_names(self):
        """Test that custom field names appear in error messages."""
        is_valid, value, error = validate_positive_number("-1", "Density")
        assert error == "Density must be positive"
        
        is_valid, value, error = validate_positive_number("abc", "Material C0")
        assert error == "Material C0 must be a valid number"


class TestValidateNonNegativeNumber:
    """Test suite for validate_non_negative_number function."""
    
    def test_valid_non_negative_numbers(self):
        """Test valid non-negative numbers including zero."""
        # Zero should be valid
        is_valid, value, error = validate_non_negative_number("0", "test_field")
        assert is_valid == True
        assert value == 0.0
        assert error == ""
        
        # Positive numbers should be valid
        is_valid, value, error = validate_non_negative_number("5.5", "test_field")
        assert is_valid == True
        assert value == 5.5
        assert error == ""
        
        # Very small positive number
        is_valid, value, error = validate_non_negative_number("0.001", "test_field")
        assert is_valid == True
        assert value == 0.001
        assert error == ""
    
    def test_negative_numbers_rejected(self):
        """Test that negative numbers are rejected."""
        is_valid, value, error = validate_non_negative_number("-1.0", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be non-negative"
        
        is_valid, value, error = validate_non_negative_number("-0.001", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be non-negative"
    
    def test_invalid_strings(self):
        """Test invalid string inputs."""
        is_valid, value, error = validate_non_negative_number("abc", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be a valid number"


class TestValidateFraction:
    """Test suite for validate_fraction function."""
    
    def test_valid_fractions(self):
        """Test valid fraction values (0 to 1)."""
        # Zero
        is_valid, value, error = validate_fraction("0", "test_field")
        assert is_valid == True
        assert value == 0.0
        assert error == ""
        
        # One
        is_valid, value, error = validate_fraction("1", "test_field")
        assert is_valid == True
        assert value == 1.0
        assert error == ""
        
        # Middle value
        is_valid, value, error = validate_fraction("0.5", "test_field")
        assert is_valid == True
        assert value == 0.5
        assert error == ""
        
        # Near boundaries
        is_valid, value, error = validate_fraction("0.001", "test_field")
        assert is_valid == True
        assert value == 0.001
        assert error == ""
        
        is_valid, value, error = validate_fraction("0.999", "test_field")
        assert is_valid == True
        assert value == 0.999
        assert error == ""
    
    def test_out_of_range_values(self):
        """Test values outside 0-1 range."""
        # Negative
        is_valid, value, error = validate_fraction("-0.1", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be between 0 and 1"
        
        # Greater than 1
        is_valid, value, error = validate_fraction("1.1", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be between 0 and 1"
        
        # Much greater than 1
        is_valid, value, error = validate_fraction("5", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be between 0 and 1"
    
    def test_invalid_strings(self):
        """Test invalid string inputs."""
        # Non-numeric string
        is_valid, value, error = validate_fraction("abc", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be a valid number"
        
        # Empty string
        is_valid, value, error = validate_fraction("", "test_field")
        assert is_valid == False
        assert value == 0.0
        assert error == "test_field must be a valid number"
    
    def test_custom_field_names(self):
        """Test that custom field names appear in error messages."""
        is_valid, value, error = validate_fraction("2", "Volume Fraction")
        assert error == "Volume Fraction must be between 0 and 1"
        
        is_valid, value, error = validate_fraction("abc", "Material Fraction")
        assert error == "Material Fraction must be a valid number"


class TestValidateIntegerRange:
    """Test suite for validate_integer_range function."""
    
    def test_valid_integers_no_range(self):
        """Test valid integers without range constraints."""
        is_valid, value, error = validate_integer_range("5", "test_field")
        assert is_valid == True
        assert value == 5
        assert error == ""
        
        is_valid, value, error = validate_integer_range("-3", "test_field")
        assert is_valid == True
        assert value == -3
        assert error == ""
        
        is_valid, value, error = validate_integer_range("0", "test_field")
        assert is_valid == True
        assert value == 0
        assert error == ""
    
    def test_valid_integers_with_min_constraint(self):
        """Test integers with minimum value constraint."""
        is_valid, value, error = validate_integer_range("5", "test_field", min_val=1)
        assert is_valid == True
        assert value == 5
        assert error == ""
        
        # At boundary
        is_valid, value, error = validate_integer_range("1", "test_field", min_val=1)
        assert is_valid == True
        assert value == 1
        assert error == ""
        
        # Below minimum
        is_valid, value, error = validate_integer_range("0", "test_field", min_val=1)
        assert is_valid == False
        assert value == 0
        assert error == "test_field must be at least 1"
    
    def test_valid_integers_with_max_constraint(self):
        """Test integers with maximum value constraint."""
        is_valid, value, error = validate_integer_range("5", "test_field", max_val=10)
        assert is_valid == True
        assert value == 5
        assert error == ""
        
        # At boundary
        is_valid, value, error = validate_integer_range("10", "test_field", max_val=10)
        assert is_valid == True
        assert value == 10
        assert error == ""
        
        # Above maximum
        is_valid, value, error = validate_integer_range("11", "test_field", max_val=10)
        assert is_valid == False
        assert value == 0
        assert error == "test_field must be at most 10"
    
    def test_valid_integers_with_both_constraints(self):
        """Test integers with both min and max constraints."""
        # Valid within range
        is_valid, value, error = validate_integer_range("5", "test_field", min_val=1, max_val=10)
        assert is_valid == True
        assert value == 5
        assert error == ""
        
        # At lower boundary
        is_valid, value, error = validate_integer_range("1", "test_field", min_val=1, max_val=10)
        assert is_valid == True
        assert value == 1
        assert error == ""
        
        # At upper boundary
        is_valid, value, error = validate_integer_range("10", "test_field", min_val=1, max_val=10)
        assert is_valid == True
        assert value == 10
        assert error == ""
        
        # Below range
        is_valid, value, error = validate_integer_range("0", "test_field", min_val=1, max_val=10)
        assert is_valid == False
        assert value == 0
        assert error == "test_field must be at least 1"
        
        # Above range
        is_valid, value, error = validate_integer_range("11", "test_field", min_val=1, max_val=10)
        assert is_valid == False
        assert value == 0
        assert error == "test_field must be at most 10"
    
    def test_float_strings_converted_to_int(self):
        """Test that float strings are converted to integers."""
        is_valid, value, error = validate_integer_range("5.0", "test_field")
        assert is_valid == True
        assert value == 5
        assert error == ""
        
        # Float with decimal part should truncate
        is_valid, value, error = validate_integer_range("5.7", "test_field")
        assert is_valid == True
        assert value == 5  # int() truncates
        assert error == ""
    
    def test_invalid_strings(self):
        """Test invalid string inputs."""
        # Non-numeric string
        is_valid, value, error = validate_integer_range("abc", "test_field")
        assert is_valid == False
        assert value == 0
        assert error == "test_field must be a valid integer"
        
        # Empty string
        is_valid, value, error = validate_integer_range("", "test_field")
        assert is_valid == False
        assert value == 0
        assert error == "test_field must be a valid integer"
        
        # Mixed string
        is_valid, value, error = validate_integer_range("5abc", "test_field")
        assert is_valid == False
        assert value == 0
        assert error == "test_field must be a valid integer"
    
    def test_custom_field_names_and_ranges(self):
        """Test that custom field names and ranges appear in error messages."""
        is_valid, value, error = validate_integer_range("0", "Number of Materials", min_val=1, max_val=10)
        assert error == "Number of Materials must be at least 1"
        
        is_valid, value, error = validate_integer_range("15", "Point Count", min_val=1, max_val=10)
        assert error == "Point Count must be at most 10"
        
        is_valid, value, error = validate_integer_range("abc", "User Input", min_val=1)
        assert error == "User Input must be a valid integer"
