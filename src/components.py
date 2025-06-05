import numpy as np
from typing import List, Tuple # Ensure Tuple is imported
import numpy.typing as npt # Added for npt.ArrayLike
from dataclasses import dataclass
from fasthtml.common import * 
import plotly.graph_objs as go
from scipy.stats import linregress as LR # Added for generate_mixed_hugoniot_many


@dataclass
class HugoniotEOS:
    name: str
    rho0: float
    C0: float
    S: float

    def hugoniot_eos(self, up):
        Us = self.C0 + self.S * up
        return Us

    def hugoniot_P(self, up):
        Us = self.hugoniot_eos(up)
        P = self.rho0 * Us * up
        return P

    def solve_up(self, P):
        a = self.S
        b = self.C0
        c = -P / self.rho0
        Up = (-b + np.sqrt(b**2 - 4 * a * c)) / (2 * a)
        return Up


@dataclass
class MixedHugoniotEOS(HugoniotEOS):
    components: List[str]
    vfracs: List[float]


def convert_volfrac_to_massfrac(rho1, rho2, Vx1):
    mass_1 = rho1 * Vx1
    mass_2 = rho2 * (1 - Vx1)
    x1 = mass_1 / (mass_1 + mass_2)
    return x1


def generate_mixed_hugoniot(
    name, material1, material2, Vx_mat1, Up=np.linspace(0, 8, 1000)
):
    P = material1.hugoniot_P(Up)
    material1Up = Up
    material2Up = material2.solve_up(P)
    mass_mat1 = material1.rho0 * Vx_mat1
    mass_mat2 = material2.rho0 * (1 - Vx_mat1)
    x_mat1 = convert_volfrac_to_massfrac(material1.rho0, material2.rho0, Vx_mat1)
    rho_mix = (mass_mat1 + mass_mat2) / (
        mass_mat1 / material1.rho0 + mass_mat2 / material2.rho0
    )
    mixed_Up = np.sqrt(material1Up**2 * x_mat1 + material2Up**2 * (1 - x_mat1))
    mixed_Us = P[1:] / (rho_mix * mixed_Up[1:])
    regression = np.polyfit(mixed_Up[1:], mixed_Us, 1)
    names = [material1.name, material2.name]
    vols = [Vx_mat1, 1 - Vx_mat1]
    mfracs = [x_mat1, 1 - x_mat1]
    mixed = MixedHugoniotEOS(name, rho_mix, regression[1], regression[0], names, vols)
    mixed.mfracs = mfracs
    return mixed


def generate_table(c0_values, s_values, rho_values, ):
    # Create the basic structure of the table
    table = Table(
        Tr(
            Th('C0'),
            Th('S'),
            Th('rho'),
        ),

        Tr(
            Td(c0_values),
            Td(s_values),
            Td(rho_values),
        )
    )
    
    return table

def plot_mixture(material1, material2, volpercent, upmin=0, upmax=6):
    up1 = np.linspace(upmin, upmax, 1000)
    mix = generate_mixed_hugoniot(
        f"vol{str(volpercent) + material1.name + material2.name}",
        material1,
        material2,
        volpercent,
        up1,
    )
    P = material1.hugoniot_P(up1)
    upmix = mix.solve_up(P)
    up2 = material2.solve_up(P)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=up1,
            y=P,
            mode="lines",
            name=material1.name,
            line=dict(color="blue", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=material2.solve_up(P),
            y=P,
            mode="lines",
            name=material2.name,
            line=dict(color="red", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=mix.solve_up(P),
            y=P,
            mode="lines",
            name=f"{mix.vfracs[0] * 100:.1f} %v {material1.name}",
            line=dict(color="magenta", dash="dash", width=3),
        )
    )
    fig.update_layout(
        title="Pressure vs Particle Velocity",
        xaxis_title="up (km/s)",
        yaxis_title="P (GPa)",
        legend=dict(font=dict(size=14)),
    )
    fig2 = go.Figure()
    fig2.add_trace(
        go.Scatter(
            x=up1,
            y=mix.hugoniot_eos(up1),
            mode="lines",
            name=f"{mix.vfracs[0] * 100:.1f} %v {material1.name}",
            line=dict(color="magenta", dash="dash", width=3),
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=up1,
            y=material1.hugoniot_eos(up1),
            mode="lines",
            name=material1.name,
            line=dict(color="blue", width=3),
        )
    )
    fig2.add_trace(
        go.Scatter(
            x=up1,
            y=material2.hugoniot_eos(up1),
            mode="lines",
            name=material2.name,
            line=dict(color="red", width=3),
        )
    )
    fig2.update_layout(
        title="Shock Velocity vs Particle Velocity",
        xaxis_title="Up",
        yaxis_title="Us",
        legend=dict(font=dict(size=14)),
    )
    mixedtable = generate_table(mix.C0, mix.S, mix.rho0)
    newdiv = Div(mixedtable,NotStr(fig.to_html(full_html=False)), NotStr(fig2.to_html(full_html=False)), )

    return newdiv


