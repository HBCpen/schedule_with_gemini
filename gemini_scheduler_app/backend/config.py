import os
from dotenv import load_dotenv

load_dotenv() # Load .env file

# Get the absolute path of the backend directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Use an absolute path for the database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(BASE_DIR, 'scheduler.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'your-super-secret-jwt-key-for-dev'
    BCRYPT_LOG_ROUNDS = 12

    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.mailtrap.io' # Using mailtrap for dev
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 2525)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME') # Needs to be set in .env for real sending
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD') # Needs to be set in .env for real sending
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER') or 'reminders@gemini-scheduler.com'

    # Gemini API Key
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

    # Test Database Filename (used in app.py for testing context)
    TEST_DB_FILENAME = 'test_scheduler.db'
