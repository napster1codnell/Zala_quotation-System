from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    send_file
)

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta

from xhtml2pdf import pisa

import os

app = Flask(__name__)

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
        db.String(100)
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

@app.route("/")
def dashboard():

    quotes = Quote.query.order_by(
        Quote.id.desc()
    ).all()

    return render_template(
        "dashboard.html",
        quotes=quotes
    )

# ==================================================
# CREATE QUOTE
# ==================================================

@app.route(
    "/create",
    methods=["GET", "POST"]
)
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

        size = request.form[
            "size"
        ]

        quantity = int(
            request.form["quantity"]
        )

        unit_price = float(
            request.form["unit_price"]
        )

        labour_percentage = float(
            request.form[
                "labour_percentage"
            ]
        )

        subtotal = (
            quantity * unit_price
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
            dest=result_file
        )

    return pisa_status.err

# ==================================================
# GENERATE PDF
# ==================================================

@app.route("/pdf/<int:quote_id>")
def generate_pdf(quote_id):
    quote = Quote.query.get_or_404(quote_id)
    
    # Add valid_until attribute to the quote object
    if quote.created_at:
        quote.valid_until = (quote.created_at + timedelta(days=14)).strftime('%d/%m/%Y')
    else:
        quote.valid_until = '14 days from issue'
    
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
def preview_quote(quote_id):

    quote = Quote.query.get_or_404(
        quote_id
    )

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
# RUN
# ==================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )