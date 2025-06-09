import pytest
import sys
import os
import tempfile
from unittest.mock import Mock, patch
import numpy as np

# Add src directory to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        temp_db_path = f.name
    
    # Mock the database path to use our temporary file
    with patch('main.database') as mock_db:
        yield mock_db, temp_db_path
    
    # Clean up
    try:
        os.unlink(temp_db_path)
    except OSError:
        pass

@pytest.fixture 
def sample_materials():
    """Sample materials for testing."""
    return [
        {"name": "Test Material 1", "rho0": 2.5, "C0": 3.0, "S": 1.5},
        {"name": "Test Material 2", "rho0": 8.9, "C0": 4.2, "S": 1.4},
        {"name": "Test Material 3", "rho0": 1.0, "C0": 1.5, "S": 2.0},
    ]

@pytest.fixture
def test_hugoniot_eos():
    """Create test HugoniotEOS instances."""
    from components import HugoniotEOS
    
    copper = HugoniotEOS(name="Copper", rho0=8.93, C0=4.27, S=1.413)
    aluminum = HugoniotEOS(name="Aluminum", rho0=2.785, C0=5.328, S=1.338)
    
    return copper, aluminum

@pytest.fixture
def sample_form_data():
    """Sample form data for testing."""
    return {
        'num_materials': '2',
        'material_type_1': 'premade',
        'material1_select': 'Copper',
        'vfrac1': '0.6',
        'material_type_2': 'custom',
        'name2': 'Custom Material',
        'rho0_2': '2.5',
        'C0_2': '3.0',
        'S_2': '1.5',
        'vfrac2': '0.4',
        'mixture_name': 'Test Mixture',
        'upmin_fit': '0.0',
        'upmax_fit': '6.0',
        'num_points_fit': '100'
    }