# New function for generating mixed Hugoniot for multiple materials
def generate_mixed_hugoniot_many(name: str, material_data_list: List[Tuple[HugoniotEOS, float]], Up_ref: npt.ArrayLike) -> MixedHugoniotEOS:
    """
    Generates a mixed Hugoniot for a given list of materials and their volume fractions.
    :param name: name of new mixture
    :param material_data_list: list of tuples containing the material EOS and its respective volume fraction [(mat1_eos, vx1), ...]
    :param Up_ref: array of particle velocities to solve for. This will be applied to the first material to get a P, 
                   after which Up will be solved for other materials at these pressures.
    :returns: MixedHugoniotEOS
    :raises ValueError: if sum of volume fractions is not close to 1 or material list is empty.
    """
    if not material_data_list:
        raise ValueError("Material list cannot be empty.")

    v_fracs_sum = sum(item[1] for item in material_data_list)
    if not np.isclose(v_fracs_sum, 1.0):
        raise ValueError(f"Volume fractions must sum to 1.0, but sum to {v_fracs_sum:.4f}")

    mat1_eos, _ = material_data_list[0]
    P_common = mat1_eos.hugoniot_P(Up_ref)

    component_eos_list = [item[0] for item in material_data_list]
    component_vfrac_list = [item[1] for item in material_data_list]
    component_names = [eos.name for eos in component_eos_list]

    component_up_list = [eos.solve_up(P_common) for eos in component_eos_list]
    
    masses = [eos.rho0 * vfrac for eos, vfrac in material_data_list]
    total_mass = sum(masses)
    
    # rho_mix is the sum of (rho_i * vfrac_i), which is equivalent to sum(mass_i) / sum(vol_i_total_mixture_perspective)
    # but since sum(vol_i_total_mixture_perspective) is 1 (as vfracs sum to 1), rho_mix = sum(mass_i)
    # This is the density of the mixture assuming ideal mixing of volumes.
    rho_mix = sum(eos.rho0 * vfrac for eos, vfrac in material_data_list)


    component_mass_frac_list = [m / total_mass if total_mass > 0 else 0 for m in masses]

    sum_up_squared_times_mass_frac = np.zeros_like(Up_ref, dtype=float)
    for up_item, mf_item in zip(component_up_list, component_mass_frac_list):
        up_item_arr = np.asarray(up_item) # Ensure up_item is an array for element-wise operations
        sum_up_squared_times_mass_frac += np.square(up_item_arr) * mf_item
    
    mixed_Up = np.sqrt(sum_up_squared_times_mass_frac)
    
    C0_mix, S_mix = mat1_eos.C0, 0.0 # Default fallback

    # Ensure there are enough points for regression after potentially removing the first point (Up=0)
    # And ensure mixed_Up is not all zeros or very small values that would cause issues in division
    if len(mixed_Up) > 1 and len(P_common) > 1:
        # Use indices from the second point onwards if Up_ref[0] is 0 (common case)
        # Filter out points where mixed_Up is zero or very small to avoid division by zero or large errors
        valid_fit_indices = mixed_Up[1:] > 1e-9 # Check for non-zero and non-tiny Up values
        
        if np.count_nonzero(valid_fit_indices) >= 2: # Need at least 2 points for linear regression
            up_for_fit = mixed_Up[1:][valid_fit_indices]
            # P_common[0] is typically 0 if Up_ref[0] is 0.
            # We need to align P_common with the filtered up_for_fit.
            p_for_fit = P_common[1:][valid_fit_indices]
            
            mixed_Us_calc = p_for_fit / (rho_mix * up_for_fit)
            
            if len(up_for_fit) >=2: # Check again after slicing for p_for_fit alignment
                regression = LR(up_for_fit, mixed_Us_calc)
                C0_mix = regression.intercept
                S_mix = regression.slope
            else:
                print("Warning: Not enough valid data points after aligning P and Up for Us-Up linear regression. Using C0 of first component and S=0 for mixture.")
        else:
            print("Warning: Not enough valid data points (Up_mix > 0, after excluding first point) for Us-Up linear regression. Using C0 of first component and S=0 for mixture.")
    else:
        print("Warning: Not enough data points in Up_ref for Us-Up linear regression. Using C0 of first component and S=0 for mixture.")

    mixed_eos_obj = MixedHugoniotEOS(name, rho_mix, C0_mix, S_mix, component_names, component_vfrac_list)
    mixed_eos_obj.mfracs = component_mass_frac_list
    return mixed_eos_obj

