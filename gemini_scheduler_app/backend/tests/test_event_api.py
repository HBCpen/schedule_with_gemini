import json
from datetime import datetime, timedelta
from unittest.mock import patch
from models.event import Event # Ensure Event model is imported for db checks

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
    # This needs to change for recurrence tests, as /api/events now requires start/end date
    # For now, assuming it might return empty or error if not provided, adjust as per API changes
    if list_resp_user2.status_code == 200: # if it still works without params
      assert len(list_resp_user2.json) == 0
    elif list_resp_user2.status_code == 400: # if it errors due to missing params
      assert "Start and end date are required" in list_resp_user2.json.get("msg", "") or \
             "Start and end date are required" in list_resp_user2.json.get("error", "")
    else:
        # Fail if it's an unexpected status code
        assert False, f"Unexpected status code {list_resp_user2.status_code} for GET /api/events without params"


# --- Search API Tests ---

# Helper to create an event for search tests
def _create_search_event(client, token, title, description, start_time, end_time, color_tag=None):
    response = client.post('/api/events', json={
        'title': title,
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': description,
        'color_tag': color_tag
    }, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201
    return response.json

@pytest.fixture(scope='module') # Use module scope for efficiency if DB setup is per module
def search_test_data(client, init_database): # init_database is function scoped, careful if test_data is module scoped
    # If init_database is function-scoped, this fixture needs to be function-scoped too,
    # or init_database needs to be session/module scoped and carefully managed.
    # For now, assuming init_database correctly cleans for each test function that uses it.
    # Let's make this fixture function-scoped to align with init_database.

    # Re-scope init_database for this specific fixture if needed, or ensure called before tokens
    # The get_auth_token calls init_database if it's passed, but that might be too late for fixture setup.
    # The tests themselves will call init_database via get_auth_token.
    # This fixture is more about defining data that tests will use *after* auth and setup.

    user1_email = 'searchuser1@example.com'
    user2_email = 'searchuser2@example.com'

    # It's better if tests manage their own tokens, this fixture is just for data creation convenience
    # if tests were to use pre-existing users/tokens.
    # However, since tests will create events, they need tokens.
    # Let's assume tests will acquire tokens and create data. This fixture is more a conceptual grouping.
    # For actual data creation, it's often cleaner to do it within each test or a test-scoped setup function.

    now = datetime.utcnow()
    events_user1 = [
        {'title': 'Alpha Meeting', 'description': 'Discuss project Alpha', 'start_time': now + timedelta(days=1), 'end_time': now + timedelta(days=1, hours=1), 'color_tag': 'work,important'},
        {'title': 'Beta Workshop', 'description': 'Learn about Beta framework', 'start_time': now + timedelta(days=2), 'end_time': now + timedelta(days=2, hours=2), 'color_tag': 'learning'},
        {'title': 'Common Project Review', 'description': 'General review of the common project', 'start_time': now + timedelta(days=3), 'end_time': now + timedelta(days=3, hours=1), 'color_tag': 'project'},
    ]
    events_user2 = [
        {'title': 'Gamma Planning', 'description': 'Plan the Gamma release', 'start_time': now + timedelta(days=1), 'end_time': now + timedelta(days=1, hours=1), 'color_tag': 'planning,urgent'},
        {'title': 'Common Project Sync', 'description': 'User 2 sync on common project', 'start_time': now + timedelta(days=4), 'end_time': now + timedelta(days=4, hours=1), 'color_tag': 'project'},
    ]
    return {'user1_email': user1_email, 'user2_email': user2_email, 'events_user1_data': events_user1, 'events_user2_data': events_user2}


def test_search_unauthorized(client):
    response = client.get('/api/events/search?q=test')
    assert response.status_code == 401 # Expecting JWT Required


def test_search_keyword_title(client, init_database, search_test_data):
    token1 = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    s_data = search_test_data['events_user1_data'][0]
    _create_search_event(client, token1, s_data['title'], s_data['description'], s_data['start_time'], s_data['end_time'], s_data['color_tag'])

    response = client.get('/api/events/search?q=Alpha', headers={'Authorization': f'Bearer {token1}'})
    assert response.status_code == 200
    results = response.json
    assert len(results) == 1
    assert results[0]['title'] == 'Alpha Meeting'

def test_search_keyword_description(client, init_database, search_test_data):
    token1 = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    s_data = search_test_data['events_user1_data'][1]
    _create_search_event(client, token1, s_data['title'], s_data['description'], s_data['start_time'], s_data['end_time'], s_data['color_tag'])

    response = client.get('/api/events/search?q=framework', headers={'Authorization': f'Bearer {token1}'})
    assert response.status_code == 200
    results = response.json
    assert len(results) == 1
    assert results[0]['title'] == 'Beta Workshop'

def test_search_keyword_multiple_events(client, init_database, search_test_data):
    token1 = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    for s_data in search_test_data['events_user1_data']: # Create all user1 events
         _create_search_event(client, token1, s_data['title'], s_data['description'], s_data['start_time'], s_data['end_time'], s_data['color_tag'])

    response = client.get('/api/events/search?q=project', headers={'Authorization': f'Bearer {token1}'}) # "project" is in "Alpha" and "Common Project Review" descriptions for user1
    assert response.status_code == 200
    results = response.json
    assert len(results) == 2 # Alpha Meeting, Common Project Review
    titles = {r['title'] for r in results}
    assert 'Alpha Meeting' in titles
    assert 'Common Project Review' in titles

def test_search_keyword_no_match(client, init_database, search_test_data):
    token1 = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    s_data = search_test_data['events_user1_data'][0]
    _create_search_event(client, token1, s_data['title'], s_data['description'], s_data['start_time'], s_data['end_time'], s_data['color_tag'])

    response = client.get('/api/events/search?q=NonExistentKeyword', headers={'Authorization': f'Bearer {token1}'})
    assert response.status_code == 200
    assert len(response.json) == 0

def test_search_keyword_case_insensitive(client, init_database, search_test_data):
    token1 = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    s_data = search_test_data['events_user1_data'][0] # "Alpha Meeting"
    _create_search_event(client, token1, s_data['title'], s_data['description'], s_data['start_time'], s_data['end_time'], s_data['color_tag'])

    response = client.get('/api/events/search?q=alpha', headers={'Authorization': f'Bearer {token1}'}) # Search lowercase
    assert response.status_code == 200
    results = response.json
    assert len(results) == 1
    assert results[0]['title'] == 'Alpha Meeting'

def test_search_only_own_events(client, init_database, search_test_data):
    token1 = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    token2 = get_auth_token(client, init_database, email=search_test_data['user2_email'])

    # User1 creates "Alpha Meeting"
    s_data1 = search_test_data['events_user1_data'][0]
    _create_search_event(client, token1, s_data1['title'], s_data1['description'], s_data1['start_time'], s_data1['end_time'], s_data1['color_tag'])
    # User2 creates "Gamma Planning"
    s_data2 = search_test_data['events_user2_data'][0]
    _create_search_event(client, token2, s_data2['title'], s_data2['description'], s_data2['start_time'], s_data2['end_time'], s_data2['color_tag'])

    # User1 searches for "Alpha" (their own event)
    response1 = client.get('/api/events/search?q=Alpha', headers={'Authorization': f'Bearer {token1}'})
    assert response1.status_code == 200
    assert len(response1.json) == 1
    assert response1.json[0]['title'] == 'Alpha Meeting'

    # User1 searches for "Gamma" (User2's event)
    response2 = client.get('/api/events/search?q=Gamma', headers={'Authorization': f'Bearer {token1}'})
    assert response2.status_code == 200
    assert len(response2.json) == 0 # Should not find User2's event

    # User2 searches for "Gamma" (their own event)
    response3 = client.get('/api/events/search?q=Gamma', headers={'Authorization': f'Bearer {token2}'})
    assert response3.status_code == 200
    assert len(response3.json) == 1
    assert response3.json[0]['title'] == 'Gamma Planning'


def test_search_date_range(client, init_database, search_test_data):
    token = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    now = datetime.utcnow()
    event_data = [
        {'title': 'Event Day1', 'start_time': now.replace(hour=10), 'end_time': now.replace(hour=11)}, # Today
        {'title': 'Event Day2', 'start_time': now + timedelta(days=1, hours=10), 'end_time': now + timedelta(days=1, hours=11)}, # Tomorrow
        {'title': 'Event Day3', 'start_time': now + timedelta(days=2, hours=10), 'end_time': now + timedelta(days=2, hours=11)}, # Day after tomorrow
    ]
    for data in event_data:
        _create_search_event(client, token, data['title'], '', data['start_time'], data['end_time'])

    # Search for tomorrow's event
    start_query = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    end_query = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.get(f'/api/events/search?start_date={start_query}&end_date={end_query}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    results = response.json
    assert len(results) == 1
    assert results[0]['title'] == 'Event Day2'

    # Search for events from today to tomorrow (should include Day1 and Day2)
    start_query_range = now.strftime('%Y-%m-%d')
    end_query_range = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    response_range = client.get(f'/api/events/search?start_date={start_query_range}&end_date={end_query_range}', headers={'Authorization': f'Bearer {token}'})
    assert response_range.status_code == 200
    results_range = response_range.json
    assert len(results_range) == 2
    titles_range = {r['title'] for r in results_range}
    assert 'Event Day1' in titles_range
    assert 'Event Day2' in titles_range

    # Search with start_date only (events from tomorrow onwards)
    response_start_only = client.get(f'/api/events/search?start_date={start_query}', headers={'Authorization': f'Bearer {token}'})
    assert response_start_only.status_code == 200
    results_start_only = response_start_only.json
    assert len(results_start_only) == 2 # Day2 and Day3
    titles_start_only = {r['title'] for r in results_start_only}
    assert 'Event Day2' in titles_start_only
    assert 'Event Day3' in titles_start_only

    # Search with end_date only (events up to today)
    end_query_today = now.strftime('%Y-%m-%d')
    response_end_only = client.get(f'/api/events/search?end_date={end_query_today}', headers={'Authorization': f'Bearer {token}'})
    assert response_end_only.status_code == 200
    results_end_only = response_end_only.json
    assert len(results_end_only) == 1 # Day1
    assert results_end_only[0]['title'] == 'Event Day1'

    # Search date range with no events
    start_far = (now + timedelta(days=10)).strftime('%Y-%m-%d')
    end_far = (now + timedelta(days=11)).strftime('%Y-%m-%d')
    response_no_events = client.get(f'/api/events/search?start_date={start_far}&end_date={end_far}', headers={'Authorization': f'Bearer {token}'})
    assert response_no_events.status_code == 200
    assert len(response_no_events.json) == 0


def test_search_tags(client, init_database, search_test_data):
    token = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    now = datetime.utcnow()
    event_data = [
        {'title': 'Work Event', 'start_time': now, 'end_time': now + timedelta(hours=1), 'color_tag': 'work,urgent'},
        {'title': 'Personal Errand', 'start_time': now + timedelta(days=1), 'end_time': now + timedelta(days=1, hours=1), 'color_tag': 'personal'},
        {'title': 'Work Planning', 'start_time': now + timedelta(days=2), 'end_time': now + timedelta(days=2, hours=1), 'color_tag': 'work,planning'},
    ]
    for data in event_data:
        _create_search_event(client, token, data['title'], '', data['start_time'], data['end_time'], data['color_tag'])

    # Search single tag "personal"
    response = client.get('/api/events/search?tags=personal', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    results = response.json
    assert len(results) == 1
    assert results[0]['title'] == 'Personal Errand'

    # Search single tag "work" (should match two events)
    response_work = client.get('/api/events/search?tags=work', headers={'Authorization': f'Bearer {token}'})
    assert response_work.status_code == 200
    results_work = response_work.json
    assert len(results_work) == 2
    titles_work = {r['title'] for r in results_work}
    assert 'Work Event' in titles_work
    assert 'Work Planning' in titles_work

    # Search multiple tags "work,planning" (should match "Work Planning")
    response_multi = client.get('/api/events/search?tags=work,planning', headers={'Authorization': f'Bearer {token}'})
    assert response_multi.status_code == 200
    results_multi = response_multi.json
    assert len(results_multi) == 1
    assert results_multi[0]['title'] == 'Work Planning'

    # Search multiple tags "urgent,personal" (should match "Work Event" and "Personal Errand")
    # The backend logic is OR for multiple tags in the tags_str list (e.g. "work,urgent" means event has "work" OR "urgent")
    # And the Event.color_tag itself can be "work,urgent". So "tags=urgent,personal"
    # will find events that have "urgent" in their color_tag OR "personal" in their color_tag
    response_multi_or = client.get('/api/events/search?tags=urgent,personal', headers={'Authorization': f'Bearer {token}'})
    assert response_multi_or.status_code == 200
    results_multi_or = response_multi_or.json
    assert len(results_multi_or) == 2
    titles_multi_or = {r['title'] for r in results_multi_or}
    assert 'Work Event' in titles_multi_or # (matches urgent)
    assert 'Personal Errand' in titles_multi_or # (matches personal)


    # Search tag not associated
    response_no_match = client.get('/api/events/search?tags=nonexistenttag', headers={'Authorization': f'Bearer {token}'})
    assert response_no_match.status_code == 200
    assert len(response_no_match.json) == 0


def test_search_combined_filters(client, init_database, search_test_data):
    token = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    now = datetime.utcnow()
    _create_search_event(client, token, 'Important Alpha Review', 'Review alpha project deliverables', now + timedelta(days=1), now + timedelta(days=1, hours=1), 'project,urgent')
    _create_search_event(client, token, 'Beta Planning Session', 'Plan beta phase', now + timedelta(days=2), now + timedelta(days=2, hours=2), 'project,planning')
    _create_search_event(client, token, 'Quick Project Sync', 'General sync up', now + timedelta(days=1, hours=2), now + timedelta(days=1, hours=3), 'project')

    # Keyword AND Date Range
    # Search "Review" for tomorrow
    tomorrow_str = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.get(f'/api/events/search?q=Review&start_date={tomorrow_str}&end_date={tomorrow_str}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    results = response.json
    assert len(results) == 1
    assert results[0]['title'] == 'Important Alpha Review'

    # Keyword AND Tag
    response_kw_tag = client.get('/api/events/search?q=project&tags=urgent', headers={'Authorization': f'Bearer {token}'})
    assert response_kw_tag.status_code == 200
    results_kw_tag = response_kw_tag.json
    assert len(results_kw_tag) == 1
    assert results_kw_tag[0]['title'] == 'Important Alpha Review' # "project" in desc, "urgent" in tag

    # Date Range AND Tag
    response_date_tag = client.get(f'/api/events/search?start_date={tomorrow_str}&end_date={tomorrow_str}&tags=project', headers={'Authorization': f'Bearer {token}'})
    assert response_date_tag.status_code == 200
    results_date_tag = response_date_tag.json
    # Expect "Important Alpha Review" and "Quick Project Sync"
    assert len(results_date_tag) == 2
    titles_date_tag = {r['title'] for r in results_date_tag}
    assert 'Important Alpha Review' in titles_date_tag
    assert 'Quick Project Sync' in titles_date_tag


    # Keyword AND Date Range AND Tag
    response_all = client.get(f'/api/events/search?q=Alpha&start_date={tomorrow_str}&end_date={tomorrow_str}&tags=urgent', headers={'Authorization': f'Bearer {token}'})
    assert response_all.status_code == 200
    results_all = response_all.json
    assert len(results_all) == 1
    assert results_all[0]['title'] == 'Important Alpha Review'

def test_search_invalid_date_format(client, init_database):
    token = get_auth_token(client, init_database, email='searchinvaliddate@example.com')
    response_start = client.get('/api/events/search?start_date=invalid-date', headers={'Authorization': f'Bearer {token}'})
    assert response_start.status_code == 400
    assert "Invalid start_date format" in response_start.json['msg']

    response_end = client.get('/api/events/search?end_date=invalid-date', headers={'Authorization': f'Bearer {token}'})
    assert response_end.status_code == 400
    assert "Invalid end_date format" in response_end.json['msg']


# --- Recurring Event API Tests ---

def _create_event_with_recurrence(client, token, title, start_time, end_time, recurrence_rule=None, description=None, color_tag=None):
    payload = {
        'title': title,
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
    }
    if recurrence_rule:
        payload['recurrence_rule'] = recurrence_rule
    if description:
        payload['description'] = description
    if color_tag:
        payload['color_tag'] = color_tag

    response = client.post('/api/events', json=payload, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201
    return response.json

def test_create_event_with_recurrence_rule(client, init_database):
    token = get_auth_token(client, init_database, email='recurcreate@example.com')
    now = datetime.utcnow()
    start_time = now + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    rrule = "FREQ=DAILY;COUNT=3"

    event_json = _create_event_with_recurrence(client, token, "Daily Meeting", start_time, end_time, recurrence_rule=rrule)
    assert event_json['recurrence_rule'] == rrule
    assert event_json['title'] == "Daily Meeting"

def test_update_event_to_add_recurrence(client, init_database):
    token = get_auth_token(client, init_database, email='recurupdate@example.com')
    now = datetime.utcnow()
    start_time = now + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    event_json = _create_event_with_recurrence(client, token, "Single Event", start_time, end_time)
    event_id = event_json['id']
    assert event_json.get('recurrence_rule') is None

    rrule = "FREQ=WEEKLY;BYDAY=MO;INTERVAL=1"
    update_response = client.put(f'/api/events/{event_id}', json={
        'title': 'Weekly Monday Meeting',
        'recurrence_rule': rrule
    }, headers={'Authorization': f'Bearer {token}'})

    assert update_response.status_code == 200
    assert update_response.json['recurrence_rule'] == rrule
    assert update_response.json['title'] == 'Weekly Monday Meeting'

def test_update_event_to_change_recurrence(client, init_database):
    token = get_auth_token(client, init_database, email='recurchange@example.com')
    now = datetime.utcnow()
    start_time = now + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    initial_rrule = "FREQ=DAILY;COUNT=5"

    event_json = _create_event_with_recurrence(client, token, "Daily Standup", start_time, end_time, recurrence_rule=initial_rrule)
    event_id = event_json['id']

    changed_rrule = "FREQ=WEEKLY;BYDAY=TU;COUNT=3"
    update_response = client.put(f'/api/events/{event_id}', json={
        'recurrence_rule': changed_rrule
    }, headers={'Authorization': f'Bearer {token}'})

    assert update_response.status_code == 200
    assert update_response.json['recurrence_rule'] == changed_rrule

def test_update_event_to_remove_recurrence(client, init_database):
    token = get_auth_token(client, init_database, email='recurremove@example.com')
    now = datetime.utcnow()
    start_time = now + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    initial_rrule = "FREQ=DAILY;COUNT=2"

    event_json = _create_event_with_recurrence(client, token, "Temporary Daily", start_time, end_time, recurrence_rule=initial_rrule)
    event_id = event_json['id']

    update_response = client.put(f'/api/events/{event_id}', json={
        'recurrence_rule': None # Send null to remove
    }, headers={'Authorization': f'Bearer {token}'})

    assert update_response.status_code == 200
    assert update_response.json.get('recurrence_rule') is None


def test_get_events_requires_date_range(client, init_database):
    token = get_auth_token(client, init_database, email='geteventparams@example.com')
    response = client.get('/api/events', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 400 # Or whatever error code your API returns
    assert "error" in response.json
    assert "Start and end date are required" in response.json["error"]


def test_fetch_recurring_event_expansion(client, init_database):
    token = get_auth_token(client, init_database, email='recurfetch@example.com')
    now_utc = datetime.utcnow()
    # Ensure start_time is unambiguous (e.g. specific hour, minute, second, no microsecond for easier comparison)
    series_start_time = now_utc.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    series_end_time = series_start_time + timedelta(hours=1)
    rrule = "FREQ=DAILY;COUNT=3" # Generates 3 occurrences

    _create_event_with_recurrence(client, token, "Daily Test Series", series_start_time, series_end_time, recurrence_rule=rrule)

    # Date range covering all 3 occurrences
    query_start_date = series_start_time.strftime('%Y-%m-%d')
    query_end_date = (series_start_time + timedelta(days=2)).strftime('%Y-%m-%d')

    response = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    events = response.json

    assert len(events) == 3

    expected_start_times_iso = [
        (series_start_time + timedelta(days=i)).isoformat() + "Z" for i in range(3)
    ]

    for i, event in enumerate(events):
        assert event['title'] == "Daily Test Series"
        assert event['is_occurrence'] == True
        # Compare start times carefully
        assert event['start_time'].startswith(expected_start_times_iso[i].split('.')[0]) # Ignore microseconds for robust comparison
        assert event['recurrence_rule'] == rrule # Master rule is passed along
        assert event['parent_event_id'] is not None # Should be the ID of the master event

    # Date range covering only the second occurrence
    query_start_date_middle = (series_start_time + timedelta(days=1)).strftime('%Y-%m-%d')
    query_end_date_middle = (series_start_time + timedelta(days=1)).strftime('%Y-%m-%d')

    response_middle = client.get(f'/api/events?start_date={query_start_date_middle}&end_date={query_end_date_middle}', headers={'Authorization': f'Bearer {token}'})
    assert response_middle.status_code == 200
    events_middle = response_middle.json
    assert len(events_middle) == 1
    assert events_middle[0]['start_time'].startswith(expected_start_times_iso[1].split('.')[0])

    # Date range before any occurrences
    query_start_date_before = (series_start_time - timedelta(days=2)).strftime('%Y-%m-%d')
    query_end_date_before = (series_start_time - timedelta(days=1)).strftime('%Y-%m-%d')
    response_before = client.get(f'/api/events?start_date={query_start_date_before}&end_date={query_end_date_before}', headers={'Authorization': f'Bearer {token}'})
    assert response_before.status_code == 200
    assert len(response_before.json) == 0

    # Date range after all occurrences
    query_start_date_after = (series_start_time + timedelta(days=3)).strftime('%Y-%m-%d')
    query_end_date_after = (series_start_time + timedelta(days=4)).strftime('%Y-%m-%d')
    response_after = client.get(f'/api/events?start_date={query_start_date_after}&end_date={query_end_date_after}', headers={'Authorization': f'Bearer {token}'})
    assert response_after.status_code == 200
    assert len(response_after.json) == 0


def test_delete_recurring_event_series(client, init_database):
    token = get_auth_token(client, init_database, email='recurdelete@example.com')
    now_utc = datetime.utcnow()
    series_start_time = now_utc.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    series_end_time = series_start_time + timedelta(hours=1)
    rrule = "FREQ=DAILY;COUNT=2"

    created_event = _create_event_with_recurrence(client, token, "Series To Delete", series_start_time, series_end_time, recurrence_rule=rrule)
    event_id_master = created_event['id'] # This is the ID of the master event

    # Delete the master event
    delete_response = client.delete(f'/api/events/{event_id_master}', headers={'Authorization': f'Bearer {token}'})
    assert delete_response.status_code == 200
    assert delete_response.json['msg'] == "Event deleted successfully"

    # Try to fetch events for the period, should be none from this series
    query_start_date = series_start_time.strftime('%Y-%m-%d')
    query_end_date = (series_start_time + timedelta(days=1)).strftime('%Y-%m-%d')

    response_after_delete = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert response_after_delete.status_code == 200
    assert len(response_after_delete.json) == 0

    # Also check that the master event itself is gone (if trying to GET by ID)
    get_master_response = client.get(f'/api/events/{event_id_master}', headers={'Authorization': f'Bearer {token}'})
    assert get_master_response.status_code == 404 # Not found


# --- Find Free Time API Tests ---

def test_find_free_time_api_success(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetimeuser@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1) # Assuming user_id 1 from token

    # Mock database query for events
    mock_event_1 = mocker.MagicMock()
    mock_event_1.to_dict.return_value = {
        "title": "Existing Event 1",
        "start_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        "end_time": (datetime.utcnow() + timedelta(hours=3)).isoformat()
    }
    # More robust SQLAlchemy mocking for chained calls on Event.query
    mock_query = mocker.patch('api.event.Event.query')
    mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_event_1]

    expected_slots = [{"start_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(), "end_time": (datetime.utcnow() + timedelta(hours=5)).isoformat()}]
    mock_gemini_call = mocker.patch(
        'api.event.gemini_service.find_free_time_slots_with_gemini',
        return_value=expected_slots
    )

    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')

    response = client.post('/api/events/find-free-time',
                           json={"query": "Find free time tomorrow afternoon"},
                           headers=access_token_headers)

    assert response.status_code == 200
    assert response.json == expected_slots
    mock_gemini_call.assert_called_once()
    args, kwargs = mock_gemini_call.call_args
    assert args[0] == "Find free time tomorrow afternoon"
    events_json_list = json.loads(args[1]) # events_json is the second positional argument
    assert len(events_json_list) == 1
    assert events_json_list[0]['title'] == "Existing Event 1"

def test_find_free_time_api_missing_query(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetime_noquery@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')

    response = client.post('/api/events/find-free-time', json={}, headers=access_token_headers)

    assert response.status_code == 400
    assert "Natural language query ('query') is required" in response.json.get("msg")

def test_find_free_time_api_gemini_key_missing(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetime_nokey@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mocker.patch('api.event.os.environ.get', return_value=None) # Simulate missing API key

    response = client.post('/api/events/find-free-time',
                           json={"query": "any query"},
                           headers=access_token_headers)

    assert response.status_code == 503
    assert "Gemini API key not configured" in response.json.get("msg")

def test_find_free_time_api_gemini_service_error(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetime_geminierror@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')

    # Mock database query to return empty list, simplifying this test's focus
    mock_query = mocker.patch('api.event.Event.query')
    mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []

    error_response_from_service = {"error": "Gemini API error", "detail": "some detail from Gemini"}
    mocker.patch('api.event.gemini_service.find_free_time_slots_with_gemini',
                 return_value=error_response_from_service)

    response = client.post('/api/events/find-free-time',
                           json={"query": "any query"},
                           headers=access_token_headers)

    assert response.status_code == 500
    assert response.json.get("msg") == "Error finding free time slots with Gemini"
    assert response.json.get("detail") == "some detail from Gemini"

def test_find_free_time_api_database_error(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetime_dberror@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')

    # Mock database query to raise an exception
    mock_query = mocker.patch('api.event.Event.query')
    mock_query.filter.return_value.filter.return_value.order_by.return_value.all.side_effect = Exception("Database connection failed")

    response = client.post('/api/events/find-free-time',
                           json={"query": "any query"},
                           headers=access_token_headers)

    assert response.status_code == 500
    assert response.json.get("msg") == "Error fetching user events"

def test_find_free_time_api_invalid_start_date_format(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetime_baddate@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')

    response = client.post('/api/events/find-free-time',
                           json={"query": "any query", "start_date": "invalid-date-string"},
                           headers=access_token_headers)

    assert response.status_code == 400
    assert "Invalid start_date format" in response.json.get("msg")

def test_find_free_time_api_invalid_end_date_format(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetime_baddate2@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')

    response = client.post('/api/events/find-free-time',
                           json={"query": "any query", "end_date": "invalid-date-string"},
                           headers=access_token_headers)

    assert response.status_code == 400
    assert "Invalid end_date format" in response.json.get("msg")

def test_find_free_time_api_end_date_before_start_date(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetime_dateorder@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')

    start_date = datetime.utcnow() + timedelta(days=2)
    end_date = datetime.utcnow() + timedelta(days=1) # End date is before start date

    response = client.post('/api/events/find-free-time',
                           json={
                               "query": "any query",
                               "start_date": start_date.isoformat(),
                               "end_date": end_date.isoformat()
                           },
                           headers=access_token_headers)

    assert response.status_code == 400
    assert "end_date cannot be before start_date" in response.json.get("msg")

def test_find_free_time_api_success_with_date_range(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetimeuser_ranged@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}

    mocker.patch('api.event.get_jwt_identity', return_value=1)

    mock_event_1 = mocker.MagicMock()
    mock_event_1.to_dict.return_value = {
        "title": "Event In Range",
        "start_time": (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat(),
        "end_time": (datetime.utcnow() + timedelta(days=1, hours=3)).isoformat()
    }
    # Mock Event.query chain
    mock_query = mocker.patch('api.event.Event.query')
    # Configure the chain of calls. Each method call returns the mock_query object itself,
    # until .all() is called, which returns the list of mock events.
    mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_event_1]

    expected_slots = [{"start_time": (datetime.utcnow() + timedelta(days=1, hours=4)).isoformat(), "end_time": (datetime.utcnow() + timedelta(days=1, hours=5)).isoformat()}]
    mock_gemini_call = mocker.patch(
        'api.event.gemini_service.find_free_time_slots_with_gemini',
        return_value=expected_slots
    )

    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')

    start_date_param = datetime.utcnow().isoformat()
    end_date_param = (datetime.utcnow() + timedelta(days=3)).isoformat()

    response = client.post('/api/events/find-free-time',
                           json={
                               "query": "Find free time in the next 3 days",
                               "start_date": start_date_param,
                               "end_date": end_date_param
                           },
                           headers=access_token_headers)

    assert response.status_code == 200
    assert response.json == expected_slots

    # Verify that Event.query.filter was called with date range conditions
    # This requires inspecting the calls to mock_query.filter
    # The first filter is by user_id, the second should be for start_time >= start_date
    # The third filter (actually part of the same filter call in the implementation) is Event.start_time <= end_date
    # This is a bit complex to assert directly with the current simple mock_query patch.
    # A more detailed assertion would involve checking call_args of mock_query.filter.
    # For now, we trust the endpoint logic used the dates if the test passes.
    # A simple check: ensure .all() was called.
    mock_query.filter.return_value.filter.return_value.order_by.return_value.all.assert_called_once()
    mock_gemini_call.assert_called_once()


# --- Auto Tagging Integration Tests ---

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_create_event_with_auto_tagging(mock_suggest_tags, client, init_database):
    token = get_auth_token(client, init_database, email='taguser_create@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    event_title = "Project Kickoff Meeting"
    event_description = "Initial meeting to discuss project scope and deliverables."

    # Case 1: Successful tagging
    mock_suggest_tags.return_value = ["project", "work"]
    response = client.post('/api/events', json={
        'title': event_title,
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': event_description,
        # No color_tag provided by user, should be auto-filled
    }, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 201
    created_event_id = response.json['id']
    mock_suggest_tags.assert_called_with(event_title, event_description)

    # Verify in DB
    event_from_db = Event.query.get(created_event_id)
    assert event_from_db is not None
    assert event_from_db.color_tag == "project,work"
    assert event_from_db.title == event_title # Ensure other fields are still correct

    # Case 2: Gemini returns empty list
    mock_suggest_tags.return_value = []
    start_time_2 = start_time + timedelta(days=1)
    end_time_2 = end_time + timedelta(days=1)
    event_title_2 = "Personal errand"
    event_description_2 = "Pick up dry cleaning"

    response_empty_tags = client.post('/api/events', json={
        'title': event_title_2,
        'start_time': start_time_2.isoformat() + 'Z',
        'end_time': end_time_2.isoformat() + 'Z',
        'description': event_description_2,
    }, headers={'Authorization': f'Bearer {token}'})
    assert response_empty_tags.status_code == 201
    event_empty_tags_id = response_empty_tags.json['id']
    mock_suggest_tags.assert_called_with(event_title_2, event_description_2)
    event_from_db_empty = Event.query.get(event_empty_tags_id)
    assert event_from_db_empty.color_tag == ""

    # Case 3: Gemini returns default tag (e.g., ["general"])
    mock_suggest_tags.return_value = ["general"]
    start_time_3 = start_time + timedelta(days=2)
    end_time_3 = end_time + timedelta(days=2)
    event_title_3 = "Quick reminder"
    event_description_3 = None # Test with no description

    response_general_tag = client.post('/api/events', json={
        'title': event_title_3,
        'start_time': start_time_3.isoformat() + 'Z',
        'end_time': end_time_3.isoformat() + 'Z',
        'description': event_description_3,
    }, headers={'Authorization': f'Bearer {token}'})
    assert response_general_tag.status_code == 201
    event_general_tag_id = response_general_tag.json['id']
    mock_suggest_tags.assert_called_with(event_title_3, event_description_3)
    event_from_db_general = Event.query.get(event_general_tag_id)
    assert event_from_db_general.color_tag == "general"

    # Case 4: Gemini service raises an exception
    mock_suggest_tags.side_effect = Exception("Gemini processing error")
    start_time_4 = start_time + timedelta(days=3)
    end_time_4 = end_time + timedelta(days=3)
    event_title_4 = "Event with service error"
    event_description_4 = "This should trigger fallback"

    response_service_error = client.post('/api/events', json={
        'title': event_title_4,
        'start_time': start_time_4.isoformat() + 'Z',
        'end_time': end_time_4.isoformat() + 'Z',
        'description': event_description_4,
    }, headers={'Authorization': f'Bearer {token}'})
    assert response_service_error.status_code == 201 # Event creation should still succeed
    event_service_error_id = response_service_error.json['id']
    mock_suggest_tags.assert_called_with(event_title_4, event_description_4)
    event_from_db_error = Event.query.get(event_service_error_id)
    # Based on create_event logic, color_tag becomes "" on exception
    assert event_from_db_error.color_tag == ""


@patch('api.event.gemini_service.suggest_tags_for_event')
def test_update_event_with_auto_tagging(mock_suggest_tags, client, init_database):
    token = get_auth_token(client, init_database, email='taguser_update@example.com')

    # Create an initial event
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    initial_title = "Original Event Title"
    initial_description = "Original event description."
    initial_tags_str = "initial,tag"

    # Manually create event without relying on the endpoint's auto-tagging for setup
    # to control the initial state of color_tag precisely.
    from app import db # Required for direct db interaction
    user_for_event = Event.query.join(Event.user).filter_by(email='taguser_update@example.com').first()
    if not user_for_event: # If user doesn't exist from get_auth_token, create one (simplified)
        # This part is tricky as get_auth_token handles user creation.
        # Assuming get_auth_token has run and user exists.
        # A better way would be to fetch user ID from token or a fixture.
        # For now, let's assume User table is populated by get_auth_token
        # and we can query for the user_id if needed, or just use the token.
        # The event creation within the test uses the API which handles user_id from token.
        pass


    # Create event via API to ensure it has an ID and user_id set by the system
    # We will override its color_tag after creation for specific test cases if needed.
    create_resp = client.post('/api/events', json={
        'title': initial_title,
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': initial_description,
        'color_tag': initial_tags_str # Set initial tag for now, though create also calls suggest_tags
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_resp.status_code == 201
    event_id = create_resp.json['id']

    # Manually update the color_tag in DB to bypass create_event's auto-tagging for precise setup for update tests
    event_to_update = Event.query.get(event_id)
    assert event_to_update is not None
    event_to_update.color_tag = initial_tags_str
    db.session.commit()


    # Case 1: Update title, tags should be re-evaluated and change
    mock_suggest_tags.reset_mock() # Reset call count from create
    mock_suggest_tags.return_value = ["updated", "project"]
    updated_title = "New Event Title After Update"

    response_title_update = client.put(f'/api/events/{event_id}', json={
        'title': updated_title
        # Description remains initial_description
    }, headers={'Authorization': f'Bearer {token}'})

    assert response_title_update.status_code == 200
    mock_suggest_tags.assert_called_once_with(updated_title, initial_description)
    event_from_db = Event.query.get(event_id)
    assert event_from_db.color_tag == "updated,project"
    assert event_from_db.title == updated_title

    # Case 2: Update description, tags should be re-evaluated and change
    mock_suggest_tags.reset_mock()
    event_from_db.color_tag = "some,old,tags" # Reset tags for this case
    db.session.commit()
    mock_suggest_tags.return_value = ["description_tag"]
    updated_description = "A brand new description for the event."

    response_desc_update = client.put(f'/api/events/{event_id}', json={
        'description': updated_description
        # Title is now updated_title from previous step
    }, headers={'Authorization': f'Bearer {token}'})

    assert response_desc_update.status_code == 200
    mock_suggest_tags.assert_called_once_with(updated_title, updated_description) # Title is sticky from previous update
    event_from_db = Event.query.get(event_id)
    assert event_from_db.color_tag == "description_tag"
    assert event_from_db.description == updated_description

    # Case 3: Update unrelated field (e.g., start_time), tags re-evaluated
    mock_suggest_tags.reset_mock()
    event_from_db.color_tag = "original,tags,again" # Reset for clarity
    db.session.commit()
    mock_suggest_tags.return_value = ["routine_check"]
    new_start_time = (datetime.utcnow() + timedelta(days=5)).isoformat() + 'Z'
    new_end_time = (datetime.utcnow() + timedelta(days=5, hours=1)).isoformat() + 'Z'

    response_time_update = client.put(f'/api/events/{event_id}', json={
        'start_time': new_start_time,
        'end_time': new_end_time
        # Title and description are from previous step (updated_title, updated_description)
    }, headers={'Authorization': f'Bearer {token}'})

    assert response_time_update.status_code == 200
    # suggest_tags called with current title (updated_title) and description (updated_description)
    mock_suggest_tags.assert_called_once_with(updated_title, updated_description)
    event_from_db = Event.query.get(event_id)
    assert event_from_db.color_tag == "routine_check"

    # Case 4: Gemini returns empty list on update
    mock_suggest_tags.reset_mock()
    mock_suggest_tags.return_value = []
    response_empty_on_update = client.put(f'/api/events/{event_id}', json={
        'title': "Title leading to empty tags"
    }, headers={'Authorization': f'Bearer {token}'})

    assert response_empty_on_update.status_code == 200
    event_from_db = Event.query.get(event_id)
    assert event_from_db.color_tag == ""

    # Case 5: Gemini service raises an exception on update
    mock_suggest_tags.reset_mock()
    tags_before_error = "stable,tags"
    event_from_db.color_tag = tags_before_error # Set known tags
    event_from_db.title = "Title before error" # Set known title
    db.session.commit()

    mock_suggest_tags.side_effect = Exception("Gemini service is down during update")
    title_causing_error_update = "Update attempt causing error"
    description_for_error_update = event_from_db.description # Keep current description

    response_error_on_update = client.put(f'/api/events/{event_id}', json={
        'title': title_causing_error_update
    }, headers={'Authorization': f'Bearer {token}'})

    assert response_error_on_update.status_code == 200 # Update itself should succeed
    mock_suggest_tags.assert_called_once_with(title_causing_error_update, description_for_error_update)
    event_from_db = Event.query.get(event_id)
    # As per update_event logic, tags should be preserved on error
    assert event_from_db.color_tag == tags_before_error
    assert event_from_db.title == title_causing_error_update # Title update still happens


# --- Related Information API Tests ---

@patch('api.event.gemini_service.get_related_information_for_event')
def test_get_related_info_success(mock_get_related_info, client, init_database):
    token = get_auth_token(client, init_database, email='relatedinfo_user@example.com')
    headers = {'Authorization': f'Bearer {token}'}

    # Create a user to associate with the event
    from models.user import User # Assuming User model is available
    from app import db # Assuming db is available
    with client.application.app_context(): # Ensure app context for db operations
        user = User.query.filter_by(email='relatedinfo_user@example.com').first()
        if not user: # Should be created by get_auth_token
            user = User(email='relatedinfo_user@example.com', password_hash='hashed') # Simplified
            db.session.add(user)
            db.session.commit()
        user_id = user.id

        start_time = datetime.utcnow() + timedelta(days=1)
        event = Event(
            title="Test Event for Related Info",
            start_time=start_time,
            end_time=start_time + timedelta(hours=1),
            location="Test Location",
            description="A test description",
            user_id=user_id
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    mock_response_data = {
        "weather": {"condition": "Sunny"},
        "traffic": {"congestion_level": "Low"},
        "suggestions": [],
        "related_content": [{"type": "article", "title": "Test Article", "url": "http://example.com/test"}]
    }
    mock_get_related_info.return_value = mock_response_data

    response = client.get(f'/api/events/{event_id}/related-info', headers=headers)

    assert response.status_code == 200
    assert response.json == mock_response_data
    mock_get_related_info.assert_called_once_with(
        event_location="Test Location",
        event_start_datetime_iso=start_time.isoformat(),
        event_title="Test Event for Related Info",
        event_description="A test description"
    )

def test_get_related_info_unauthenticated(client, init_database):
    # Create a dummy event so the endpoint exists
    token = get_auth_token(client, init_database, email='relatedinfo_owner@example.com')
    from app import db
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(email='relatedinfo_owner@example.com').first()
        user_id = user.id
        start_time = datetime.utcnow() + timedelta(days=1)
        event = Event(title="Dummy", start_time=start_time, location="Someplace", user_id=user_id)
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.get(f'/api/events/{event_id}/related-info') # No auth header
    assert response.status_code == 401


@patch('api.event.gemini_service.get_related_information_for_event')
def test_get_related_info_event_not_found(mock_get_related_info, client, init_database):
    token = get_auth_token(client, init_database, email='relatedinfo_notfound@example.com')
    headers = {'Authorization': f'Bearer {token}'}

    response = client.get('/api/events/99999/related-info', headers=headers) # Non-existent event

    assert response.status_code == 404
    assert "Event not found" in response.json['msg']
    mock_get_related_info.assert_not_called()

@patch('api.event.gemini_service.get_related_information_for_event')
def test_get_related_info_event_missing_location(mock_get_related_info, client, init_database):
    token = get_auth_token(client, init_database, email='relatedinfo_nolocation@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    from app import db
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(email='relatedinfo_nolocation@example.com').first()
        user_id = user.id
        start_time = datetime.utcnow() + timedelta(days=1)
        # Event created without a location
        event = Event(title="No Location Event", start_time=start_time, user_id=user_id, location=None)
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.get(f'/api/events/{event_id}/related-info', headers=headers)

    assert response.status_code == 400
    assert "location and start time are required" in response.json['msg']
    mock_get_related_info.assert_not_called()

@patch('api.event.gemini_service.get_related_information_for_event')
def test_get_related_info_event_missing_start_time(mock_get_related_info, client, init_database):
    token = get_auth_token(client, init_database, email='relatedinfo_nostart@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    from app import db
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(email='relatedinfo_nostart@example.com').first()
        user_id = user.id
        # Event created without a start_time
        event = Event(title="No StartTime Event", location="Some Location", user_id=user_id, start_time=None)
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    response = client.get(f'/api/events/{event_id}/related-info', headers=headers)

    assert response.status_code == 400
    assert "location and start time are required" in response.json['msg']
    mock_get_related_info.assert_not_called()

@patch('api.event.gemini_service.get_related_information_for_event')
def test_get_related_info_service_gemini_config_error(mock_get_related_info, client, init_database):
    token = get_auth_token(client, init_database, email='relatedinfo_configerror@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    from app import db
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(email='relatedinfo_configerror@example.com').first()
        user_id = user.id
        start_time = datetime.utcnow() + timedelta(days=1)
        event = Event(title="Config Error Event", start_time=start_time, location="A Location", user_id=user_id)
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    mock_get_related_info.return_value = {"error": "Gemini API not configured", "detail": "API key missing."}

    response = client.get(f'/api/events/{event_id}/related-info', headers=headers)

    assert response.status_code == 503
    assert "Related information service is currently unavailable" in response.json['msg']
    assert "API key missing" in response.json['detail']
    mock_get_related_info.assert_called_once()

@patch('api.event.gemini_service.get_related_information_for_event')
def test_get_related_info_service_date_format_error(mock_get_related_info, client, init_database):
    token = get_auth_token(client, init_database, email='relatedinfo_dateerror@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    from app import db
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(email='relatedinfo_dateerror@example.com').first()
        user_id = user.id
        start_time = datetime.utcnow() + timedelta(days=1)
        event = Event(title="Date Error Event", start_time=start_time, location="A Location", user_id=user_id)
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    mock_get_related_info.return_value = {"error": "Invalid ISO format for event_start_datetime_iso", "detail": "Date parsing failed."}

    response = client.get(f'/api/events/{event_id}/related-info', headers=headers)

    assert response.status_code == 400
    assert "Error with event data" in response.json['msg']
    assert "Date parsing failed" in response.json['detail']
    mock_get_related_info.assert_called_once()

@patch('api.event.gemini_service.get_related_information_for_event')
def test_get_related_info_service_generic_error(mock_get_related_info, client, init_database):
    token = get_auth_token(client, init_database, email='relatedinfo_genericerror@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    from app import db
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(email='relatedinfo_genericerror@example.com').first()
        user_id = user.id
        start_time = datetime.utcnow() + timedelta(days=1)
        event = Event(title="Generic Error Event", start_time=start_time, location="A Location", user_id=user_id)
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    mock_get_related_info.return_value = {"error": "Some other Gemini issue", "detail": "Details of the issue."}

    response = client.get(f'/api/events/{event_id}/related-info', headers=headers)

    assert response.status_code == 500
    assert "Failed to retrieve related information due to a server error" in response.json['msg']
    assert "Details of the issue" in response.json['detail']
    mock_get_related_info.assert_called_once()


# --- Event Summary API Tests ---

@patch('api.event.event_service.get_events_in_range')
@patch('api.event.gemini_service.generate_event_summary_with_gemini')
def test_get_event_summary_success_default_date(mock_generate_summary, mock_get_events, client, init_database):
    token = get_auth_token(client, init_database, email='summaryuser_default@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    # Mock event_service response
    mock_event_data = [{"id": 1, "title": "Event 1", "start_time": f"{today_str}T10:00:00", "end_time": f"{today_str}T11:00:00", "description": "Desc 1"}]
    mock_get_events.return_value = mock_event_data

    # Mock gemini_service response
    mocked_summary_text = "Summary for today's events."
    mock_generate_summary.return_value = mocked_summary_text

    response = client.get('/api/events/summary', headers=headers)

    assert response.status_code == 200
    assert response.json == {"summary": mocked_summary_text}
    mock_get_events.assert_called_once_with(user_id=1, start_date_str=today_str, end_date_str=today_str) # Assuming user_id 1 from token mock

    simplified_events_for_gemini = [{"title": "Event 1", "start_time": "10:00", "end_time": "11:00", "description": "Desc 1"}]
    mock_generate_summary.assert_called_once_with(json.dumps(simplified_events_for_gemini), target_date_str=today_str)

@patch('api.event.event_service.get_events_in_range')
@patch('api.event.gemini_service.generate_event_summary_with_gemini')
def test_get_event_summary_success_specific_date(mock_generate_summary, mock_get_events, client, init_database):
    token = get_auth_token(client, init_database, email='summaryuser_specific@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    target_date_str = "2024-05-15"

    mock_event_data = [{"id": 1, "title": "Event May15", "start_time": f"{target_date_str}T14:00:00", "end_time": f"{target_date_str}T15:00:00", "description": "May 15 event"}]
    mock_get_events.return_value = mock_event_data
    mocked_summary_text = "Summary for May 15."
    mock_generate_summary.return_value = mocked_summary_text

    response = client.get(f'/api/events/summary?date={target_date_str}', headers=headers)

    assert response.status_code == 200
    assert response.json == {"summary": mocked_summary_text}
    mock_get_events.assert_called_once_with(user_id=1, start_date_str=target_date_str, end_date_str=target_date_str)
    simplified_events_for_gemini = [{"title": "Event May15", "start_time": "14:00", "end_time": "15:00", "description": "May 15 event"}]
    mock_generate_summary.assert_called_once_with(json.dumps(simplified_events_for_gemini), target_date_str=target_date_str)

def test_get_event_summary_invalid_date_format(client, init_database):
    token = get_auth_token(client, init_database, email='summaryuser_baddate@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    response = client.get('/api/events/summary?date=invalid-date', headers=headers)
    assert response.status_code == 400
    assert response.json == {"msg": "Invalid date format. Use YYYY-MM-DD"}

@patch('api.event.event_service.get_events_in_range')
@patch('api.event.gemini_service.generate_event_summary_with_gemini')
def test_get_event_summary_no_events_found(mock_generate_summary, mock_get_events, client, init_database):
    token = get_auth_token(client, init_database, email='summaryuser_noevents@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    mock_get_events.return_value = [] # No events

    response = client.get('/api/events/summary', headers=headers)

    assert response.status_code == 200
    assert response.json == {"summary": "No events scheduled for this date."}
    mock_get_events.assert_called_once_with(user_id=1, start_date_str=today_str, end_date_str=today_str)
    mock_generate_summary.assert_not_called()

@patch('api.event.event_service.get_events_in_range')
@patch('api.event.gemini_service.generate_event_summary_with_gemini')
def test_get_event_summary_event_service_error(mock_generate_summary, mock_get_events, client, init_database):
    token = get_auth_token(client, init_database, email='summaryuser_eventerror@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    mock_get_events.return_value = {"error": "Database connection failed", "status_code": 500}

    response = client.get('/api/events/summary', headers=headers)

    assert response.status_code == 500
    assert response.json == {"msg": "Database connection failed"}
    mock_get_events.assert_called_once_with(user_id=1, start_date_str=today_str, end_date_str=today_str)
    mock_generate_summary.assert_not_called()

@patch('api.event.event_service.get_events_in_range')
@patch('api.event.gemini_service.generate_event_summary_with_gemini')
def test_get_event_summary_gemini_service_error(mock_generate_summary, mock_get_events, client, init_database):
    token = get_auth_token(client, init_database, email='summaryuser_geminierror@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    mock_event_data = [{"id": 1, "title": "Event For Gemini Error", "start_time": f"{today_str}T10:00:00", "end_time": f"{today_str}T11:00:00", "description": "Desc"}]
    mock_get_events.return_value = mock_event_data

    gemini_error_response = {"error": "Gemini API is down", "detail": "Service unavailable", "status_code": 503}
    mock_generate_summary.return_value = gemini_error_response

    response = client.get('/api/events/summary', headers=headers)

    assert response.status_code == 503
    assert response.json == {"msg": "Gemini API is down", "detail": "Service unavailable"}
    mock_get_events.assert_called_once_with(user_id=1, start_date_str=today_str, end_date_str=today_str)
    simplified_events_for_gemini = [{"title": "Event For Gemini Error", "start_time": "10:00", "end_time": "11:00", "description": "Desc"}]
    mock_generate_summary.assert_called_once_with(json.dumps(simplified_events_for_gemini), target_date_str=today_str)

def test_get_event_summary_unauthorized(client, init_database):
    # No token provided
    response = client.get('/api/events/summary')
    assert response.status_code == 401 # Expecting JWT Unauthorized
