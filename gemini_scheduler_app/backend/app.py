from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import config # Direct import for config
import os # Import the os module

db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
mail = Mail()

def create_app(config_overrides=None):
    app = Flask(__name__)
    app.config.from_object(config.Config)

    if config_overrides:
        app.config.update(config_overrides)

    # If running under pytest (based on env var set by conftest) OR if TESTING is already true
    # in the configuration (e.g., from direct override or default in config.Config),
    # then apply test-specific configurations.
    if os.environ.get('PYTEST_RUNNING') == 'true' or app.config.get("TESTING"):
        app.config["TESTING"] = True # Ensure TESTING is explicitly True

        # Construct path relative to the backend directory (where app.py is)
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        # Use TEST_DB_FILENAME from app.config if available (set by config.Config or overrides)
        # Fallback to a default name if somehow not set.
        test_db_filename = app.config.get('TEST_DB_FILENAME', 'test_scheduler.db')
        test_db_path = os.path.join(backend_dir, test_db_filename)

        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{test_db_path}"
        app.config["BCRYPT_LOG_ROUNDS"] = 4 # Consistent with conftest.py
        # Add any other essential test configurations here, e.g.,
        # app.config["JWT_SECRET_KEY"] = "test-jwt-secret-key" # if not always overridden
        # app.config["SERVER_NAME"] = "localhost.test" # if needed by services creating urls

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    from api.auth import auth_bp
    from api.event import event_bp
    # Register blueprints without additional url_prefix here,
    # as they now have the full prefix in their definition.
    app.register_blueprint(auth_bp)
    app.register_blueprint(event_bp)

    # db.create_all() is typically handled by migrations or initial setup,
    # not every time the app is created. Tests will handle their own DB setup.
    # with app.app_context():
    #     from models.user import User
    #     from models.event import Event
    #     db.create_all()

    from services import reminder_service
    @app.cli.command("send_reminders")
    def send_reminders_command():
        print("CLI: Starting reminder check...")
        result = reminder_service.send_event_reminders()
        print(result)

    return app

if __name__ == '__main__':
    app_instance = create_app()
    app_instance.run(debug=True, use_reloader=False)
