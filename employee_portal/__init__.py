from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from flask_wtf.csrf import CSRFProtect

from flask_bootstrap import Bootstrap

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
bootstrap = Bootstrap()
csrf = CSRFProtect()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    migrate.init_app(app, db)
    bootstrap.init_app(app)
    csrf.init_app(app)

    @login_manager.unauthorized_handler
    def unauthorized():
        return redirect(url_for('auth.login'))

    @app.before_request
    def before_request():
        from flask_login import current_user
        from datetime import datetime
        if current_user.is_authenticated:
            current_user.last_seen = datetime.utcnow()
            try:
                db.session.commit()
            except:
                db.session.rollback()

    with app.app_context():
        from . import models

    # Blueprints will be registered here
    from .auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from .main import bp as main_bp
    app.register_blueprint(main_bp)

    from .admin import bp as admin_bp
    app.register_blueprint(admin_bp)

    # Register Template Filters
    from employee_portal.utils.helpers import format_datetime_ist
    @app.template_filter('to_ist')
    def to_ist_filter(dt, fmt='%Y-%m-%d %H:%M:%S'):
        return format_datetime_ist(dt, fmt)

    return app