import json

def test_register(client, init_database): # init_database fixture ensures a clean DB for this test
    response = client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response.status_code == 201
    assert response.json['msg'] == 'User created successfully'

    response_duplicate = client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'password': 'password123'
    })
    assert response_duplicate.status_code == 400
    assert response_duplicate.json['msg'] == 'Email already exists'

def test_login(client, init_database):
    # Register user first
    client.post('/api/auth/register', json={'email': 'loginuser@example.com', 'password': 'password123'})

    response = client.post('/api/auth/login', json={
        'email': 'loginuser@example.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    assert 'access_token' in response.json

    response_fail_password = client.post('/api/auth/login', json={
        'email': 'loginuser@example.com',
        'password': 'wrongpassword'
    })
    assert response_fail_password.status_code == 401
    assert response_fail_password.json['msg'] == 'Bad email or password'

    response_fail_user = client.post('/api/auth/login', json={
        'email': 'wronguser@example.com',
        'password': 'password123'
    })
    assert response_fail_user.status_code == 401
    assert response_fail_user.json['msg'] == 'Bad email or password'


def test_me_endpoint_protected(client, init_database):
    response_no_token = client.get('/api/auth/me')
    assert response_no_token.status_code == 401 # Expecting 401 due to @jwt_required

    # Register and login to get a token
    client.post('/api/auth/register', json={'email': 'me_user@example.com', 'password': 'password123'})
    login_response = client.post('/api/auth/login', json={'email': 'me_user@example.com', 'password': 'password123'})
    token = login_response.json['access_token']

    me_response = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me_response.status_code == 200
    assert me_response.json['logged_in_as'] == 'me_user@example.com'
    assert 'user_id' in me_response.json # Check if user_id is present

    # Test with a bad token (optional, but good for completeness)
    bad_token_response = client.get('/api/auth/me', headers={'Authorization': 'Bearer badtoken'})
    assert bad_token_response.status_code == 422 # Flask-JWT-Extended returns 422 for malformed tokens