# New plot function for multiple materials using Plotly
def plot_mixture_many(original_material_configs: List[Tuple[HugoniotEOS, float]], 
                      mixed_eos: MixedHugoniotEOS, 
                      up_min: float, up_max: float, num_points: int = 200):
    
    up_plot_range = np.linspace(up_min, up_max, num_points)
    # Ensure up_plot_range is never empty or single point if up_min=up_max
    if up_min == up_max:
        if up_min == 0: up_plot_range = np.array([0, 1e-6]) # Tiny range if both are 0
        else: up_plot_range = np.array([up_min, up_min + 1e-6*(abs(up_min) if up_min !=0 else 1)])


    # P-Up plot
    fig_p_up = go.Figure()
    # Use the mixed EOS's Up range to generate a common P range for plotting consistency
    # This P_common will be used to solve for Up for all components for plotting P-Up
    P_plot_common = mixed_eos.hugoniot_P(up_plot_range)


    for i, (mat_orig, vfrac) in enumerate(original_material_configs):
        # Solve for original material's Up at the common pressure range
        up_orig_solved = mat_orig.solve_up(P_plot_common)
        fig_p_up.add_trace(go.Scatter(
            x=up_orig_solved, 
            y=P_plot_common, 
            mode='lines', 
            name=f"{mat_orig.name} ({vfrac*100:.1f}%)",
            line=dict(width=2)
        ))

    # Plot the mixed material's P-Up curve directly using its own Up range
    fig_p_up.add_trace(go.Scatter(
        x=up_plot_range, 
        y=P_plot_common, # This is P_mix
        mode='lines', 
        name=f"{mixed_eos.name} (Mix)",
        line=dict(dash='dash', width=3, color='black')
    ))
    
    fig_p_up.update_layout(
        title_text="Pressure vs. Particle Velocity",
        xaxis_title_text="Up (km/s)",
        yaxis_title_text="P (GPa)",
        legend_title_text='Materials'
    )

    # Us-Up plot
    fig_us_up = go.Figure()
    for i, (mat_orig, vfrac) in enumerate(original_material_configs):
        fig_us_up.add_trace(go.Scatter(
            x=up_plot_range, 
            y=mat_orig.hugoniot_eos(up_plot_range), 
            mode='lines', 
            name=f"{mat_orig.name} ({vfrac*100:.1f}%)",
            line=dict(width=2)
        ))
    
    fig_us_up.add_trace(go.Scatter(
        x=up_plot_range, 
        y=mixed_eos.hugoniot_eos(up_plot_range), 
        mode='lines', 
        name=f"{mixed_eos.name} (Mix)",
        line=dict(dash='dash', width=3, color='black')
    ))

    fig_us_up.update_layout(
        title_text="Shock Velocity vs. Particle Velocity",
        xaxis_title_text="Up (km/s)",
        yaxis_title_text="Us (km/s)",
        legend_title_text='Materials'
    )

    mixed_table_html = generate_table(
        f"{mixed_eos.C0:.4f}", 
        f"{mixed_eos.S:.4f}", 
        f"{mixed_eos.rho0:.4f}"
    )
    
    comp_header = [Th("Component"), Th("Vol. Frac (%)")]
    if hasattr(mixed_eos, 'mfracs') and mixed_eos.mfracs:
      comp_header.append(Th("Mass Frac (%)"))

    comp_rows = [Tr(comp_header)]
    for i, comp_name in enumerate(mixed_eos.components):
        vfrac_percent = mixed_eos.vfracs[i] * 100
        row_data = [Td(comp_name), Td(f"{vfrac_percent:.2f}")]
        if hasattr(mixed_eos, 'mfracs') and mixed_eos.mfracs and i < len(mixed_eos.mfracs):
            mfrac_percent = mixed_eos.mfracs[i] * 100
            row_data.append(Td(f"{mfrac_percent:.2f}"))
        elif hasattr(mixed_eos, 'mfracs'): # mfracs exist but maybe not for this component index
             row_data.append(Td("N/A"))
        comp_rows.append(Tr(*row_data))
        
    components_table_html = Table(*comp_rows)

    results_div = Div(
        H3("Mixture Parameters:"),
        mixed_table_html,
        H3("Component Fractions:"),
        components_table_html,
        H3("Plots:"),
        NotStr(fig_p_up.to_html(full_html=False, include_plotlyjs='cdn')),
        NotStr(fig_us_up.to_html(full_html=False, include_plotlyjs=False))
    )
    return results_div

