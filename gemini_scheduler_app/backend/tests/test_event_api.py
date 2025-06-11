import json
from datetime import datetime, timedelta

# Helper function to get auth token, ensures user exists.
# Uses init_database to ensure it can create the user if it's the first auth action in a test.
def get_auth_token(client, init_database, email='eventuser@example.com', password='password'):
    # init_database is used to ensure the database is clean before this potential registration
    # For tests that call this multiple times with different users,
    # init_database should be called before the first user registration of that test.

    # Check if user already exists, if so, just login
    # This is a simplified check; real-world might need more robust user management for tests
    # For now, this assumes tests either use a clean DB via init_database or this helper handles it.
    # If init_database is function-scoped, each test gets a clean DB.

    # Attempt to login first, if user might exist from a previous step in the same test function
    login_resp = client.post('/api/auth/login', json={'email': email, 'password': password})
    if login_resp.status_code == 200 and 'access_token' in login_resp.json:
        return login_resp.json['access_token']

    # If login failed, try to register (works on a clean DB from init_database)
    reg_resp = client.post('/api/auth/register', json={'email': email, 'password': password})
    # if reg_resp.status_code != 201 and reg_resp.status_code != 400: # 400 if user already exists
        # print(f"DEBUG: Registration response for {email}: {reg_resp.status_code} {reg_resp.json}")

    login_response = client.post('/api/auth/login', json={'email': email, 'password': password})
    if 'access_token' not in login_response.json:
        raise Exception(f"Failed to get token for {email}. Login response: {login_response.json}")
    return login_response.json['access_token']

def test_create_event(client, init_database): # init_database ensures a clean slate
    token = get_auth_token(client, init_database, email='createeventuser@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    response = client.post('/api/events', json={
        'title': 'Test Event Create',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': 'A test event description for creation',
        'color_tag': 'blue'
    }, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 201
    assert response.json['title'] == 'Test Event Create'
    assert response.json['color_tag'] == 'blue'
    assert 'user_id' in response.json
    assert response.json['reminder_sent'] == False # Check default

def test_get_events(client, init_database):
    token = get_auth_token(client, init_database, email='geteventsuser@example.com')
    start_time1 = datetime.utcnow() + timedelta(days=1)
    end_time1 = start_time1 + timedelta(hours=1)
    start_time2 = datetime.utcnow() + timedelta(days=2)
    end_time2 = start_time2 + timedelta(hours=1)

    client.post('/api/events', json={'title': 'Event Alpha', 'start_time': start_time1.isoformat()+'Z', 'end_time': end_time1.isoformat()+'Z'}, headers={'Authorization': f'Bearer {token}'})
    client.post('/api/events', json={'title': 'Event Beta', 'start_time': start_time2.isoformat()+'Z', 'end_time': end_time2.isoformat()+'Z'}, headers={'Authorization': f'Bearer {token}'})

    response = client.get('/api/events', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert len(response.json) == 2
    assert response.json[0]['title'] == 'Event Alpha' # Sorted by start_time
    assert response.json[1]['title'] == 'Event Beta'

def test_update_event(client, init_database):
    token = get_auth_token(client, init_database, email='updateeventuser@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    create_response = client.post('/api/events', json={
        'title': 'Initial Event Title',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': 'Initial Description'
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_response.status_code == 201
    event_id = create_response.json['id']

    updated_title = "Updated Event Title"
    updated_description = "Updated Description"
    updated_start_time = start_time + timedelta(hours=2)
    updated_end_time = updated_start_time + timedelta(hours=1)

    update_response = client.put(f'/api/events/{event_id}', json={
        'title': updated_title,
        'start_time': updated_start_time.isoformat() + 'Z',
        'end_time': updated_end_time.isoformat() + 'Z',
        'description': updated_description
    }, headers={'Authorization': f'Bearer {token}'})

    assert update_response.status_code == 200
    assert update_response.json['title'] == updated_title
    assert update_response.json['description'] == updated_description
    assert update_response.json['start_time'].startswith(updated_start_time.isoformat().split('.')[0]) # Compare without microseconds for simplicity

def test_delete_event(client, init_database):
    token = get_auth_token(client, init_database, email='deleteeventuser@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    create_response = client.post('/api/events', json={
        'title': 'Event to Delete',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z'
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_response.status_code == 201
    event_id = create_response.json['id']

    delete_response = client.delete(f'/api/events/{event_id}', headers={'Authorization': f'Bearer {token}'})
    assert delete_response.status_code == 200
    assert delete_response.json['msg'] == 'Event deleted successfully'

    get_response = client.get(f'/api/events/{event_id}', headers={'Authorization': f'Bearer {token}'})
    assert get_response.status_code == 404 # Event should be gone

def test_event_access_permissions(client, init_database):
    token1 = get_auth_token(client, init_database, email='user1@example.com')
    token2 = get_auth_token(client, init_database, email='user2@example.com')

    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    create_resp_user1 = client.post('/api/events', json={
        'title': 'User1 Event', 'start_time': start_time.isoformat()+'Z', 'end_time': end_time.isoformat()+'Z'
    }, headers={'Authorization': f'Bearer {token1}'})
    assert create_resp_user1.status_code == 201
    event_id_user1 = create_resp_user1.json['id']

    # User2 tries to GET, PUT, DELETE User1's event
    get_resp_user2_fail = client.get(f'/api/events/{event_id_user1}', headers={'Authorization': f'Bearer {token2}'})
    assert get_resp_user2_fail.status_code == 404

    put_resp_user2_fail = client.put(f'/api/events/{event_id_user1}', json={'title': 'Attempted Update'}, headers={'Authorization': f'Bearer {token2}'})
    assert put_resp_user2_fail.status_code == 404

    delete_resp_user2_fail = client.delete(f'/api/events/{event_id_user1}', headers={'Authorization': f'Bearer {token2}'})
    assert delete_resp_user2_fail.status_code == 404

    # User1 can access their own event
    get_resp_user1_ok = client.get(f'/api/events/{event_id_user1}', headers={'Authorization': f'Bearer {token1}'})
    assert get_resp_user1_ok.status_code == 200
    assert get_resp_user1_ok.json['title'] == 'User1 Event'

    # User2 should have no events listed
    list_resp_user2 = client.get('/api/events', headers={'Authorization': f'Bearer {token2}'})
    assert list_resp_user2.status_code == 200
    assert len(list_resp_user2.json) == 0
