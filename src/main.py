# pyright: basic
# Explicitly import necessary symbols from fasthtml.common
from fasthtml.common import (
    FastHTML, Titled, Div, Form, Input, Button, RedirectResponse, database,
    NotFoundError, Grid, H1, A, Label, Group, Select, Option, Article, Hr, H2, H4, Table, Tr, Th, Td, NotStr, Style, Script, picolink,
    Beforeware, # Added Beforeware
    P, # Added P
    H3 # Added H3
)
from hmac import compare_digest
from dataclasses import dataclass, fields, field
from passlib.context import CryptContext
import passlib.exc # Ensure this is imported for specific exception types
from components import (
    HugoniotEOS,
    MixedHugoniotEOS,
    generate_mixed_hugoniot_many, 
    plot_mixture_many,
)
import numpy as np
from starlette.requests import Request
from starlette.datastructures import FormData
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
import os # Import os for SECRET_KEY

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


bware = Beforeware(before, skip=["/favicon\\.ico", "/static/.*", ".*\\.css", "/login"])

def _create_material_form_section(section_idx: int, material_options: list, default_custom_values: dict) -> tuple:
    """Helper function to create the form section for a single material."""
    custom_radio_id = f"material{section_idx}_custom_radio"
    premade_radio_id = f"material{section_idx}_premade_radio"
    custom_div_id = f"material{section_idx}_custom"
    premade_div_id = f"material{section_idx}_premade"
    selected_hidden_id = f"material{section_idx}_selected_type"
    select_id = f"material{section_idx}_select"
    info_div_id = f"material{section_idx}_info"

    name_id = f"name{section_idx}"
    rho0_id = f"rho0_{section_idx}"
    c0_id = f"C0_{section_idx}"
    s_id = f"S_{section_idx}"
    vfrac_id = f"vfrac{section_idx}"

    # Ensure default_custom_values for vfrac is float
    default_vfrac = default_custom_values.get("vfrac", 0.5 / section_idx if section_idx > 0 else 0.5) # Example default
    try:
        default_vfrac = float(default_vfrac)
    except (ValueError, TypeError):
        default_vfrac = 0.1


    return (
        Article( # Wrap each material section in an Article for better structure/styling
            H3(f"Material {section_idx}"),
            Group(
                Label("Type:", cls="label-inline"),
                Input( type="radio", id=custom_radio_id, name=f"material_type_{section_idx}", value="custom", data_idx=str(section_idx)),
                Label(f"Custom", for_=custom_radio_id, cls="label-inline"),
                Input( type="radio", id=premade_radio_id, name=f"material_type_{section_idx}", value="premade", checked=True, data_idx=str(section_idx)),
                Label("Premade", for_=premade_radio_id, cls="label-inline"),
            ),
            Div( # Custom material inputs
                Group(Label("Name", for_=name_id), Input(id=name_id, name=name_id, placeholder=f"Material {section_idx} Name", value=str(default_custom_values.get("name", "")))),
                Group(Label("Density (g/cc)", for_=rho0_id), Input(id=rho0_id, name=rho0_id, placeholder="Density", type="number", value=float(default_custom_values.get("rho0", 1.0)), step="any")),
                Group(Label("C0 (km/s)", for_=c0_id), Input(id=c0_id, name=c0_id, placeholder="C0", type="number", value=float(default_custom_values.get("C0", 1.5)), step="any")),
                Group(Label("S (dimensionless)", for_=s_id), Input(id=s_id, name=s_id, placeholder="S", type="number", value=float(default_custom_values.get("S", 1.5)), step="any")),
                id=custom_div_id, style="display: none;", # Hide custom material form by default
            ),
            Div( # Premade material inputs
                Group(
                    Select(
                        *material_options, id=select_id, name=select_id,
                        placeholder=f"Select Material {section_idx}",
                        hx_get="/get_material", hx_target=f"#{info_div_id}", hx_trigger="change", hx_include=f"[name='{select_id}']"
                    )
                ),
                Div(id=info_div_id),
                id=premade_div_id,
            ),
            Group( # Volume fraction input
                Label(f"Volume Fraction for Material {section_idx}", for_=vfrac_id),
                Input(id=vfrac_id, name=vfrac_id, placeholder="Volume Fraction", type="number", value=default_vfrac, step="any", min="0", max="1")
            ),
            Input(type="hidden", id=selected_hidden_id, name=selected_hidden_id, value="premade") # Stores custom/premade choice
        ) # End Article
    )

