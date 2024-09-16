<<<<<<< Updated upstream
# pyright:basic
=======
# pyright: basic
>>>>>>> Stashed changes
import numpy as np
from typing import List
from dataclasses import dataclass
import plotly.graph_objs as go
<<<<<<< Updated upstream
from fasthtml.common import Div, Group, Label, Input, Br
=======
import numpy.typing as npt
>>>>>>> Stashed changes


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


def generate_mixed_hugoniot_many(
    name: str,
    material_list: List[Tuple[HugoniotEOS, float]],
    Up: npt.ArrayLike = np.linspace(0, 8, 1000),
) -> MixedHugoniotEOS:
    """
    Generates a mixed Hugoniot for a given list of materials and their volume percent

    :param name: name of new mixture
    :param material_list: list of tuples containing the material and it's respective volume fraction [(mat1, vx1), (mat2, vx2)]
    :param Up: array of particle velocities to solve for. This will be applied to the first material to get a P, after which
            We will solve for Up at the first materials pressures.
    :returns: MixedHugonitEOS
    :raises ValueError: raises if sum of volume percents is not equal to 1
    """
    vols = [i[1] for i in material_list]
    if np.isclose(sum(vols), 1):
        raise ValueError("Volume fractions must sum to 1")
    mat1, xv1 = material_list[0]
    P = mat1.hugoniot_P(Up)
    Up_list = [Up]
    masses = []
    vols = []
    names = []
    xvs = []
    masses.append(mat1.rho0 * xv1)
    vols.append(masses[0] / mat1.rho0)
    for mat, xv in material_list[1:]:
        names.append(mat.name)
        xvs.append(xv)
        mass = mat.rho0 * xv
        vol = mass / mat.rho0
        masses.append(mass)
        vols.append(vol)
        Up_list.append(mat.solve_up(P))
    rho_mix = sum(masses) / sum(vols)
    mass_frac = [m / sum(masses) for m in masses]
    mixed_Up = np.sqrt(sum([up**2 * x for up, x in zip(Up_list, mass_frac)]))
    mixed_Us = (P[1:]) / (rho_mix * mixed_Up[1:])
    regression = LR(mixed_Up[1:], mixed_Us)

    mixed = MixedHugoniotEOS(
        name, rho_mix, regression.intercept, regression.slope, names, xvs
    )
    mixed.mfracs = mass_frac
    return mixed


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
    return fig.to_html(full_html=False) + fig2.to_html(full_html=False)


def make_custom_mat(num: int, **kwargs):
    numstr = str(num)

    mat = Div(
        Group(
            Label("Name", for_="name" + numstr, style="margin-right: 1em"),
            Input(
                id="name" + numstr,
                name="name" + numstr,
                placeholder="Material  " + numstr + " Name",
            ),
        ),
        Group(
            Label("density", for_="rho0_" + numstr, style="margin-right: 1em"),
            Input(
                id="rho0_" + numstr,
                name="rho0_" + numstr,
                placeholder="Density " + numstr,
                type="number",
                step=1e-05,
            ),
        ),
        Group(
            Label("C0", for_="C0_" + numstr, style="margin-right: 1em"),
            Input(
                id="C0_" + numstr,
                name="C0_" + numstr,
                placeholder="C0 " + numstr,
                type="number",
                step=1e-05,
            ),
        ),
        Group(
            Label("S", for_="S_" + numstr, style="margin-right: 1em"),
            Input(
                id="S_" + numstr,
                name="S_" + numstr,
                placeholder="S " + numstr,
                type="number",
                step=1e-05,
            ),
        ),
        Br(),
        id="material" + numstr + "_custom",
        style="display: none;",  # Hide custom material form by default
        **kwargs,
    )
    return mat
