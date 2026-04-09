from flask_sqlalchemy import SQLAlchemy
from flask_apscheduler import APScheduler
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

# Shared Flask extensions

db = SQLAlchemy()
scheduler = APScheduler()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)
cors = CORS()
