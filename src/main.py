# pyright: basic
from fasthtml.common import *
from hmac import compare_digest
from typing import List
from dataclasses import dataclass
from components import (
    HugoniotEOS,
    MixedHugoniotEOS,
    convert_volfrac_to_massfrac,
    generate_mixed_hugoniot,
    plot_mixture,
)

# Database setup
db = database("data/calcapp.db")
users, materials = db.t.users, db.t.materials

if users not in db.t:
    users.create(dict(name=str, pwd=str), pk="name")
if materials not in db.t:
    materials.create(dict(name=str, rho0=float, C0=float, S=float), pk="name")

User, Material = users.dataclass(), materials.dataclass()

login_redir = RedirectResponse("/login", status_code=303)


def _not_found(req, exc):
    return Titled("Oh no!", Div("We could not find that page :("))


def before(req, sess):
    auth = req.scope["auth"] = sess.get("auth", None)
    if not auth:
        return login_redir


bware = Beforeware(before, skip=["/favicon\\.ico", "/static/.*", ".*\\.css", "/login"])

script = """
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded and parsed');

    function updateMaterialForm(materialType, customDivId, premadeDivId, hiddenInputId) {
        if (materialType === 'custom') {
            document.getElementById(customDivId).style.display = 'block';
            document.getElementById(premadeDivId).style.display = 'none';
            document.getElementById(hiddenInputId).value = 'custom';
        } else {
            document.getElementById(customDivId).style.display = 'none';
            document.getElementById(premadeDivId).style.display = 'block';
            document.getElementById(hiddenInputId).value = 'premade';
        }
    }

    document.querySelectorAll('input[name="material1_type"]').forEach((elem) => {
        console.log('Attaching event listener to material1_type radio buttons');
        elem.addEventListener('change', function() {
            console.log('material1_type changed to', this.value);
            updateMaterialForm(this.value, 'material1_custom', 'material1_premade', 'material1_selected');
        });
    });

    document.querySelectorAll('input[name="material2_type"]').forEach((elem) => {
        console.log('Attaching event listener to material2_type radio buttons');
        elem.addEventListener('change', function() {
            console.log('material2_type changed to', this.value);
            updateMaterialForm(this.value, 'material2_custom', 'material2_premade', 'material2_selected');
        });
    });

    // Check initial state of radio buttons
    const material1Type = document.querySelector('input[name="material1_type"]:checked').value;
    updateMaterialForm(material1Type, 'material1_custom', 'material1_premade', 'material1_selected');
    const material2Type = document.querySelector('input[name="material2_type"]:checked').value;
    updateMaterialForm(material2Type, 'material2_custom', 'material2_premade', 'material2_selected');

    document.getElementById('material1_select').addEventListener('change', function() {
        console.log('material1_select changed to', this.value);
        fetch(`/get_material?name=${this.value}`)
            .then(response => response.json())
            .then(data => {
                document.getElementById('material1_info').innerHTML = `
                    <table>
                        <tr><th>Name</th><td>${data.name}</td></tr>
                        <tr><th>Density</th><td>${data.rho0}</td></tr>
                        <tr><th>C0</th><td>${data.C0}</td></tr>
                        <tr><th>S</th><td>${data.S}</td></tr>
                    </table>
                `;
            });
    });

    document.getElementById('material2_select').addEventListener('change', function() {
        console.log('material2_select changed to', this.value);
        fetch(`/get_material?name=${this.value}`)
            .then(response => response.json())
            .then(data => {
                document.getElementById('material2_info').innerHTML = `
                    <table>
                        <tr><th>Name</th><td>${data.name}</td></tr>
                        <tr><th>Density</th><td>${data.rho0}</td></tr>
                        <tr><th>C0</th><td>${data.C0}</td></tr>
                        <tr><th>S</th><td>${data.S}</td></tr>
                    </table>
                `;
            });
    });
});
"""

app = FastHTML(
    before=bware,
    exception_handlers={404: _not_found},
    hdrs=(picolink, Style(":root { --pico-font-size: 100%; }"), Script(script)),
)
rt = app.route


@dataclass
class Login:
    name: str
    pwd: str


@rt("/login")
def get():
    frm = Form(
        Input(id="name", placeholder="Name"),
        Input(id="pwd", type="password", placeholder="Password"),
        Button("login"),
        action="/login",
        method="post",
    )
    return Titled("Login", frm, H3("First time login will create your account. Do not reuse passwords from other websites on this website."))


