# pyright: basic
from fasthtml.common import *
from hmac import compare_digest
from dataclasses import dataclass
from passlib.context import CryptContext
import passlib.exc # Ensure this is imported for specific exception types
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
    # 'pwd' field will store the hash, or initially plain text during migration
    users.create(dict(name=str, pwd=str), pk="name")
if materials not in db.t:
    materials.create(dict(name=str, rho0=float, C0=float, S=float), pk="name")

User, Material = users.dataclass(), materials.dataclass()

# Password hashing setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

login_redir = RedirectResponse("/login", status_code=303)


def _not_found(req, exc):
    return Titled("Oh no!", Div("We could not find that page :("))


def before(req, sess):
    auth = req.scope["auth"] = sess.get("auth", None)
    if not auth:
        return login_redir


bware = Beforeware(before, skip=["/favicon\\\\.ico", "/static/.*", ".*\\\\.css", "/login"])

def _create_material_form_section(section_id: int, material_options: list, default_custom_values: dict) -> tuple:
    """Helper function to create the form section for a single material."""
    custom_radio_id = f"material{section_id}_custom_radio"
    premade_radio_id = f"material{section_id}_premade_radio"
    custom_div_id = f"material{section_id}_custom"
    premade_div_id = f"material{section_id}_premade"
    selected_hidden_id = f"material{section_id}_selected"
    select_id = f"material{section_id}_select"
    info_div_id = f"material{section_id}_info"

    name_id = f"name{section_id}"
    rho0_id = f"rho0_{section_id}"
    c0_id = f"C0_{section_id}"
    s_id = f"S_{section_id}"

    return (
        H2(f"Material {section_id}"),
        Group(
            Input(
                type="radio",
                id=custom_radio_id,
                name=f"material{section_id}_type",
                value="custom",
                style="border-radius: 0;"
            ),
            Label(f"Custom Material", for_=custom_radio_id),
            Input(
                type="radio",
                id=premade_radio_id,
                name=f"material{section_id}_type",
                value="premade",
                checked=True, # Default to premade
            ),
            Label("Premade Material", for_=premade_radio_id),
        ),
        Div(
            Group(
                Label("Name", for_=name_id),
                Input(id=name_id, name=name_id, placeholder=f"Material {section_id} Name", value=default_custom_values.get("name", ""))
            ),
            Group(
                Label("Density (g/cc)", for_=rho0_id),
                Input(id=rho0_id, name=rho0_id, placeholder=f"Density {section_id}", type="number", value=default_custom_values.get("rho0", 0.0), step="any")
            ),
            Group(
                Label("C0 (km/s)", for_=c0_id),
                Input(id=c0_id, name=c0_id, placeholder=f"C0 {section_id}", type="number", value=default_custom_values.get("C0", 0.0), step="any")
            ),
            Group(
                Label("S (dimensionless)", for_=s_id),
                Input(id=s_id, name=s_id, placeholder=f"S {section_id}", type="number", value=default_custom_values.get("S", 0.0), step="any")
            ),
            id=custom_div_id,
            style="display: none;",  # Hide custom material form by default
        ),
        Div(
            Group(
                Select(
                    *material_options,
                    id=select_id,
                    name=select_id, # Name should match the expected query param for /get_material
                    placeholder=f"Select Material {section_id}",
                    hx_get="/get_material",
                    hx_target=f"#{info_div_id}",
                    hx_trigger="change"
                )
            ),
            Div(id=info_div_id),
            id=premade_div_id,
        ),
        Input(
            type="hidden",
            id=selected_hidden_id,
            name=f"material{section_id}_selected", # This name is used in CalculationInput
            value="premade",
        )
    )

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
        user_record = users[login.name]
        stored_pwd = user_record.pwd

        is_identified_hash = False
        if isinstance(stored_pwd, str) and stored_pwd:
            try:
                pwd_context.identify(stored_pwd)
                is_identified_hash = True
            except passlib.exc.UnknownHashError:
                is_identified_hash = False
            except (ValueError, TypeError):
                is_identified_hash = False
        else:
            is_identified_hash = False

        if is_identified_hash:
            if pwd_context.verify(login.pwd, stored_pwd):
                sess["auth"] = user_record.name
                return RedirectResponse("/", status_code=303)
            else:
                return login_redir
        else:
            plain_stored_pwd_for_compare = stored_pwd if isinstance(stored_pwd, str) else ""
            if compare_digest(plain_stored_pwd_for_compare.encode("utf-8"), login.pwd.encode("utf-8")):
                new_pwd_hash = pwd_context.hash(login.pwd)
                users.update({"pwd": new_pwd_hash}, user_record.name)
                sess["auth"] = user_record.name
                return RedirectResponse("/", status_code=303)
            else:
                return login_redir

    except NotFoundError:
        pwd_hash = pwd_context.hash(login.pwd)
        users.insert({"name": login.name, "pwd": pwd_hash})
        sess["auth"] = login.name
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
        *(_create_material_form_section(1, material_options, {"name": "MgO", "rho0": 3.583, "C0": 6.661, "S": 1.36})),
        *(_create_material_form_section(2, material_options, {"name": "Epoxy", "rho0": 1.2, "C0": 2.9443, "S": 1.3395})),
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
    return Titled("Calculation App", top, form, warning, plot_container)


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
def get(material1_select: str = None, material2_select: str = None):
    name_to_fetch = material1_select or material2_select
    if not name_to_fetch:
        return P("Please select a material.", style="color:orange;")
    try:
        material = materials[name_to_fetch]
        return Table(
            Tr(Th("Name"), Td(material.name)),
            Tr(Th("Density"), Td(material.rho0)),
            Tr(Th("C0"), Td(material.C0)),
            Tr(Th("S"), Td(material.S)),
        )
    except NotFoundError:
        return P("Material not found.", style="color:red;")