script_dynamic_materials = r"""
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded and parsed for dynamic materials');

    function updateMaterialFormVisibility(idx, materialType) {
        const customDiv = document.getElementById(`material${idx}_custom`);
        const premadeDiv = document.getElementById(`material${idx}_premade`);
        const selectedTypeInput = document.getElementById(`material${idx}_selected_type`);

        if (!customDiv || !premadeDiv || !selectedTypeInput) {
            console.error(`Elements not found for index ${idx}`);
            return;
        }

        if (materialType === 'custom') {
            customDiv.style.display = 'block';
            premadeDiv.style.display = 'none';
            selectedTypeInput.value = 'custom';
        } else { // premade
            customDiv.style.display = 'none';
            premadeDiv.style.display = 'block';
            selectedTypeInput.value = 'premade';
        }
    }

    document.body.addEventListener('change', function(event) {
        if (event.target.matches('input[type="radio"][name^="material_type_"]')) {
            const idx = event.target.dataset.idx;
            if(idx){
                console.log(`Material type changed for index ${idx} to ${event.target.value}`);
                updateMaterialFormVisibility(idx, event.target.value);
            }
        }
    });
    
    function initializeAllForms() {
        document.querySelectorAll('input[name^="material_type_"][type="radio"]:checked').forEach(radio => {
            const idx = radio.dataset.idx;
            if(idx) {
                 console.log(`Initializing form for index ${idx} with type ${radio.value}`);
                 updateMaterialFormVisibility(idx, radio.value);
            }
        });
    }

    initializeAllForms();

    document.body.addEventListener('htmx:afterSwap', function(event) {
        if (event.detail.target.id === 'material-inputs-container' || event.detail.target.closest('#material-inputs-container')) {
            console.log('HTMX swap detected in material-inputs-container, re-initializing forms.');
            initializeAllForms();
        }
    });
});
"""

# Generate a simple secret key for the session middleware
# In a production app, this should be a strong, randomly generated key stored securely
SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "a-super-secret-key-that-should-be-changed")

middleware = [
    Middleware(SessionMiddleware, secret_key=SECRET_KEY)
]

app = FastHTML(
    before=bware,
    exception_handlers={404: _not_found},
    hdrs=(picolink, Style(":root { --pico-font-size: 100%; }"), Script(script_dynamic_materials)),
    middleware=middleware
)
rt = app.route # rt is obtained here

@dataclass
class Login:
    name: str
    pwd: str

@rt("/login")
def get_login(sess): # Kept descriptive name
    frm = Form(
        Input(id="name", placeholder="Name"),
        Input(id="pwd", type="password", placeholder="Password"),
        Button("login"),
        action="/login",
        method="post",
    )
    return Titled("Login", frm, H3("First time login will create your account. Do not reuse passwords from other websites on this website."))

@rt("/login")
def post_login(login: Login, sess): # Kept descriptive name
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
            except passlib.exc.UnknownHashError: is_identified_hash = False
            except (ValueError, TypeError): is_identified_hash = False
        else: is_identified_hash = False

        if is_identified_hash:
            if pwd_context.verify(login.pwd, stored_pwd):
                sess["auth"] = user_record.name
                return RedirectResponse("/", status_code=303)
            else: return login_redir
        else:
            plain_stored_pwd_for_compare = stored_pwd if isinstance(stored_pwd, str) else ""
            if compare_digest(plain_stored_pwd_for_compare.encode("utf-8"), login.pwd.encode("utf-8")):
                new_pwd_hash = pwd_context.hash(login.pwd)
                users.update({"pwd": new_pwd_hash}, user_record.name)
                sess["auth"] = user_record.name
                return RedirectResponse("/", status_code=303)
            else: return login_redir
    except NotFoundError:
        pwd_hash = pwd_context.hash(login.pwd)
        users.insert({"name": login.name, "pwd": pwd_hash})
        sess["auth"] = login.name
        return RedirectResponse("/", status_code=303)

@rt("/logout")
def get_logout(sess): # Kept descriptive name
    del sess["auth"]
    return login_redir

