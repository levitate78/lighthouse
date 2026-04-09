from flask import Blueprint, redirect, render_template, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required
from flask_dance.contrib.gitlab import gitlab as gitlab_dance
from werkzeug.security import generate_password_hash, check_password_hash

from extensions import db, limiter
from forms import LoginForm, SignupForm, ChangePasswordForm
from gitlab_utils import validate_gitlab_token
from models import User

auth_bp = Blueprint("auth", __name__)


def load_user(user_id):
    return db.session.get(User, int(user_id))


@auth_bp.route("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    from config import Config

    enable_gitlab = Config().ENABLE_GITLAB_LOGIN
    return render_template("login.html", form=form, enable_gitlab=enable_gitlab)


@auth_bp.route("/gitlab/login")
def gitlab_login():
    if not gitlab_dance.authorized:
        return redirect(url_for("gitlab.login"))

    resp = gitlab_dance.get("/api/v4/user")
    if resp.ok:
        user_info = resp.json()
        user = db.session.query(User).filter_by(gitlab_id=user_info["id"]).first()
        if not user:
            existing_username = db.session.query(User).filter_by(
                username=user_info["username"]
            ).first()
            if existing_username:
                flash("A user with that username already exists.")
                return redirect(url_for("auth.login"))
            user = User(
                gitlab_id=user_info["id"],
                username=user_info["username"],
                name=user_info["name"],
                email=user_info.get("email", ""),
                avatar_url=user_info.get("avatar_url", ""),
                provider="gitlab",
                approved=False,  # GitLab users also need admin approval
            )
            db.session.add(user)
            db.session.commit()
            flash(
                "GitLab account linked successfully! Your account is pending administrator approval before you can log in."
            )
            return redirect(url_for("auth.login"))
        if not user.approved:
            flash(
                "Your account is pending administrator approval. Please try again later."
            )
            return redirect(url_for("auth.login"))
        login_user(user)
        return redirect(url_for("index"))
    return redirect(url_for("auth.login"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


@auth_bp.route("/login/local", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def local_login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.query(User).filter_by(
            username=form.username.data, provider="local"
        ).first()
        if user and user.password_hash and check_password_hash(user.password_hash, form.password.data):
            if not user.approved:
                flash(
                    "Your account is pending administrator approval. Please try again later."
                )
                return render_template("login.html", form=form, login_type="local")
            login_user(user)
            if user.password_change_required:
                return redirect(url_for("auth.change_password"))
            return redirect(url_for("index"))
        flash("Invalid username or password")
    return render_template("login.html", form=form, login_type="local")


@auth_bp.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per hour")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = SignupForm()
    if form.validate_on_submit():
        if db.session.query(User).filter_by(username=form.username.data).first():
            flash("Username already exists")
            return render_template("signup.html", form=form)

        if form.gitlab_token.data:
            is_valid, error_msg = validate_gitlab_token(form.gitlab_token.data)
            if not is_valid:
                flash(f"Invalid GitLab token: {error_msg}")
                return render_template("signup.html", form=form)

        user = User(
            username=form.username.data,
            name=form.name.data,
            email=form.email.data,
            password_hash=generate_password_hash(form.password.data),
            provider="local",
            approved=False,  # New users need admin approval
        )
        user.gitlab_token_decrypted = form.gitlab_token.data
        try:
            db.session.add(user)
            db.session.commit()
            flash(
                "Account created successfully! Your account is pending administrator approval before you can log in."
            )
            return redirect(url_for("auth.login"))
        except Exception:
            db.session.rollback()
            flash("Failed to create account. Please try again.")
            return render_template("signup.html", form=form)
    return render_template("signup.html", form=form)


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if current_user.provider != "local" or not current_user.password_hash:
        flash("Password change is only available for local accounts.")
        return redirect(url_for("index"))
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not check_password_hash(
            current_user.password_hash, form.current_password.data
        ):
            flash("Current password is incorrect")
            return render_template("change_password.html", form=form)

        current_user.password_hash = generate_password_hash(form.new_password.data)
        current_user.password_change_required = False
        db.session.commit()
        flash("Password changed successfully")
        return redirect(url_for("index"))
    return render_template("change_password.html", form=form)
