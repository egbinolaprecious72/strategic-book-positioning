import os
import smtplib
import ssl
import threading
from email.message import EmailMessage
from dotenv import load_dotenv
from pathlib import Path
from functools import wraps

from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash, abort
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash

from database import get_db_connection, initialize_database, initialize_admin_table


app = Flask(__name__)

# Load the application secret from the environment or local private file
secret_key = os.environ.get("SECRET_KEY")

if not secret_key:
    secret_path = Path("instance/secret_key")
    if secret_path.exists():
        secret_key = secret_path.read_text().strip()

if not secret_key:
    raise RuntimeError("Application secret is missing.")

app.secret_key = secret_key

# Session and security settings
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "1",
    PERMANENT_SESSION_LIFETIME=1800,
    MAX_CONTENT_LENGTH=1 * 1024 * 1024
)

csrf = CSRFProtect(app)

# Load private Gmail settings
load_dotenv()

def send_email_notification(subject, body):
    email_address = os.getenv("MAIL_USERNAME")
    email_password = os.getenv("MAIL_PASSWORD")
    recipient = os.getenv("NOTIFICATION_EMAIL")
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", "587"))

    if not email_address or not email_password or not recipient:
        raise RuntimeError("Email settings are incomplete.")

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = f'"Egbinola Precious | Strategic Book Market Positioning" <{email_address}>'
    email["To"] = recipient
    email.set_content(body)

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        mail_server, mail_port, timeout=20, context=context
    ) as server:
        server.login(email_address, email_password)
        server.send_message(email)



def send_author_confirmation(author_email, author_name, book_title):
    email_address = os.getenv("MAIL_USERNAME")
    email_password = os.getenv("MAIL_PASSWORD")
    mail_server = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    mail_port = int(os.getenv("MAIL_PORT", "465"))

    if not email_address or not email_password:
        raise RuntimeError("Email settings are incomplete.")

    email = EmailMessage()
    email["Subject"] = "We Have Received Your Enquiry - Strategic Book Market Positioning"
    email["From"] = f'"Egbinola Precious | Strategic Book Market Positioning" <{email_address}>'
    email["To"] = author_email

    email.set_content(f"""Hello {author_name},

I'm Egbinola Precious from Strategic Book Market Positioning. Thank you for contacting us.

We have successfully received your enquiry about "{book_title or "your book"}".

We will review the information you submitted and contact you at this email address to discuss your book's market positioning needs and the possible next steps.

You can also reply directly to this email if you would like to add any information or ask a question.

We appreciate your interest and look forward to connecting with you.

Best regards,
Egbinola Precious
Strategic Book Market Positioning
""")

    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(
        mail_server, mail_port, timeout=20, context=context
    ) as server:
        server.login(email_address, email_password)
        server.send_message(email)



def send_enquiry_emails_in_background(
    subject, body, author_email, author_name, book_title
):
    def send_emails():
        try:
            send_email_notification(subject, body)
        except Exception:
            app.logger.exception("Administrator notification failed.")

        try:
            send_author_confirmation(author_email, author_name, book_title)
        except Exception:
            app.logger.exception("Author confirmation email failed.")

    thread = threading.Thread(target=send_emails, daemon=True)
    thread.start()


# Protect private administrator pages
def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("admin_login"))

        return view(*args, **kwargs)

    return wrapped_view


# PUBLIC WEBSITE ROUTES

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/egbinola-precious")
def founder():
    return render_template("founder.html")


@app.route("/services")
def services():
    return render_template("services.html")


@app.route("/our-work")
def our_work():
    return render_template("our-work.html")


@app.route("/process")
def process():
    return render_template("process.html")


@app.route("/why-us")
def why_us():
    return render_template("why-us.html")


@app.route("/insights")
def insights():
    return render_template("insights.html")


@app.route("/contact")
def contact():
    return redirect(url_for("get_started"))