@rt("/login")
def post(login: Login, sess):
    if not login.name or not login.pwd:
        return login_redir
    try:
        u = users[login.name]
    except NotFoundError:
        u = users.insert(login)
    if not compare_digest(u.pwd.encode("utf-8"), login.pwd.encode("utf-8")):
        return login_redir
    sess["auth"] = u.name
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(sess):
    del sess["auth"]
    return login_redir


@rt("/")
def get(auth):
    title = f"Calculation App for {auth}"
    top = Grid(
        H1(title),
        Div(
            A("logout", href="/logout"),
            " | ",
            A("Add Material", href="/admin/add_material"),
            style="text-align: right",
        ),
    )
    material_options = [
        Option("Select from dropdown", value="", disabled=True, selected=True)
    ] + [Option(material.name, value=material.name) for material in materials()]

    form = Form(
        H2("Material 1"),
        Group(
            Input(
                type="radio",
                id="material1_custom_radio",
                name="material1_type",
                value="custom",
                style="border-radius: 0;"
            ),
            Label("Custom Material", for_="material1_custom_radio"),
            Input(
                type="radio",
                id="material1_premade_radio",
                name="material1_type",
                value="premade",
                checked=True,
            ),
            Label("Premade Material", for_="material1_premade_radio"),
        ),
        Div(
            Group(
                Label("Name",for_="name1", ),
                Input(
                    id="name1", name="name1", placeholder="Material 1 Name", value="MgO"
                )
            ),
            Group(
                Label("density",for_="rho0_1", ),
                Input(
                    id="rho0_1",
                    name="rho0_1",
                    placeholder="Density 1",
                    type="number",
                    value=3.583,
                    step=1e-05,
                ),
            ),
            Group(
                Label("C0",for_="C0_1"),
                Input(
                    id="C0_1",
                    name="C0_1",
                    placeholder="C0 1",
                    type="number",
                    value=6.661,
                    step=1e-05,
                )
            ),
            Group(
                Label("S",for_="S_1"),
                Input(
                    id="S_1",
                    name="S_1",
                    placeholder="S 1",
                    type="number",
                    value=1.36,
                    step=1e-05,
                )
            ),
            id="material1_custom",
            style="display: none;",  # Hide custom material form by default
        ),
        Div(
            Group(
                Select(
                    *material_options,
                    id="material1_select",
                    name="material1_select",
                    placeholder="Select Material 1",
                )
            ),
            Div(id="material1_info"),
            id="material1_premade",
        ),
        Input(
            type="hidden",
            id="material1_selected",
            name="material1_selected",
            value="premade",
        ),  # Hidden input for selected material type
        H2("Material 2"),
        Group(
            Input(
                type="radio",
                id="material2_custom_radio",
                name="material2_type",
                value="custom",
                style="border-radius: 0;"
            ),
            Label("Custom Material", for_="material2_custom_radio"),
            Input(
                type="radio",
                id="material2_premade_radio",
                name="material2_type",
                value="premade",
                checked=True,
            ),
            Label("Premade Material", for_="material2_premade_radio"),
        ),
        Div(
            Group(
                Label("Name", for_="name2"),
                Input(
                    id="name2",
                    name="name2",
                    placeholder="Material 2 Name",
                    value="Epoxy",
                )
            ),
            Group(
                Label("density",for_="rho0_2"),
                Input(
                    id="rho0_2",
                    name="rho0_2",
                    placeholder="Density 2",
                    type="number",
                    value=1.2,
                    step=1e-05,
                )
            ),
            Group(
                Label("C0",for_="C0_2"),
                Input(
                    id="C0_2",
                    name="C0_2",
                    placeholder="C0 2",
                    type="number",
                    value=2.9443,
                    step=1e-05,
                )
            ),
            Group(
                Label("S",for_="S_2"),
                Input(
                    id="S_2",
                    name="S_2",
                    placeholder="S 2",
                    type="number",
                    value=1.3395,
                    step=1e-05,
                )
            ),
            id="material2_custom",
            style="display: none;",  # Hide custom material form by default
        ),
        Div(
            Group(
                Select(
                    *material_options,
                    id="material2_select",
                    name="material2_select",
                    placeholder="Select Material 2",
                )
            ),
            Div(id="material2_info"),
            id="material2_premade",
        ),
        Input(
            type="hidden",
            id="material2_selected",
            name="material2_selected",
            value="premade",
        ),  # Hidden input for selected material type
        Hr(),  # Add a horizontal rule for visual separation
        H2("Calculation Parameters"),
        Group(
            Label("Volume fraction of Material 1", for_="volpercent"),
            Input(
                id="volpercent",
                name="volpercent",
                placeholder="Volume Percent",
                type="number",
                value=0.4,
                step=0.01,
            ),
        ),
        Group(
            Label("Minimum Up to fit", for_="upmin"),
            Input(
                id="upmin",
                name="upmin",
                placeholder="Upmin",
                type="number",
                value=0,
                step=0.01,
            ),
        ),
        Group(
            Label("Maximum Up to fit", for_="upmax"),
            Input(
                id="upmax",
                name="upmax",
                placeholder="Upmax",
                type="number",
                value=6,
                step=0.01,
            ),
        ),
        Button("Calculate", type="submit"),
        action="/calculate",
        method="post",
        hx_boost="true",
        hx_target="#plot-container",
        hx_swap="innerHTML",
    )
    warning = H4("Please give this a few seconds to calculate")
    plot_container = Div(id="plot-container")
    return Titled("Calculation App", top, form,warning,  plot_container)


@dataclass
class CalculationInput:
    material1_type: str
    material2_type: str
    name1: str = ""
    rho0_1: float = 0.0
    C0_1: float = 0.0
    S_1: float = 0.0
    material1_select: str = ""
    name2: str = ""
    rho0_2: float = 0.0
    C0_2: float = 0.0
    S_2: float = 0.0
    material2_select: str = ""
    volpercent: float = 0.0
    upmin: float = 0.0
    upmax: float = 6.0


@rt("/calculate")
def post(calc_input: CalculationInput):
    if calc_input.material1_type == "premade" and calc_input.material1_select:
        premade_material1 = materials[calc_input.material1_select]
        material1 = HugoniotEOS(
            name=premade_material1.name,
            rho0=premade_material1.rho0,
            C0=premade_material1.C0,
            S=premade_material1.S,
        )
    else:
        material1 = HugoniotEOS(
            name=calc_input.name1,
            rho0=calc_input.rho0_1,
            C0=calc_input.C0_1,
            S=calc_input.S_1,
        )

    if calc_input.material2_type == "premade" and calc_input.material2_select:
        premade_material2 = materials[calc_input.material2_select]
        material2 = HugoniotEOS(
            name=premade_material2.name,
            rho0=premade_material2.rho0,
            C0=premade_material2.C0,
            S=premade_material2.S,
        )
    else:
        material2 = HugoniotEOS(
            name=calc_input.name2,
            rho0=calc_input.rho0_2,
            C0=calc_input.C0_2,
            S=calc_input.S_2,
        )

    plot_html = plot_mixture(
        material1, material2, calc_input.volpercent, calc_input.upmin, calc_input.upmax
    )
    return plot_html


@dataclass
class MaterialInput:
    name: str
    rho0: float
    C0: float
    S: float


@rt("/admin/add_material")
def get(auth):
    if auth != "admin":
        return RedirectResponse("/", status_code=303)
    form = Form(
        Group(Input(id="name", name="name", placeholder="Material Name")),
        Group(
            Input(
                id="rho0", name="rho0", placeholder="Density", type="number", step=1e-05
            )
        ),
        Group(Input(id="C0", name="C0", placeholder="C0", type="number", step=1e-05)),
        Group(Input(id="S", name="S", placeholder="S", type="number", step=1e-05)),
        Button("Add Material", type="submit"),
        action="/admin/add_material",
        method="post",
    )
    return Titled("Add Material", form)


@rt("/admin/add_material")
def post(material_input: MaterialInput, auth):
    if auth != "admin":
        return RedirectResponse("/", status_code=303)
    materials.insert(material_input)
    return RedirectResponse("/admin/add_material", status_code=303)


@rt("/get_material")
def get(name: str):
    material = materials[name]
    material_dict = {
        "name": material.name,
        "rho0": material.rho0,
        "C0": material.C0,
        "S": material.S,
    }
    return JSONResponse(material_dict)