@rt("/")
def get_main_page(request: Request): # Kept descriptive name
    # Explicitly get auth from request scope
    auth = request.scope.get("auth")
    if not auth:
        # This case should ideally be handled by the 'before' middleware redirect,
        # but as a fallback or if middleware is bypassed, redirect here.
        return login_redir

    num_materials_str = request.query_params.get('num_materials', '2')
    try:
        num_materials = int(num_materials_str)
        if not (1 <= num_materials <= 10): num_materials = 2
    except ValueError: num_materials = 2

    title = f"Calculation App for {auth}"
    top = Grid(
        H1(title),
        Div(A("logout", href="/logout"), " | ", A("Add Material", href="/admin/add_material"), style="text-align: right"),
    )
    material_options = [Option("Select from dropdown", value="", disabled=True, selected=True)] + \
                       [Option(material.name, value=material.name) for material in materials()]

    num_materials_form = Form(
        Group(
            Label("Number of Materials (1-10):", for_="num_materials_input"),
            Input(id="num_materials_input", name="num_materials", type="number", value=num_materials, min="1", max="10"),
            Button("Update Material Sections", type="submit"),
        ),
        action="/", method="get", hx_get="/", hx_target="#main-form-content",
        hx_select="#main-form-content", hx_swap="outerHTML"
    )
    
    material_inputs_container_id = "material-inputs-container"
    default_vfracs = [1.0/num_materials] * num_materials if num_materials > 0 else []
    if num_materials > 0 and not np.isclose(sum(default_vfracs), 1.0):
        default_vfracs[-1] = 1.0 - sum(default_vfracs[:-1])

    material_form_sections = [_create_material_form_section(i + 1, material_options, {"vfrac": default_vfracs[i] if i < len(default_vfracs) else (1.0/num_materials)}) for i in range(num_materials)]
    flat_material_form_sections = [item for sublist in material_form_sections for item in sublist]

    calculation_form_content_id = "main-form-content"
    calculation_form = Div(
        Form(
            Div(*flat_material_form_sections, id=material_inputs_container_id), Hr(),
            H2("Calculation Parameters"),
            Group(Label("Mixture Name (Optional)", for_="mixture_name"), Input(id="mixture_name", name="mixture_name", placeholder="e.g., MySlurryMix", type="text", value="MyMixture")),
            Group(Label("Minimum Up for EOS fit (km/s)", for_="upmin_fit"), Input(id="upmin_fit", name="upmin_fit", type="number", value=0.0, step="any")),
            Group(Label("Maximum Up for EOS fit (km/s)", for_="upmax_fit"), Input(id="upmax_fit", name="upmax_fit", type="number", value=6.0, step="any")),
            Group(Label("Number of points for Up array (EOS fit)", for_="num_points_fit"), Input(id="num_points_fit", name="num_points_fit", type="number", value=100, step="1", min="10")),
            Button("Calculate Mixture", type="submit"),
            method="post", hx_post="/calculate", hx_target="#plot-container", hx_swap="innerHTML",
        ), id=calculation_form_content_id
    )
    warning = H4("Please allow a few seconds for calculation, especially with many materials or points.")
    plot_container = Div(id="plot-container")
    
    return Titled(f"EOS Mixer - {auth}", top, num_materials_form, calculation_form, warning, plot_container)