@app.route("/get-started", methods=["GET", "POST"])
def get_started():
    if request.method == "POST":
        name = request.form.get("author_name", "").strip()
        email = request.form.get("email", "").strip()
        book_title = request.form.get("book_title", "").strip()
        genre = request.form.get("genre", "").strip()
        amazon_link = request.form.get("amazon_link", "").strip()
        publishing_status = request.form.get("publishing_status", "").strip()

        selected_divisions = request.form.getlist("service_division")
        selected_services = request.form.getlist("specific_service")

        division_text = "\\n".join(
            f"- {division}" for division in selected_divisions
        ) or "- Not specified"

        specific_service_text = "\\n".join(
            f"- {service}" for service in selected_services
        ) or "- Not specified"

        service_interest = (
            "Selected divisions:\\n"
            + division_text
            + "\\n\\nSpecific services:\\n"
            + specific_service_text
        )

        goals = request.form.get("goals", "").strip()

        if not all([name, email, goals]):
            flash("Please complete your name, email address and enquiry details.", "warning")
            return redirect(url_for("get_started"))

        connection = get_db_connection()
        try:
            connection.execute(
                """INSERT INTO enquiries
                (name, email, book_title, amazon_link, service, message,
                 source, genre, publishing_status, service_interest)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    name, email, book_title, amazon_link,
                    "Strategic Book Market Positioning", goals,
                    "Get Started", genre, publishing_status,
                    service_interest
                )
            )
            connection.commit()
        finally:
            connection.close()

        email_body = f"""A new Get Started request has been submitted.

Author name: {name}
Author email: {email}
Book title: {book_title or "Not provided"}
Book genre: {genre or "Not provided"}
Amazon link: {amazon_link or "Not provided"}
Publishing status: {publishing_status or "Not provided"}

{service_interest}

Author's goals:
{goals}

Open your private administration dashboard to review the request:

ADMIN DASHBOARD:
https://egbinolaprecious.pythonanywhere.com/admin/login
"""

        send_enquiry_emails_in_background(
            "NEW GET STARTED REQUEST - Strategic Book Market Positioning",
            email_body,
            email,
            name,
            book_title
        )

        flash(
            "Your enquiry has been submitted successfully! We have received your details and will contact you by email about the next steps. Please check your Inbox and Spam/Junk folders for our response.",
            "success"
        )

        return redirect(url_for("get_started"))

    return render_template("get-started.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/disclaimer")
def disclaimer():
    return render_template("disclaimer.html")


# ADMINISTRATOR LOGIN

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():

    if "admin_id" in session:
        return redirect(url_for("admin_dashboard"))

    from flask_wtf import FlaskForm

    form = FlaskForm()

    if form.validate_on_submit():
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        connection = get_db_connection()

        admin = connection.execute(
            "SELECT id, username, password_hash FROM admins WHERE username = ?",
            (username,)
        ).fetchone()

        connection.close()

        if admin and check_password_hash(admin["password_hash"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            session.permanent = True

            return redirect(url_for("admin_dashboard"))

        flash("Incorrect username or password.")

    return render_template("admin/login.html", form=form)


# PRIVATE DASHBOARD

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():

    connection = get_db_connection()

    enquiries = connection.execute(
        "SELECT * FROM enquiries ORDER BY created_at DESC"
    ).fetchall()

    total = connection.execute(
        "SELECT COUNT(*) FROM enquiries"
    ).fetchone()[0]

    new_count = connection.execute(
        "SELECT COUNT(*) FROM enquiries WHERE status = 'New'"
    ).fetchone()[0]

    connection.close()

    return render_template(
        "admin/dashboard.html",
        enquiries=enquiries,
        total=total,
        new_count=new_count
    )


# PRIVATE ENQUIRY DETAILS
@app.route("/admin/enquiry/<int:enquiry_id>")
@admin_required
def admin_enquiry_detail(enquiry_id):
    connection = get_db_connection()
    enquiry = connection.execute(
        "SELECT * FROM enquiries WHERE id = ?",
        (enquiry_id,)
    ).fetchone()
    connection.close()

    if enquiry is None:
        abort(404)

    return render_template(
        "admin/enquiry-detail.html",
        enquiry=enquiry
    )



# UPDATE ENQUIRY STATUS
@app.route("/admin/enquiry/<int:enquiry_id>/status", methods=["POST"])
@admin_required
def update_enquiry_status(enquiry_id):
    allowed_statuses = {
        "New", "Reviewed", "Contacted", "In Progress", "Completed"
    }

    status = request.form.get("status", "").strip()

    if status not in allowed_statuses:
        flash("Please select a valid enquiry status.", "warning")
        return redirect(url_for("admin_enquiry_detail", enquiry_id=enquiry_id))

    connection = get_db_connection()

    enquiry = connection.execute(
        "SELECT id FROM enquiries WHERE id = ?",
        (enquiry_id,)
    ).fetchone()

    if enquiry is None:
        connection.close()
        abort(404)

    connection.execute(
        "UPDATE enquiries SET status = ? WHERE id = ?",
        (status, enquiry_id)
    )
    connection.commit()
    connection.close()

    flash("Enquiry status updated successfully.", "success")
    return redirect(url_for("admin_enquiry_detail", enquiry_id=enquiry_id))


# ADMINISTRATOR LOGOUT

@app.route("/admin/logout", methods=["POST"])
@admin_required
def admin_logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("admin_login"))


# Initialize database tables when the application starts
initialize_database()
initialize_admin_table()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=os.environ.get("FLASK_DEBUG") == "1")
