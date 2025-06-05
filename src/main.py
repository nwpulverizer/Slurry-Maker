# pyright: basic
# Explicitly import necessary symbols from fasthtml.common
from fasthtml.common import (
    FastHTML, Titled, Div, Form, Input, Button, RedirectResponse, database,
    NotFoundError, Grid, H1, A, Label, Group, Select, Option, Article, Hr, H2, H4, Table, Tr, Th, Td, NotStr, Style, Script, picolink,
    Beforeware, # Added Beforeware
    P, # Added P
    H3, # Added H3
    HtmxResponseHeaders # Added HtmxResponseHeaders
)
from hmac import compare_digest
from dataclasses import dataclass, fields, field
from passlib.context import CryptContext
import passlib.exc # Ensure this is imported for specific exception types
import os # Import os for SECRET_KEY
import sys # Import sys for stdout.flush()
import numpy as np
from components import (
    HugoniotEOS,
    MixedHugoniotEOS,
    generate_mixed_hugoniot_many, 
    plot_mixture_many,
)
from starlette.requests import Request
from starlette.datastructures import FormData
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import Response # Import Response
import os # Import os for SECRET_KEY
from typing import Optional

# --- Shared style variables for layout and headings ---
container_style = (
    "max-width: 900px; margin: 2em auto; padding: 2em 2.5em; background: var(--pico-card-background-color, #fff); border-radius: 14px; "
    "box-shadow: 0 2px 16px #0002;"
)
section_style = "margin-bottom: 2em;"
heading_style = "margin-bottom: 0.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em;"
subheading_style = "margin: 1.5em 0 0.5em 0; font-size: 1.1em;"

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
    print("Before middleware running.") # Added print
    print(f"Session content in before: {dict(sess)}") # Added print
    print(f"Request cookies in before: {req.cookies if hasattr(req, 'cookies') else 'No cookies attr'}") # Added print
    auth = req.scope["auth"] = sess.get("auth", None)
    if not auth:
        print("Auth not found in session, redirecting to login.") # Added print
        return login_redir
    print(f"Auth found in session: {auth}") # Added print


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

    # Use values from default_custom_values
    default_vfrac = default_custom_values.get("vfrac", 0.5 / section_idx if section_idx > 0 else 0.5)
    try:
        default_vfrac = float(default_vfrac)
    except (ValueError, TypeError):
        default_vfrac = 0.1
    material_type = default_custom_values.get("material_type", "premade")
    selected_material = default_custom_values.get("selected", "")

    # Set checked for radios
    custom_checked = material_type == "custom"
    premade_checked = material_type == "premade"

    # Set selected for dropdown
    premade_options = [
        Option("Select from dropdown", value="", disabled=True, selected=(selected_material == ""))
    ] + [
        Option(material.name, value=material.name, selected=(material.name == selected_material))
        for material in material_options[1:] # skip the first Option, which is always the placeholder
    ]

    return (
        Article(
            H3(f"Material {section_idx}"),
            Group(
                Label("Type:", cls="label-inline"),
                Input(type="radio", id=custom_radio_id, name=f"material_type_{section_idx}", value="custom", data_idx=str(section_idx), checked=custom_checked),
                Label(f"Custom", for_=custom_radio_id, cls="label-inline"),
                Input(type="radio", id=premade_radio_id, name=f"material_type_{section_idx}", value="premade", checked=premade_checked, data_idx=str(section_idx)),
                Label("Premade", for_=premade_radio_id, cls="label-inline"),
            ),
            Div(
                Group(Label("Name", for_=name_id), Input(id=name_id, name=name_id, placeholder=f"Material {section_idx} Name", value=str(default_custom_values.get("name", "")))),
                Group(Label("Density (g/cc)", for_=rho0_id), Input(id=rho0_id, name=rho0_id, placeholder="Density", type="number", value=float(default_custom_values.get("rho0", 1.0)), step="any")),
                Group(Label("C0 (km/s)", for_=c0_id), Input(id=c0_id, name=c0_id, placeholder="C0", type="number", value=float(default_custom_values.get("C0", 1.5)), step="any")),
                Group(Label("S (dimensionless)", for_=s_id), Input(id=s_id, name=s_id, placeholder="S", type="number", value=float(default_custom_values.get("S", 1.5)), step="any")),
                id=custom_div_id, style=f"display: {'block' if material_type == 'custom' else 'none'};",
            ),
            Div(
                Group(
                    Select(
                        *premade_options, id=select_id, name=select_id,
                        placeholder=f"Select Material {section_idx}",
                        hx_get="/get_material", hx_target=f"#{info_div_id}", hx_trigger="change", hx_include=f"[name='{select_id}']"
                    )
                ),
                Div(id=info_div_id),
                id=premade_div_id, style=f"display: {'block' if material_type == 'premade' else 'none'};",
            ),
            Group(
                Label(f"Volume Fraction for Material {section_idx}", for_=vfrac_id),
                Input(id=vfrac_id, name=vfrac_id, placeholder="Volume Fraction", type="number", value=default_vfrac, step="any", min="0", max="1")
            ),
            Input(type="hidden", id=selected_hidden_id, name=selected_hidden_id, value=material_type)
        )
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
    name: Optional[str] = None
    pwd: Optional[str] = None

@rt("/login")
async def login(request: Request, sess):
    if request.method == "GET":
        frm = Form(
            Input(id="name", name="name", placeholder="Name"),
            Input(id="pwd", name="pwd", type="password", placeholder="Password"),
            Button("login"),
            action="/login",
            method="post",
        )
        return Titled("Login", frm, H3("First time login will create your account. Do not reuse passwords from other websites on this website."))
    else:
        form = await request.form() if hasattr(request, 'form') and callable(request.form) else request.form
        name = form.get("name")
        pwd = form.get("pwd")
        print(f"Attempting login for user: {name}")
        if not name or not pwd:
            print("Login failed: Missing name or password.")
            print(f"Returning: {login_redir}")
            return login_redir
        try:
            user_record = users[name]
            stored_pwd = user_record.pwd
            print(f"User {name} found in DB.")
            is_identified_hash = False
            if isinstance(stored_pwd, str) and stored_pwd:
                try:
                    pwd_context.identify(stored_pwd)
                    is_identified_hash = True
                    print("Stored password identified as hash.")
                except passlib.exc.UnknownHashError:
                    is_identified_hash = False
                    print("Stored password not a recognized hash.")
                except (ValueError, TypeError):
                    is_identified_hash = False
                    print("Error identifying stored password hash type.")
            else:
                is_identified_hash = False
                print("Stored password is not a string or is empty.")
            if (is_identified_hash and pwd_context.verify(pwd, stored_pwd)) or \
               (not is_identified_hash and compare_digest((stored_pwd if isinstance(stored_pwd, str) else "").encode("utf-8"), pwd.encode("utf-8"))):
                print("Password verification successful.")
                sess["auth"] = user_record.name
                print(f"Session auth set for {user_record.name}. Redirecting to /.")
                print(f"Session after setting auth: {dict(sess)}")
                sys.stdout.flush()
                if "HX-Request" in request.headers:
                    print("HTMX request detected. Returning HX-Location header.")
                    return HtmxResponseHeaders(location="/")
                else:
                    print("Non-HTMX request. Returning RedirectResponse.")
                    return RedirectResponse("/", status_code=303)
            else:
                print("Password verification failed.")
                print(f"Returning: {login_redir}")
                return login_redir
        except NotFoundError:
            print(f"User {name} not found. Creating new user.")
            pwd_hash = pwd_context.hash(pwd)
            users.insert({"name": name, "pwd": pwd_hash})
            sess["auth"] = name
            print(f"New user {name} created and session auth set. Redirecting to /.")
            print(f"Session after setting auth: {dict(sess)}")
            sys.stdout.flush()
            if "HX-Request" in request.headers:
                print("HTMX request detected. Returning HX-Location header.")
                return HtmxResponseHeaders(location="/")
            else:
                print("Non-HTMX request. Returning RedirectResponse.")
                return RedirectResponse("/", status_code=303)

@rt("/logout")
def get_logout(sess): # Kept descriptive name
    del sess["auth"]
    return login_redir

@rt("/")
def get_main_page(request: Request): # Kept descriptive name
    print("Reached get_main_page route.") # Added print statement
    auth = request.scope.get("auth")
    print(f"Auth value in get_main_page: {auth}") # Added print
    if not auth:
        print("Auth not found in scope, redirecting to login.")
        return login_redir
    print(f"Auth found in scope: {auth}")

    num_materials_str = request.query_params.get('num_materials', '2')
    try:
        num_materials = int(num_materials_str)
        if not (1 <= num_materials <= 10): num_materials = 2
    except ValueError: num_materials = 2

    # Parse existing form data from query parameters to preserve user inputs
    existing_data = {}
    for key, value in request.query_params.items():
        if key != 'num_materials':  # Skip the num_materials parameter
            existing_data[key] = value
    
    print(f"Existing form data: {existing_data}")  # Debug logging
    print(f"All query params: {dict(request.query_params)}")  # Debug logging

    title = f"Calculation App for {auth}"
    top = Div(
        Grid(
            H1(title, style="margin-bottom:0.2em;"),
            Div(
                A("logout", href="/logout", cls="contrast"),
                " | ",
                A("Add Material", href="/admin/add_material", cls="secondary"),
                style="text-align: right; margin-bottom: 0.5em;"
            ),
        ),
        style=section_style
    )
    material_options = [Option("Select from dropdown", value="", disabled=True, selected=True)] + \
                       [Option(material.name, value=material.name) for material in materials()]

    num_materials_form = Div(
        H2("Material Mixer", style=heading_style),
        Form(
            Group(
                Label("Number of Materials (1-10):", for_="num_materials_input"),
                Input(
                    id="num_materials_input", 
                    name="num_materials", 
                    type="number", 
                    value=num_materials, 
                    min="1", 
                    max="10", 
                    style="width: 6em; display: inline-block; margin-right: 1em;",
                    onchange="updateMaterialsWithCurrentData(this.value)"
                ),
            ),
            id="num-materials-form",
            style="margin-bottom: 1.5em;"
        ),
        style=section_style
    )
    
    material_inputs_container_id = "material-inputs-container"
    default_vfracs = [1.0/num_materials] * num_materials if num_materials > 0 else []
    if num_materials > 0 and not np.isclose(sum(default_vfracs), 1.0):
        default_vfracs[-1] = 1.0 - sum(default_vfracs[:-1])

    # Function to get preserved data for each material
    def get_material_data(i):
        idx = i + 1
        material_data = {
            "vfrac": default_vfracs[i] if i < len(default_vfracs) else (1.0/num_materials)
        }
        
        # Preserve existing values if they exist
        if f"vfrac{idx}" in existing_data:
            try:
                material_data["vfrac"] = float(existing_data[f"vfrac{idx}"])
            except (ValueError, TypeError):
                pass
        
        if f"material_type_{idx}" in existing_data:
            material_data["material_type"] = existing_data[f"material_type_{idx}"]
        
        if f"material{idx}_select" in existing_data:
            material_data["selected"] = existing_data[f"material{idx}_select"]
        
        # Preserve custom material values
        if f"name{idx}" in existing_data:
            material_data["name"] = existing_data[f"name{idx}"]
        if f"rho0_{idx}" in existing_data:
            try:
                material_data["rho0"] = float(existing_data[f"rho0_{idx}"])
            except (ValueError, TypeError):
                pass
        if f"C0_{idx}" in existing_data:
            try:
                material_data["C0"] = float(existing_data[f"C0_{idx}"])
            except (ValueError, TypeError):
                pass
        if f"S_{idx}" in existing_data:
            try:
                material_data["S"] = float(existing_data[f"S_{idx}"])
            except (ValueError, TypeError):
                pass
        
        return material_data

    # --- Material Sections as Cards ---
    material_form_sections = [
        Div(
            _create_material_form_section(i + 1, material_options, get_material_data(i)),
            style="background: #f8f9fa; border-radius: 8px; box-shadow: 0 1px 4px #0001; padding: 1.2em 1em; margin-bottom: 1.2em;"
        )
        for i in range(num_materials)
    ]

    calculation_form_content_id = "main-form-content"
    
    # Preserve calculation parameters
    mixture_name = existing_data.get("mixture_name", "MyMixture")
    upmin_fit = existing_data.get("upmin_fit", "0.0")
    upmax_fit = existing_data.get("upmax_fit", "6.0")
    num_points_fit = existing_data.get("num_points_fit", "100")
    
    try:
        upmin_fit = float(upmin_fit)
    except (ValueError, TypeError):
        upmin_fit = 0.0
    
    try:
        upmax_fit = float(upmax_fit)
    except (ValueError, TypeError):
        upmax_fit = 6.0
        
    try:
        num_points_fit = int(num_points_fit)
    except (ValueError, TypeError):
        num_points_fit = 100
    
    # --- Wrap calculation form and plot container in a single parent Div ---
    calculation_form = Div(
        H2("Calculation Parameters", style=heading_style),
        Form(
            Div(*material_form_sections, id=material_inputs_container_id), Hr(),
            Group(Label("Mixture Name (Optional)", for_="mixture_name"), Input(id="mixture_name", name="mixture_name", placeholder="e.g., MySlurryMix", type="text", value=mixture_name, style="width: 60%; min-width: 180px;")),
            Group(Label("Minimum Up for EOS fit (km/s)", for_="upmin_fit"), Input(id="upmin_fit", name="upmin_fit", type="number", value=upmin_fit, step="any", style="width: 8em;")),
            Group(Label("Maximum Up for EOS fit (km/s)", for_="upmax_fit"), Input(id="upmax_fit", name="upmax_fit", type="number", value=upmax_fit, step="any", style="width: 8em;")),
            Group(Label("Number of points for Up array (EOS fit)", for_="num_points_fit"), Input(id="num_points_fit", name="num_points_fit", type="number", value=num_points_fit, step="1", min="10", style="width: 8em;")),
            Button("Calculate Mixture", type="submit", cls="contrast", style="margin-top: 1em; width: 100%; font-size: 1.1em;"),
            # Plot button removed from initial load - will be added after successful calculation
            method="post", hx_post="/calculate", hx_target="#main-form-content", hx_swap="outerHTML",
            style="margin-bottom: 1.5em;"
        ), id=None, style=section_style
    )
    warning = H4("Please allow a few seconds for calculation, especially with many materials or points.", style="color: #b85c00; margin-bottom: 1.5em;")
    plot_container = Div(" ", id="plot-container", style="margin-top: 2em;")

    # --- Main Card Container ---
    return Div(
        top,
        num_materials_form,
        Div(
            calculation_form,
            plot_container,
            id="main-form-content",
            style="margin-bottom: 2em;"
        ),
        warning,
        Script("""
        function updateMaterialsWithCurrentData(newNumMaterials) {
            // Collect all current form data
            const params = new URLSearchParams();
            params.append('num_materials', newNumMaterials);
            
            // Collect all inputs from the main form
            const mainForm = document.querySelector('#main-form-content form');
            if (mainForm) {
                // Get all form elements and manually collect the values
                const inputs = mainForm.querySelectorAll('input, select, textarea');
                
                inputs.forEach(input => {
                    if (input.name && input.name !== 'num_materials') {
                        // For radio buttons, only include if checked
                        if (input.type === 'radio') {
                            if (input.checked) {
                                params.append(input.name, input.value);
                            }
                        }
                        // For checkboxes, only include if checked
                        else if (input.type === 'checkbox') {
                            if (input.checked) {
                                params.append(input.name, input.value);
                            }
                        }
                        // For all other inputs and selects
                        else {
                            params.append(input.name, input.value);
                        }
                    }
                });
            }
            
            console.log('Sending form data:', params.toString()); // Debug log
            
            // Make the HTMX request
            htmx.ajax('GET', '/?' + params.toString(), {
                target: '#main-form-content',
                select: '#main-form-content',
                swap: 'outerHTML'
            });
        }
        """),
        Script(script_dynamic_materials),
        style=container_style
    )

# --- Helper for robust numeric form parsing ---
def get_numeric_form_value(form_data, key, default, typ=float):
    val = form_data.get(key, None)
    if val is None or str(val).strip() == "":
        return default
    try:
        return typ(val)
    except (ValueError, TypeError):
        return default

@rt("/calculate")
async def post_calculate(request: Request):
    form_data: FormData = await request.form()
    try:
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
        upmin_fit = get_numeric_form_value(form_data, "upmin_fit", 0.0, float)
        upmax_fit = get_numeric_form_value(form_data, "upmax_fit", 6.0, float)
        num_points_fit = get_numeric_form_value(form_data, "num_points_fit", 100, int)

        if upmin_fit >= upmax_fit: return P("Error: Up_min for fit must be less than Up_max for fit.", style="color:red;")
        if num_points_fit < 10: return P("Error: Number of points for Up array (fit) must be at least 10.", style="color:red;")

        up_ref_array = np.linspace(upmin_fit, upmax_fit, num_points_fit)

        try:
            mixed_eos_result = generate_mixed_hugoniot_many(name=mixture_name, material_data_list=material_data_list, Up_ref=up_ref_array)
            plot_html = plot_mixture_many(original_material_configs=original_material_configs_for_plot, mixed_eos=mixed_eos_result, up_min=upmin_fit, up_max=upmax_fit, num_points=200)
            # --- Rebuild the calculation form with POSTed values pre-filled ---
            # Reuse the same logic as get_main_page, but fill values from form_data
            # (For brevity, only vfrac and mixture_name are pre-filled; extend as needed)
            num_materials = num_materials_in_form
            material_inputs_container_id = "material-inputs-container"
            material_options = [Option("Select from dropdown", value="", disabled=True, selected=True)] + \
                               [Option(material.name, value=material.name) for material in materials()]
            material_form_sections = [
                Div(
                    _create_material_form_section(
                        i + 1,
                        material_options,
                        {
                            "vfrac": form_data.get(f"vfrac{i+1}", 1.0/num_materials),
                            "name": form_data.get(f"name{i+1}", ""),
                            "rho0": get_numeric_form_value(form_data, f"rho0_{i+1}", 1.0, float),
                            "C0": get_numeric_form_value(form_data, f"C0_{i+1}", 1.5, float),
                            "S": get_numeric_form_value(form_data, f"S_{i+1}", 1.5, float),
                            "material_type": form_data.get(f"material_type_{i+1}", "premade"),
                            "selected": form_data.get(f"material{i+1}_select", ""),
                        }
                    ),
                    style="background: #f8f9fa; border-radius: 8px; box-shadow: 0 1px 4px #0001; padding: 1.2em 1em; margin-bottom: 1.2em;"
                )
                for i in range(num_materials)
            ]
            calculation_form = Div(
                H2("Calculation Parameters", style=heading_style),
                Form(
                    Div(*material_form_sections, id=material_inputs_container_id), Hr(),
                    Group(Label("Mixture Name (Optional)", for_="mixture_name"), Input(id="mixture_name", name="mixture_name", placeholder="e.g., MySlurryMix", type="text", value=mixture_name, style="width: 60%; min-width: 180px;")),
                    Group(Label("Minimum Up for EOS fit (km/s)", for_="upmin_fit"), Input(id="upmin_fit", name="upmin_fit", type="number", value=upmin_fit, step="any", style="width: 8em;")),
                    Group(Label("Maximum Up for EOS fit (km/s)", for_="upmax_fit"), Input(id="upmax_fit", name="upmax_fit", type="number", value=upmax_fit, step="any", style="width: 8em;")),
                    Group(Label("Number of points for Up array (EOS fit)", for_="num_points_fit"), Input(id="num_points_fit", name="num_points_fit", type="number", value=num_points_fit, step="1", min="10", style="width: 8em;")),
                    Button("Calculate Mixture", type="submit", cls="contrast", style="margin-top: 1em; width: 100%; font-size: 1.1em;"),
                    Button("Plot", id="plot-btn", type="submit", name="plot", hx_post="/plot", hx_target="#plot-container", hx_swap="innerHTML", hx_include="closest form", hx_trigger="click", cls="secondary", style="margin-top:1em; width:100%; font-size:1.1em;"),
                    method="post", hx_post="/calculate", hx_target="#main-form-content", hx_swap="outerHTML",
                    style="margin-bottom: 1.5em;"
                ), id=None, style=section_style
            )
            # Return both the form and the plot in the same parent Div
            return Div(
                calculation_form,
                Div(
                    plot_html,
                    id="plot-container",
                    style="margin-top: 2em;"
                ),
                id="main-form-content",
                style="margin-bottom: 2em;"
            )
        except ValueError as ve: return P(f"Calculation Error: {ve}", style="color:red;")
        except Exception as e:
            import traceback; print(traceback.format_exc())
            return P(f"An unexpected error occurred: {e}", style="color:red;")
    except Exception as e:
        import traceback; print(traceback.format_exc())
        return P(f"An unexpected error occurred in post_calculate: {e}", style="color:red;")

@rt("/plot")
async def post_plot(request: Request):
    form_data: FormData = await request.form()
    # Reuse the same logic as in /calculate to get the plot, but only render the plot (not the form)
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
        if not vfrac_str: vfrac_str = "0"
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
            rho0 = get_numeric_form_value(form_data, f"rho0_{i}", 1.0, float)
            C0 = get_numeric_form_value(form_data, f"C0_{i}", 1.5, float)
            S_val = get_numeric_form_value(form_data, f"S_{i}", 1.5, float)
            if rho0 <=0 or C0 <=0:
                if vfrac > 0: return P(f"Error: For Custom Material {i}, Density and C0 must be positive.", style="color:red;")
                else: continue 
            eos = HugoniotEOS(name=name, rho0=rho0, C0=C0, S=S_val)
        else:
            if vfrac > 0 and material_type: return P(f"Error: Unknown type for Material {i}: {material_type}", style="color:red;")
            elif vfrac > 0 and not material_type: return P(f"Error: Material type not specified for Material {i} with vfrac > 0.", style="color:red;")
            else: continue 
        if eos:
            original_material_configs_for_plot.append((eos, vfrac))
            if vfrac > 0:
                material_data_list.append((eos, vfrac))
                total_vfrac += vfrac
    if not material_data_list:
        return P("Error: No materials with volume fraction > 0 to calculate a mixture.", style="color:red;")
    if not np.isclose(total_vfrac, 1.0):
        return P(f"Error: Sum of volume fractions ({total_vfrac:.4f}) for active materials must be 1.0. Please adjust.", style="color:red;")
    mixture_name = str(form_data.get("mixture_name", "MyMixture"))
    upmin_fit = get_numeric_form_value(form_data, "upmin_fit", 0.0, float)
    upmax_fit = get_numeric_form_value(form_data, "upmax_fit", 6.0, float)
    num_points_fit = get_numeric_form_value(form_data, "num_points_fit", 100, int)
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
def get_admin_add_material(request: Request): # Kept descriptive name
    auth = request.scope.get("auth")
    if not auth:
        return login_redir
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
async def post_admin_add_material(request: Request): # Kept descriptive name
    auth = request.scope.get("auth")
    if not auth:
        return login_redir
    
    form_data = await request.form()
    name = form_data.get("name", "").strip()
    
    try:
        rho0 = float(form_data.get("rho0", "0"))
        C0 = float(form_data.get("C0", "0"))
        S = float(form_data.get("S", "0"))
    except (ValueError, TypeError):
        return Titled("Error Adding Material", P("Invalid numeric values provided for material properties."))
    
    if not name:
        return Titled("Error Adding Material", P("Material name is required."))
    
    if rho0 <= 0 or C0 <= 0:
        return Titled("Error Adding Material", P("Density and C0 must be positive values."))
    
    try:
        materials.insert(dict(name=name, rho0=rho0, C0=C0, S=S))
        return RedirectResponse("/", status_code=303) # Redirect to main page
    except Exception as e:
        return Titled("Error Adding Material", P(f"Could not add material: {e}"))

# --- Ensure plot container is always present and updated on first submit ---
# The plot_container Div is already outside the form and has id="plot-container".
# The calculation form uses hx_post="/calculate" and hx_target="#plot-container".
# To ensure the plot appears on first submit, make sure the initial page load includes an empty plot_container Div,
# and that the /calculate route always returns a valid FastHTML Div/Table/NotStr, not a string or list.
# This is already the case after the previous fixes.
# If the problem persists, it may be due to browser caching or a stale frontend. Try a hard refresh (Ctrl+Shift+R).


