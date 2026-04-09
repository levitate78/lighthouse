from forms import LoginForm, SignupForm, ChangePasswordForm


def test_login_form_valid(app):
    with app.test_request_context(
        "/", method="POST", data={"username": "user", "password": "secret"}
    ):
        form = LoginForm()
        assert form.validate()


def test_signup_form_invalid_email(app):
    with app.test_request_context(
        "/",
        method="POST",
        data={
            "username": "user",
            "name": "User",
            "email": "invalid-email",
            "password": "secret",
            "confirm_password": "secret",
        },
    ):
        form = SignupForm()
        assert not form.validate()
        assert "email" in form.errors


def test_change_password_form_valid(app):
    with app.test_request_context(
        "/",
        method="POST",
        data={
            "current_password": "old",
            "new_password": "secret",
            "confirm_password": "secret",
        },
    ):
        form = ChangePasswordForm()
        assert form.validate()