@rt("/calculate")
async def post_calculate(request: Request): # Kept descriptive name
    form_data: FormData = await request.form()
    max_idx = 0
    for key in form_data.keys():
        if key.startswith("material_type_"):
            try:
                idx = int(key.split("_")[-1])
                if idx > max_idx: max_idx = idx
            except ValueError: continue
    num_materials_in_form = max_idx

    if num_materials_in_form == 0:
        return P("Error: No material data received or material sections not found in form.", style="color:red;")

    material_data_list = [] 
    original_material_configs_for_plot = []
    total_vfrac = 0.0

    for i in range(1, num_materials_in_form + 1):
        material_type = str(form_data.get(f"material_type_{i}", ""))
        vfrac_str = str(form_data.get(f"vfrac{i}", "0")) 

        if not vfrac_str: vfrac_str = "0" # Default to 0 if empty string after str conversion
        try:
            vfrac = float(vfrac_str)
            if not (0 <= vfrac <= 1):
                 return P(f"Error: Volume fraction for Material {i} ({vfrac}) must be between 0 and 1.", style="color:red;")
        except ValueError:
            return P(f"Error: Invalid volume fraction for Material {i}: '{vfrac_str}'. Must be a number.", style="color:red;")

        eos = None
        if material_type == "premade":
            selected_name = str(form_data.get(f"material{i}_select", ""))
            if not selected_name:
                if vfrac > 0: return P(f"Error: Premade Material {i} not selected but has volume fraction > 0.", style="color:red;")
                else: continue
            try:
                db_mat = materials[selected_name]
                eos = HugoniotEOS(name=db_mat.name, rho0=db_mat.rho0, C0=db_mat.C0, S=db_mat.S)
            except NotFoundError:
                 if vfrac > 0: return P(f"Error: Premade Material {i} ('{selected_name}') not found in database.", style="color:red;")
                 else: continue
        elif material_type == "custom":
            name = str(form_data.get(f"name{i}", f"CustomMat{i}"))
            try:
                rho0_str = str(form_data.get(f"rho0_{i}", "0"))
                c0_str = str(form_data.get(f"C0_{i}", "0"))
                s_val_str = str(form_data.get(f"S_{i}", "0"))
                rho0 = float(rho0_str)
                C0 = float(c0_str)
                S_val = float(s_val_str)
                if rho0 <=0 or C0 <=0:
                    if vfrac > 0: return P(f"Error: For Custom Material {i}, Density and C0 must be positive.", style="color:red;")
                    else: continue 
                eos = HugoniotEOS(name=name, rho0=rho0, C0=C0, S=S_val)
            except (ValueError, TypeError) as e:
                if vfrac > 0: return P(f"Error: Invalid custom material properties for Material {i}: {e}", style="color:red;")
                else: continue
        else:
            if vfrac > 0 and material_type: return P(f"Error: Unknown type for Material {i}: {material_type}", style="color:red;")
            elif vfrac > 0 and not material_type: return P(f"Error: Material type not specified for Material {i} with vfrac > 0.", style="color:red;")
            else: continue 
        
        if eos: # Add to plotting list even if vfrac is 0
            original_material_configs_for_plot.append((eos, vfrac))
            if vfrac > 0: # Only add to calculation list if vfrac > 0
                material_data_list.append((eos, vfrac))
                total_vfrac += vfrac
    
    if not material_data_list:
        return P("Error: No materials with volume fraction > 0 to calculate a mixture.", style="color:red;")

    if not np.isclose(total_vfrac, 1.0):
        return P(f"Error: Sum of volume fractions ({total_vfrac:.4f}) for active materials must be 1.0. Please adjust.", style="color:red;")

    mixture_name = str(form_data.get("mixture_name", "MyMixture"))
    upmin_fit_str = str(form_data.get("upmin_fit", "0.0"))
    upmax_fit_str = str(form_data.get("upmax_fit", "6.0"))
    num_points_fit_str = str(form_data.get("num_points_fit", "100"))

    try:
        upmin_fit = float(upmin_fit_str)
        upmax_fit = float(upmax_fit_str)
        num_points_fit = int(num_points_fit_str)
    except ValueError:
        return P("Error: Invalid numeric value for Up fit parameters.", style="color:red;")

    if upmin_fit >= upmax_fit: return P("Error: Up_min for fit must be less than Up_max for fit.", style="color:red;")
    if num_points_fit < 10: return P("Error: Number of points for Up array (fit) must be at least 10.", style="color:red;")

    up_ref_array = np.linspace(upmin_fit, upmax_fit, num_points_fit)

    try:
        mixed_eos_result = generate_mixed_hugoniot_many(name=mixture_name, material_data_list=material_data_list, Up_ref=up_ref_array)
        plot_html = plot_mixture_many(original_material_configs=original_material_configs_for_plot, mixed_eos=mixed_eos_result, up_min=upmin_fit, up_max=upmax_fit, num_points=200)
        return plot_html
    except ValueError as ve: return P(f"Calculation Error: {ve}", style="color:red;")
    except Exception as e:
        import traceback; print(traceback.format_exc())
        return P(f"An unexpected error occurred: {e}", style="color:red;")

@rt("/get_material")
def get_material_details(request: Request): # Kept descriptive name
    name_to_fetch = None
    for i in range(1, 11): 
        key = f"material{i}_select"
        if key in request.query_params:
            name_to_fetch = request.query_params[key]
            break 
    
    if not name_to_fetch:
        return P("Please select a material from a dropdown.", style="color:orange;")
    try:
        material = materials[name_to_fetch]
        return Div(
            Table(
                Tr(Th("Name"), Td(material.name)),
                Tr(Th("Density (g/cc)"), Td(f"{material.rho0:.4f}")),
                Tr(Th("C0 (km/s)"), Td(f"{material.C0:.4f}")),
                Tr(Th("S (dim-less)"), Td(f"{material.S:.4f}")),
            )
        )
    except NotFoundError:
        return P(f"Material '{name_to_fetch}' not found.", style="color:red;")

# Admin route to add materials - placeholder for now
@rt("/admin/add_material")
def get_admin_add_material(auth:str): # Kept descriptive name
    # Check if user is admin if implementing roles, for now just auth
    return Titled(f"Add Material - Admin ({auth})",
        Form(
            Input(name="name", placeholder="Material Name"),
            Input(name="rho0", placeholder="Density (g/cc)", type="number", step="any"),
            Input(name="C0", placeholder="C0 (km/s)", type="number", step="any"),
            Input(name="S", placeholder="S (dimensionless)", type="number", step="any"),
            Button("Add Material"),
            method="post",
            action="/admin/add_material" 
        )
    )

@rt("/admin/add_material")
def post_admin_add_material(name:str, rho0:float, C0:float, S:float, auth:str): # Kept descriptive name
    try:
        materials.insert(dict(name=name, rho0=rho0, C0=C0, S=S))
        return RedirectResponse("/", status_code=303) # Redirect to main page
    except Exception as e:
        return Titled("Error Adding Material", P(f"Could not add material: {e}"))

# serve()


