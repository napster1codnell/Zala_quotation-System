from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file,
    session,
    flash,
)

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from xhtml2pdf import pisa

import os
import json

app = Flask(__name__)
app.secret_key = "your-secret-key-change-in-production"

# ==================================================
# CONFIG
# ==================================================

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quotations.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ==================================================
# DATABASE
# ==================================================

class Quote(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    quote_number = db.Column(
        db.String(50),
        unique=True
    )

    customer_name = db.Column(
        db.String(200)
    )

    customer_phone = db.Column(
        db.String(100)
    )

    customer_address = db.Column(
        db.Text
    )

    description = db.Column(
        db.String(500)
    )

    material = db.Column(
        db.String(200)
    )

    size = db.Column(
        db.Text
    )

    quantity = db.Column(
        db.Integer
    )

    unit_price = db.Column(
        db.Float
    )

    labour_percentage = db.Column(
        db.Float
    )

    labour_amount = db.Column(
        db.Float
    )

    subtotal = db.Column(
        db.Float
    )

    total = db.Column(
        db.Float
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================================================
# CREATE DATABASE
# ==================================================

with app.app_context():
    db.create_all()

os.makedirs(
    "generated_quotes",
    exist_ok=True
)

# ==================================================
# DASHBOARD
# ==================================================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
@login_required
def dashboard():

    quotes = Quote.query.order_by(
        Quote.id.desc()
    ).all()

    return render_template(
        "dashboard.html",
        quotes=quotes
    )

# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            session["logged_in"] = True
            session["user_id"] = user.id
            return redirect(url_for("dashboard"))
        else:
            return render_template("login.html", error="Invalid email or password")

    return render_template("login.html")

# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login"))

# ==================================================
# REGISTER
# ==================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not username or not email or not password:
            return render_template("register.html", error="All fields are required")

        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")

        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            return render_template("register.html", error="Username or email already exists")

        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )

        db.session.add(user)
        db.session.commit()

        return render_template("register.html", success="Account created successfully! You can now login.")

    return render_template("register.html")

# ==================================================
# CREATE QUOTE
# ==================================================

@app.route(
    "/create",
    methods=["GET", "POST"]
)
@login_required
def create_quote():

    if request.method == "POST":

        customer_name = request.form[
            "customer_name"
        ]

        customer_phone = request.form[
            "customer_phone"
        ]

        customer_address = request.form[
            "customer_address"
        ]

        description = request.form[
            "description"
        ]

        material = request.form[
            "material"
        ]

# sizes: optional JSON array submitted from the form builder
        sizes_json = request.form.get("sizes")
        parsed_sizes = None
        if sizes_json:
            try:
                parsed_sizes = json.loads(sizes_json)
                if isinstance(parsed_sizes, list) and parsed_sizes:
                    total_quantity = sum(int(item.get('qty', 1)) for item in parsed_sizes)
                    subtotal = sum((int(item.get('qty', 1)) * float(item.get('price', 0))) for item in parsed_sizes)
                    unit_price = float(parsed_sizes[0].get('price', 0)) if parsed_sizes else 0.0
                    size = sizes_json
                    quantity = total_quantity
                else:
                    parsed_sizes = None
            except Exception:
                parsed_sizes = None

        if not parsed_sizes:
            size = request.form.get("size", "Standard")
            quantity = int(request.form.get("quantity", 1))
            unit_price = float(request.form.get("unit_price", 0))
            subtotal = quantity * unit_price

        labour_percentage = float(
            request.form[
                "labour_percentage"
            ]
        )

        labour_amount = (
            subtotal *
            labour_percentage / 100
        )

        total = (
            subtotal +
            labour_amount
        )

        quote_number = (
            f"Q-{datetime.now().year}-"
            f"{Quote.query.count()+1:04}"
        )

        quote = Quote(
            quote_number=quote_number,
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_address=customer_address,
            description=description,
            material=material,
            size=size,
            quantity=quantity,
            unit_price=unit_price,
            labour_percentage=labour_percentage,
            labour_amount=labour_amount,
            subtotal=subtotal,
            total=total
        )

        db.session.add(quote)
        db.session.commit()

        return redirect(
            url_for(
                "generate_pdf",
                quote_id=quote.id
            )
        )

    return render_template(
        "create_quote.html"
    )

# ==================================================
# PDF GENERATOR
# ==================================================

def link_callback(uri, rel):
    if uri.startswith("/"):
        path = os.path.join(app.root_path, uri.lstrip("/"))
    else:
        path = os.path.join(app.root_path, uri)

    if os.path.isfile(path):
        return path

    return uri


def convert_html_to_pdf(
    source_html,
    output_filename
):

    with open(
        output_filename,
        "w+b"
    ) as result_file:

        pisa_status = pisa.CreatePDF(
            source_html,
            dest=result_file,
            link_callback=link_callback
        )

    return pisa_status.err

# ==================================================
# GENERATE PDF
# ==================================================

@app.route("/pdf/<int:quote_id>")
@login_required
def generate_pdf(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    
    # Add valid_until attribute to the quote object
    if quote.created_at:
        quote.valid_until = (quote.created_at + timedelta(days=14)).strftime('%d/%m/%Y')
    else:
        quote.valid_until = '14 days from issue'
    # If sizes were stored as JSON in quote.size, prepare a human-readable display
    try:
        parsed = json.loads(quote.size)
        if isinstance(parsed, list):
            # create readable display like: "900 x 600 (1), 1630 x 600 (2)"
            parts = []
            for item in parsed:
                s = item.get('size') if isinstance(item, dict) else str(item)
                q = int(item.get('qty', 1)) if isinstance(item, dict) else 1
                parts.append(f"{s} ({q})")
            quote.size_display = ', '.join(parts)
            quote.sizes_list = parsed
        else:
            quote.size_display = None
            quote.sizes_list = None
    except Exception:
        quote.size_display = None
        quote.sizes_list = None

    html = render_template("quotation_template.html", quote=quote)
    
    pdf_path = os.path.join("generated_quotes", f"{quote.quote_number}.pdf")
    convert_html_to_pdf(html, pdf_path)
    
    return send_file(pdf_path, as_attachment=True, download_name=f"{quote.quote_number}.pdf")
# ==================================================
# PREVIEW QUOTE
# ==================================================

@app.route(
    "/quote/<int:quote_id>"
)
@login_required
def preview_quote(quote_id):

    quote = Quote.query.get_or_404(
        quote_id
    )

    # prepare sizes display for preview if needed
    try:
        parsed = json.loads(quote.size)
        if isinstance(parsed, list):
            parts = []
            for item in parsed:
                s = item.get('size') if isinstance(item, dict) else str(item)
                q = int(item.get('qty', 1)) if isinstance(item, dict) else 1
                parts.append(f"{s} ({q})")
            quote.size_display = ', '.join(parts)
            quote.sizes_list = parsed
        else:
            quote.size_display = None
            quote.sizes_list = None
    except Exception:
        quote.size_display = None
        quote.sizes_list = None

    return render_template(
        "quotation_template.html",
        quote=quote
    )

# ==================================================
# DELETE QUOTE
# ==================================================

@app.route(
    "/delete/<int:quote_id>"
)
@login_required
def delete_quote(quote_id):

    quote = Quote.query.get_or_404(
        quote_id
    )

    db.session.delete(quote)

    db.session.commit()

    return redirect(
        url_for("dashboard")
    )

# ==================================================
# CUSTOMERS
# ==================================================

@app.route("/customers")
@login_required
def customers():
    # Get unique customers from all quotes
    quotes = Quote.query.all()
    
    # Create a dictionary of unique customers
    customers_dict = {}
    for quote in quotes:
        if quote.customer_name not in customers_dict:
            customers_dict[quote.customer_name] = {
                'name': quote.customer_name,
                'phone': quote.customer_phone,
                'address': quote.customer_address,
                'quote_count': 0,
                'total_value': 0
            }
        customers_dict[quote.customer_name]['quote_count'] += 1
        customers_dict[quote.customer_name]['total_value'] += quote.total
    
    customers_list = list(customers_dict.values())
    
    return render_template(
        "customers.html",
        customers=customers_list
    )

# ==================================================
# SETTINGS
# ==================================================

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user_id = session.get("user_id")
    user = User.query.get(user_id)
    
    if request.method == "POST":
        action = request.form.get("action")
        
        if action == "update_profile":
            username = request.form.get("username")
            email = request.form.get("email")
            
            # Check if email or username already exists (excluding current user)
            existing_user = User.query.filter(
                ((User.username == username) | (User.email == email)) & 
                (User.id != user_id)
            ).first()
            
            if existing_user:
                return render_template("settings.html", user=user, error="Username or email already exists")
            
            user.username = username
            user.email = email
            db.session.commit()
            
            return render_template("settings.html", user=user, success="Profile updated successfully!")
        
        elif action == "change_password":
            current_password = request.form.get("current_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")
            
            if not check_password_hash(user.password_hash, current_password):
                return render_template("settings.html", user=user, error="Current password is incorrect")
            
            if new_password != confirm_password:
                return render_template("settings.html", user=user, error="New passwords do not match")
            
            if len(new_password) < 6:
                return render_template("settings.html", user=user, error="Password must be at least 6 characters long")
            
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            return render_template("settings.html", user=user, success="Password changed successfully!")
    
    return render_template("settings.html", user=user)

# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )