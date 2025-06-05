import numpy as np
from typing import List
from dataclasses import dataclass
from fasthtml.common import * 
import plotly.graph_objs as go


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

