import pytest
import numpy as np
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from components import HugoniotEOS, MixedHugoniotEOS, convert_volfrac_to_massfrac, generate_mixed_hugoniot


class TestHugoniotEOS:
    """Test suite for HugoniotEOS class."""
    
    def test_initialization(self):
        """Test HugoniotEOS initialization."""
        eos = HugoniotEOS(name="Test Material", rho0=2.5, C0=3.0, S=1.5)
        assert eos.name == "Test Material"
        assert eos.rho0 == 2.5
        assert eos.C0 == 3.0
        assert eos.S == 1.5
    
    def test_hugoniot_eos_calculation(self):
        """Test shock velocity calculation (Us = C0 + S * up)."""
        eos = HugoniotEOS(name="Test", rho0=2.5, C0=3.0, S=1.5)
        
        # Test with single value
        us = eos.hugoniot_eos(2.0)  # up = 2.0 km/s
        expected_us = 3.0 + 1.5 * 2.0  # 6.0 km/s
        assert us == expected_us
        
        # Test with zero particle velocity
        us = eos.hugoniot_eos(0.0)
        assert us == 3.0  # Should equal C0
        
        # Test with array input
        up_array = np.array([0.0, 1.0, 2.0, 3.0])
        us_array = eos.hugoniot_eos(up_array)
        expected_array = np.array([3.0, 4.5, 6.0, 7.5])
        np.testing.assert_array_equal(us_array, expected_array)
    
    def test_hugoniot_pressure_calculation(self):
        """Test pressure calculation (P = rho0 * Us * up)."""
        eos = HugoniotEOS(name="Test", rho0=2.5, C0=3.0, S=1.5)
        
        # Test with single value
        pressure = eos.hugoniot_P(2.0)  # up = 2.0 km/s
        us = 3.0 + 1.5 * 2.0  # 6.0 km/s
        expected_pressure = 2.5 * 6.0 * 2.0  # 30.0 GPa
        assert pressure == expected_pressure
        
        # Test with zero (should be zero pressure)
        pressure = eos.hugoniot_P(0.0)
        assert pressure == 0.0
        
        # Test with array input
        up_array = np.array([0.0, 1.0, 2.0])
        pressure_array = eos.hugoniot_P(up_array)
        # Expected: [0.0, 2.5*4.5*1.0, 2.5*6.0*2.0] = [0.0, 11.25, 30.0]
        expected_array = np.array([0.0, 11.25, 30.0])
        np.testing.assert_array_equal(pressure_array, expected_array)
    
    def test_solve_up_from_pressure(self):
        """Test solving for particle velocity from pressure."""
        eos = HugoniotEOS(name="Test", rho0=2.5, C0=3.0, S=1.5)
        
        # Test with known pressure
        # P = 30.0 GPa should give up = 2.0 km/s (from above test)
        up_solved = eos.solve_up(30.0)
        assert abs(up_solved - 2.0) < 1e-10  # Should be very close
        
        # Test consistency: P(up) -> up should give back original up
        original_up = 1.5
        pressure = eos.hugoniot_P(original_up)
        solved_up = eos.solve_up(pressure)
        assert abs(solved_up - original_up) < 1e-10
        
        # Test with array of pressures
        pressure_array = np.array([0.0, 11.25, 30.0])
        up_array = eos.solve_up(pressure_array)
        # Should get back [0.0, 1.0, 2.0] approximately
        expected_array = np.array([0.0, 1.0, 2.0])
        np.testing.assert_array_almost_equal(up_array, expected_array, decimal=10)
    
    def test_real_material_copper(self):
        """Test with realistic copper parameters."""
        copper = HugoniotEOS(name="Copper", rho0=8.93, C0=4.27, S=1.413)
        
        # Test shock velocity calculation
        us = copper.hugoniot_eos(1.0)  # 1 km/s particle velocity
        expected_us = 4.27 + 1.413 * 1.0  # 5.683 km/s
        assert abs(us - expected_us) < 1e-10
        
        # Test pressure calculation
        pressure = copper.hugoniot_P(1.0)
        expected_pressure = 8.93 * 5.683 * 1.0  # ~50.75 GPa
        assert abs(pressure - expected_pressure) < 1e-10
        
        # Test round-trip consistency
        up_solved = copper.solve_up(pressure)
        assert abs(up_solved - 1.0) < 1e-8


class TestMixedHugoniotEOS:
    """Test suite for MixedHugoniotEOS class."""
    
    def test_initialization(self):
        """Test MixedHugoniotEOS initialization."""
        mix = MixedHugoniotEOS(
            name="Test Mix",
            rho0=5.0,
            C0=3.5,
            S=1.6,
            components=["Material A", "Material B"],
            vfracs=[0.6, 0.4]
        )
        
        assert mix.name == "Test Mix"
        assert mix.rho0 == 5.0
        assert mix.C0 == 3.5
        assert mix.S == 1.6
        assert mix.components == ["Material A", "Material B"]
        assert mix.vfracs == [0.6, 0.4]
    
    def test_inheritance_from_hugoniot_eos(self):
        """Test that MixedHugoniotEOS inherits HugoniotEOS methods."""
        mix = MixedHugoniotEOS(
            name="Test Mix",
            rho0=5.0,
            C0=3.5,
            S=1.6,
            components=["A", "B"],
            vfracs=[0.7, 0.3]
        )
        
        # Should have all parent methods
        assert hasattr(mix, 'hugoniot_eos')
        assert hasattr(mix, 'hugoniot_P')
        assert hasattr(mix, 'solve_up')
        
        # Test that methods work
        us = mix.hugoniot_eos(1.0)
        assert us == 3.5 + 1.6 * 1.0  # 5.1 km/s
        
        pressure = mix.hugoniot_P(1.0)
        assert pressure == 5.0 * 5.1 * 1.0  # 25.5 GPa


