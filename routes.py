"""
MindGuardian AI — Authentication Blueprint

Routes
------
GET  /auth/register   — Registration form
POST /auth/register   — Create account
GET  /auth/login      — Login form
POST /auth/login      — Authenticate user
GET  /auth/logout     — Logout current user
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app import db, bcrypt
from app.models import User
from app.auth.forms import RegistrationForm, LoginForm

auth_bp = Blueprint("auth", __name__, template_folder="../../templates/auth")


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = RegistrationForm()

    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode("utf-8")
        user = User(
            username=form.username.data,
            email=form.email.data.lower(),
            password_hash=hashed_pw,
        )
        db.session.add(user)
        db.session.commit()
        flash(f"Account created! Welcome, {user.username}. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form, title="Create Account")


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()

        if user and bcrypt.check_password_hash(user.password_hash, form.password.data):
            login_user(user, remember=form.remember.data)
            # Honour the original ?next= redirect if safe
            next_page = request.args.get("next")
            flash(f"Welcome back, {user.username}!", "success")
            return redirect(next_page or url_for("main.dashboard"))

        flash("Invalid email or password. Please try again.", "danger")

    return render_template("auth/login.html", form=form, title="Sign In")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been signed out.", "info")
    return redirect(url_for("auth.login"))
