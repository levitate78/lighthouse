import logging
from flask import current_app
import requests
import gitlab
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib

logger = logging.getLogger(__name__)


def get_fernet():
    key = hashlib.sha256(current_app.config["GLT_SECRET_KEY"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_token(token):
    if not token:
        return None
    f = get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted):
    if not encrypted:
        return None
    try:
        f = get_fernet()
        return f.decrypt(encrypted.encode()).decode()
    except InvalidToken:
        logger.warning("Failed to decrypt GitLab token: invalid token")
        return None


def get_gitlab_client(private_token=None):
    """Create a GitLab client for the configured instance."""
    config = current_app.config
    token = private_token or config.get("GITLAB_TOKEN")
    return gitlab.Gitlab(config["GITLAB_URL"], private_token=token)


def validate_gitlab_token(token: str) -> tuple[bool, str]:
    """Validate a GitLab token by calling the user API."""
    if not token or not token.strip():
        return False, "Token is empty"

    token = token.strip()
    if len(token) < 10:
        return False, "Token appears to be too short"

    url = f"{current_app.config['GITLAB_URL'].rstrip('/')}/api/v4/user"
    headers = {
        "PRIVATE-TOKEN": token,
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
    except requests.RequestException as exc:
        logger.warning("GitLab token validation request failed: %s", exc)
        return False, f"GitLab API request failed: {exc}"

    if response.status_code == 200:
        return True, ""
    if response.status_code == 401:
        return False, "Token authentication failed: invalid or expired token"
    if response.status_code == 403:
        return False, "Token is valid but missing required permissions (read_api scope)"
    if response.status_code == 404:
        return False, "GitLab API endpoint not found. Check GITLAB_URL configuration."

    logger.warning(
        "GitLab token validation returned %s: %s", response.status_code, response.text
    )
    return False, f"GitLab API returned unexpected status {response.status_code}"