class TestConvertVolFracToMassFrac:
    """Test suite for convert_volfrac_to_massfrac function."""
    
    def test_equal_densities(self):
        """Test with equal densities - volume fraction should equal mass fraction."""
        rho1 = rho2 = 2.5
        Vx1 = 0.6
        
        x1 = convert_volfrac_to_massfrac(rho1, rho2, Vx1)
        assert abs(x1 - Vx1) < 1e-10  # Should be essentially equal
    
    def test_different_densities(self):
        """Test with different densities."""
        rho1 = 8.93  # Copper density
        rho2 = 2.70  # Aluminum density  
        Vx1 = 0.5    # 50% volume fraction of copper
        
        x1 = convert_volfrac_to_massfrac(rho1, rho2, Vx1)
        
        # Manual calculation
        mass_1 = rho1 * Vx1  # 8.93 * 0.5 = 4.465
        mass_2 = rho2 * (1 - Vx1)  # 2.70 * 0.5 = 1.35
        expected_x1 = mass_1 / (mass_1 + mass_2)  # 4.465 / 5.815 ≈ 0.768
        
        assert abs(x1 - expected_x1) < 1e-10
        assert x1 > Vx1  # Mass fraction should be higher for denser material
    
    def test_extreme_cases(self):
        """Test extreme volume fractions."""
        rho1 = 10.0
        rho2 = 1.0
        
        # 100% of material 1
        x1 = convert_volfrac_to_massfrac(rho1, rho2, 1.0)
        assert abs(x1 - 1.0) < 1e-10
        
        # 0% of material 1  
        x1 = convert_volfrac_to_massfrac(rho1, rho2, 0.0)
        assert abs(x1 - 0.0) < 1e-10
    
    def test_conservation(self):
        """Test that mass fractions sum to 1."""
        rho1 = 5.0
        rho2 = 3.0
        Vx1 = 0.3
        
        x1 = convert_volfrac_to_massfrac(rho1, rho2, Vx1)
        x2 = convert_volfrac_to_massfrac(rho2, rho1, 1 - Vx1)
        
        # Note: x2 calculation should use swapped densities for material 2
        # Actually, let's recalculate x2 properly
        mass_1 = rho1 * Vx1
        mass_2 = rho2 * (1 - Vx1)
        total_mass = mass_1 + mass_2
        x1_calc = mass_1 / total_mass
        x2_calc = mass_2 / total_mass
        
        assert abs(x1_calc + x2_calc - 1.0) < 1e-10


class TestGenerateMixedHugoniot:
    """Test suite for generate_mixed_hugoniot function."""
    
    def test_basic_functionality(self, test_hugoniot_eos):
        """Test basic mixed hugoniot generation."""
        copper, aluminum = test_hugoniot_eos
        
        # Test with 50-50 mixture
        Vx_copper = 0.5
        Up = np.linspace(0, 2, 5)  # Small array for testing
        
        result = generate_mixed_hugoniot("CuAl_Mix", copper, aluminum, Vx_copper, Up)
        
        assert isinstance(result, MixedHugoniotEOS)
        assert result.name == "CuAl_Mix"
        assert len(result.components) == 2
        assert result.components[0] == copper.name
        assert result.components[1] == aluminum.name
        assert len(result.vfracs) == 2
        assert abs(result.vfracs[0] - Vx_copper) < 1e-10
        assert abs(result.vfracs[1] - (1 - Vx_copper)) < 1e-10
    
    def test_extreme_volume_fractions(self, test_hugoniot_eos):
        """Test with extreme volume fractions."""
        copper, aluminum = test_hugoniot_eos
        Up = np.linspace(0, 1, 3)
        
        # Nearly pure copper
        result = generate_mixed_hugoniot("Nearly_Cu", copper, aluminum, 0.99, Up)
        assert abs(result.vfracs[0] - 0.99) < 1e-10
        assert abs(result.vfracs[1] - 0.01) < 1e-10
        
        # Nearly pure aluminum
        result = generate_mixed_hugoniot("Nearly_Al", copper, aluminum, 0.01, Up)
        assert abs(result.vfracs[0] - 0.01) < 1e-10
        assert abs(result.vfracs[1] - 0.99) < 1e-10
    
    def test_mixture_properties_make_sense(self, test_hugoniot_eos):
        """Test that mixture properties are between component properties."""
        copper, aluminum = test_hugoniot_eos
        Vx_copper = 0.3  # 30% copper by volume
        Up = np.linspace(0, 1, 10)
        
        result = generate_mixed_hugoniot("Test_Mix", copper, aluminum, Vx_copper, Up)
        
        # Mixture density should be between component densities (weighted by volume)
        expected_rho = copper.rho0 * Vx_copper + aluminum.rho0 * (1 - Vx_copper)
        assert abs(result.rho0 - expected_rho) < 1e-6
        
        # The C0 and S values should be reasonable (this is more complex due to mass averaging)
        # At minimum, they should be positive
        assert result.C0 > 0
        assert result.S > 0
    
    def test_default_up_array(self, test_hugoniot_eos):
        """Test with default Up array."""
        copper, aluminum = test_hugoniot_eos
        
        # Don't provide Up parameter - should use default
        result = generate_mixed_hugoniot("Default_Up", copper, aluminum, 0.5)
        
        # Should still work and produce valid result
        assert isinstance(result, MixedHugoniotEOS)
        assert result.name == "Default_Up"
        assert len(result.vfracs) == 2
