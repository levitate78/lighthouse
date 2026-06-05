import logging
from flask import current_app
import requests
import gitlab
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib

logger = logging.getLogger(__name__)


def get_fernet() -> Fernet:
    """Generate a Fernet cipher instance using the application secret key.

    Returns:
        Fernet: A Fernet cryptography cipher object.
    """
    key = hashlib.sha256(current_app.config["GLT_SECRET_KEY"].encode()).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_token(token: str) -> str | None:
    """Encrypt a GitLab personal access token.

    Args:
        token (str): The raw token string.

    Returns:
        str | None: The encrypted token string, or None if no token is provided.
    """
    if not token:
        return None
    f = get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str | None:
    """Decrypt a GitLab personal access token.

    Args:
        encrypted (str): The encrypted token string.

    Returns:
        str | None: The raw decrypted token string, or None if decryption fails.
    """
    if not encrypted:
        return None
    try:
        f = get_fernet()
        return f.decrypt(encrypted.encode()).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        logger.warning("Failed to decrypt GitLab token: %s", exc)
        return None


def get_gitlab_client(private_token: str | None = None) -> gitlab.Gitlab:
    """Create and return an authenticated GitLab client.

    Args:
        private_token (str | None): Optional GitLab token. Defaults to config token if not provided.

    Returns:
        gitlab.Gitlab: The authenticated GitLab API client instance.
    """
    config = current_app.config
    token = private_token or config.get("GITLAB_TOKEN")
    return gitlab.Gitlab(config["GITLAB_URL"], private_token=token)


def validate_gitlab_token(token: str) -> tuple[bool, str]:
    """Validate a GitLab Personal Access Token by fetching the user profile.

    Args:
        token (str): The raw token string to validate.

    Returns:
        tuple[bool, str]: A tuple where the first element is a boolean indicating validity,
            and the second element is an error message if invalid, or empty string.
    """
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
