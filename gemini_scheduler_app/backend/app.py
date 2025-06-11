from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import config # Direct import for config

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

    with app.app_context():
        from models.user import User
        from models.event import Event
        db.create_all()

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
