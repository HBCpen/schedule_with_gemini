import pytest
import os
from app import create_app, db as _db # alias db to avoid pytest fixture conflict

TEST_DB_FILENAME = 'test_scheduler.db' # Keep it in backend/ for this test run for simplicity
os.environ['PYTEST_RUNNING'] = 'true' # Signal to create_app that it's a test run

@pytest.fixture(scope='session')
def app():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    test_db_path = os.path.join(backend_dir, TEST_DB_FILENAME)

    flask_app = create_app(config_overrides={
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{test_db_path}",
        "BCRYPT_LOG_ROUNDS": 4,
        "JWT_SECRET_KEY": "test-jwt-secret-key",
        "SERVER_NAME": "localhost.test" # Often useful for url_for in tests if ever needed
    })

    # create_app now handles the initial db.create_all() with the test config.
    # So, no need to call it again here explicitly for initial setup.
    # We do, however, want to ensure the DB is clean before the session starts.
    with flask_app.app_context():
        _db.drop_all()
        _db.create_all()

    yield flask_app

    # Clean up the test database file after the test session
    if os.path.exists(test_db_path):
        try:
            os.unlink(test_db_path)
        except Exception as e:
            print(f"Error removing test database {test_db_path}: {e}")


@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture(scope='function')
def init_database(app):
    with app.app_context():
        _db.drop_all()
        _db.create_all()
    yield _db
