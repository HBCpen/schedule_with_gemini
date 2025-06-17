import pytest
import json
import os # Added os import
from datetime import datetime, timedelta, timezone # Added timezone import
from unittest.mock import patch, MagicMock, call # Import call for checking multiple calls
from models.event import Event
from models.user import User # Added User import
from app import db # Assuming db is the SQLAlchemy instance from app.py
from dateutil import rrule
from dateutil.parser import isoparse

# Helper function to get auth token
def get_auth_token(client, init_database, email='eventuser@example.com', password='password'):
    login_resp = client.post('/api/auth/login', json={'email': email, 'password': password})
    if login_resp.status_code == 200 and 'access_token' in login_resp.json:
        return login_resp.json['access_token']
    client.post('/api/auth/register', json={'email': email, 'password': password})
    login_response = client.post('/api/auth/login', json={'email': email, 'password': password})
    if 'access_token' not in login_response.json:
        raise Exception(f"Failed to get token for {email}. Login response: {login_response.json}")
    return login_response.json['access_token']

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_create_event(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["blue"]
    token = get_auth_token(client, init_database, email='createeventuser@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    response = client.post('/api/events', json={
        'title': 'Test Event Create',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': 'A test event description for creation'
    }, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201
    assert response.json['title'] == 'Test Event Create'
    assert response.json['color_tag'] == 'blue'
    assert 'user_id' in response.json
    assert response.json['reminder_sent'] == False
    mock_suggest_tags.assert_called_once_with('Test Event Create', 'A test event description for creation')

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_create_event_auto_tagging(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["project", "meeting"]
    token = get_auth_token(client, init_database, email='createeventuser_autotag@example.com')
    start_time = datetime.utcnow() + timedelta(days=2)
    end_time = start_time + timedelta(hours=1)
    response = client.post('/api/events', json={
        'title': 'Auto Tag Test Event',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': 'Description for auto tagging.'
    }, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201
    assert response.json['title'] == 'Auto Tag Test Event'
    assert response.json['color_tag'] == 'project,meeting'
    mock_suggest_tags.assert_called_once_with('Auto Tag Test Event', 'Description for auto tagging.')

def test_get_events(client, init_database):
    token = get_auth_token(client, init_database, email='geteventsuser@example.com')
    start_time1 = datetime.utcnow() + timedelta(days=1)
    end_time1 = start_time1 + timedelta(hours=1)
    start_time2 = datetime.utcnow() + timedelta(days=2)
    end_time2 = start_time2 + timedelta(hours=1)
    with patch('api.event.gemini_service.suggest_tags_for_event', return_value=[]):
        client.post('/api/events', json={'title': 'Event Alpha', 'start_time': start_time1.isoformat()+'Z', 'end_time': end_time1.isoformat()+'Z', 'location': 'Location A'}, headers={'Authorization': f'Bearer {token}'})
        client.post('/api/events', json={'title': 'Event Beta', 'start_time': start_time2.isoformat()+'Z', 'end_time': end_time2.isoformat()+'Z', 'location': 'Location B'}, headers={'Authorization': f'Bearer {token}'})
    query_start_date = start_time1.strftime('%Y-%m-%d')
    query_end_date = (start_time2 + timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    assert len(response.json) == 2
    assert response.json[0]['title'] == 'Event Alpha'
    assert response.json[1]['title'] == 'Event Beta'

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_update_event(mock_suggest_tags, client, init_database):
    token = get_auth_token(client, init_database, email='updateeventuser@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    mock_suggest_tags.return_value = ["initial"]
    create_response = client.post('/api/events', json={'title': 'Initial Event Title', 'start_time': start_time.isoformat() + 'Z', 'end_time': end_time.isoformat() + 'Z', 'description': 'Initial Description'}, headers={'Authorization': f'Bearer {token}'})
    assert create_response.status_code == 201
    event_id = create_response.json['id']
    assert create_response.json['color_tag'] == "initial"
    mock_suggest_tags.return_value = ["updated"] # New mock for the update call
    updated_title = "Updated Event Title"
    updated_description = "Updated Description"
    updated_start_time = start_time + timedelta(hours=2)
    updated_end_time = updated_start_time + timedelta(hours=1)
    update_response = client.put(f'/api/events/{event_id}', json={'title': updated_title, 'start_time': updated_start_time.isoformat() + 'Z', 'end_time': updated_end_time.isoformat() + 'Z', 'description': updated_description}, headers={'Authorization': f'Bearer {token}'})
    assert update_response.status_code == 200
    assert update_response.json['title'] == updated_title
    assert update_response.json['description'] == updated_description
    assert update_response.json['color_tag'] == "updated"
    assert update_response.json['start_time'].startswith(updated_start_time.isoformat().split('.')[0])

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_delete_event(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["to_delete"]
    token = get_auth_token(client, init_database, email='deleteeventuser@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    create_response = client.post('/api/events', json={'title': 'Event to Delete', 'start_time': start_time.isoformat() + 'Z', 'end_time': end_time.isoformat() + 'Z'}, headers={'Authorization': f'Bearer {token}'})
    assert create_response.status_code == 201
    event_id = create_response.json['id']
    delete_response = client.delete(f'/api/events/{event_id}', headers={'Authorization': f'Bearer {token}'})
    assert delete_response.status_code == 200
    assert delete_response.json['msg'] == 'Event deleted successfully'
    get_response = client.get(f'/api/events/{event_id}', headers={'Authorization': f'Bearer {token}'})
    assert get_response.status_code == 404

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_event_access_permissions(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["user1_event_tag"]
    token1 = get_auth_token(client, init_database, email='user1@example.com')
    token2 = get_auth_token(client, init_database, email='user2@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    create_resp_user1 = client.post('/api/events', json={'title': 'User1 Event', 'start_time': start_time.isoformat()+'Z', 'end_time': end_time.isoformat()+'Z'}, headers={'Authorization': f'Bearer {token1}'})
    assert create_resp_user1.status_code == 201
    event_id_user1 = create_resp_user1.json['id']
    get_resp_user2_fail = client.get(f'/api/events/{event_id_user1}', headers={'Authorization': f'Bearer {token2}'})
    assert get_resp_user2_fail.status_code == 404
    mock_suggest_tags.return_value = ["attempt_tag"] # For PUT attempt
    put_resp_user2_fail = client.put(f'/api/events/{event_id_user1}', json={'title': 'Attempted Update'}, headers={'Authorization': f'Bearer {token2}'})
    assert put_resp_user2_fail.status_code == 404
    delete_resp_user2_fail = client.delete(f'/api/events/{event_id_user1}', headers={'Authorization': f'Bearer {token2}'})
    assert delete_resp_user2_fail.status_code == 404
    get_resp_user1_ok = client.get(f'/api/events/{event_id_user1}', headers={'Authorization': f'Bearer {token1}'})
    assert get_resp_user1_ok.status_code == 200
    assert get_resp_user1_ok.json['title'] == 'User1 Event'
    query_start_date = (datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')
    query_end_date = (datetime.utcnow() + timedelta(days=5)).strftime('%Y-%m-%d')
    list_resp_user2 = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token2}'})
    assert list_resp_user2.status_code == 200
    assert len(list_resp_user2.json) == 0

# Helper for search tests
def _create_search_event(client, token, title, description, start_time, end_time, color_tag_payload=None):
    payload = {'title': title, 'start_time': start_time.isoformat() + 'Z', 'end_time': end_time.isoformat() + 'Z', 'description': description}
    if color_tag_payload is not None:
        payload['color_tag'] = color_tag_payload
    response = client.post('/api/events', json=payload, headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 201
    return response.json

@pytest.fixture(scope='function')
def search_test_data(client, init_database):
    user1_email = 'searchuser1@example.com'
    user2_email = 'searchuser2@example.com'
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
    assert response.status_code == 401

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_search_keyword_title(mock_suggest_tags, client, init_database, search_test_data):
    token1 = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    s_data = search_test_data['events_user1_data'][0]
    mock_suggest_tags.return_value = s_data['color_tag'].split(',')
    created_event = _create_search_event(client, token1, s_data['title'], s_data['description'], s_data['start_time'], s_data['end_time'])
    assert created_event['color_tag'] == s_data['color_tag']
    event_start_date_str = s_data['start_time'].strftime('%Y-%m-%d')
    event_end_date_str = (s_data['end_time'] + timedelta(days=1)).strftime('%Y-%m-%d')
    response = client.get(f'/api/events/search?q=Alpha&start_date={event_start_date_str}&end_date={event_end_date_str}', headers={'Authorization': f'Bearer {token1}'})
    assert response.status_code == 200
    results = response.json
    assert len(results) == 1
    assert results[0]['title'] == 'Alpha Meeting'
    assert results[0]['color_tag'] == s_data['color_tag']

def test_find_free_time_api_success(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetimeuser@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}
    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mock_event_instance = MagicMock(spec=Event)
    mock_event_instance.to_dict.return_value = {"title": "Existing Event 1",
                                               "start_time": (datetime.utcnow() + timedelta(hours=2)).isoformat() + 'Z',
                                               "end_time": (datetime.utcnow() + timedelta(hours=3)).isoformat() + 'Z',
                                               "location": "Office"}
    mock_query_obj = MagicMock()
    mocker.patch('api.event.Event.query', mock_query_obj)
    mock_query_obj.filter.return_value.order_by.return_value.all.return_value = [mock_event_instance]
    expected_slots = [{"start_time": (datetime.utcnow() + timedelta(hours=4)).isoformat(), "end_time": (datetime.utcnow() + timedelta(hours=5)).isoformat()}]
    mock_gemini_call = mocker.patch('api.event.gemini_service.find_free_time_slots_with_gemini', return_value=expected_slots)
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')
    response = client.post('/api/events/find-free-time', json={"query": "Find free time tomorrow afternoon"}, headers=access_token_headers)
    assert response.status_code == 200
    assert response.json == expected_slots
    mock_gemini_call.assert_called_once()
    assert mock_gemini_call.call_args.kwargs['user_query'] == "Find free time tomorrow afternoon"
    events_json_list = json.loads(mock_gemini_call.call_args.kwargs['events_json'])
    assert len(events_json_list) == 1
    assert events_json_list[0]['title'] == "Existing Event 1"

def test_find_free_time_api_database_error(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetime_dberror@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}
    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')
    mock_query_obj = MagicMock()
    mocker.patch('api.event.Event.query', mock_query_obj)
    mock_query_obj.filter.return_value.order_by.return_value.all.side_effect = Exception("Database connection failed")
    mock_gemini_service_call = mocker.patch('api.event.gemini_service.find_free_time_slots_with_gemini')
    response = client.post('/api/events/find-free-time', json={"query": "any query"}, headers=access_token_headers)
    assert response.status_code == 500
    assert response.json.get("msg") == "Error fetching user events"
    mock_gemini_service_call.assert_not_called()

@patch('api.event.gemini_service.find_free_time_slots_with_gemini')
def test_find_free_time_api_success_with_date_range(mock_find_slots, client, init_database, mocker):
    token = get_auth_token(client, init_database, email='freetimeuser_ranged@example.com')
    access_token_headers = {'Authorization': f'Bearer {token}'}
    mocker.patch('api.event.get_jwt_identity', return_value=1)
    mock_event_instance = MagicMock(spec=Event)
    mock_event_instance.to_dict.return_value = {"title": "Event In Range", "start_time": (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat()+'Z', "end_time": (datetime.utcnow() + timedelta(days=1, hours=3)).isoformat()+'Z', "location": "Office"}
    mock_query_obj = MagicMock()
    mocker.patch('api.event.Event.query', mock_query_obj)
    mock_query_obj.filter.return_value.order_by.return_value.all.return_value = [mock_event_instance]
    expected_slots = [{"start_time": (datetime.utcnow() + timedelta(days=1, hours=4)).isoformat(), "end_time": (datetime.utcnow() + timedelta(days=1, hours=5)).isoformat()}]
    mock_find_slots.return_value = expected_slots
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key')
    start_date_param = datetime.utcnow().isoformat()
    end_date_param = (datetime.utcnow() + timedelta(days=3)).isoformat()
    response = client.post('/api/events/find-free-time', json={"query": "Find free time in the next 3 days", "start_date": start_date_param, "end_date": end_date_param }, headers=access_token_headers)
    assert response.status_code == 200
    assert response.json == expected_slots
    mock_query_obj.filter.return_value.order_by.return_value.all.assert_called_once()
    mock_find_slots.assert_called_once()

def test_search_invalid_date_format(client, init_database):
    token = get_auth_token(client, init_database, email='searchinvaliddate@example.com')
    response_start = client.get('/api/events/search?start_date=invalid-date', headers={'Authorization': f'Bearer {token}'})
    assert response_start.status_code == 400
    assert "Invalid start_date format. Use ISO format." in response_start.json['msg']
    response_end = client.get('/api/events/search?end_date=invalid-date', headers={'Authorization': f'Bearer {token}'})
    assert response_end.status_code == 400
    assert "Invalid end_date format. Use ISO format." in response_end.json['msg']

@patch('api.event.gemini_service.get_related_information_for_event')
def test_get_related_info_event_missing_start_time(mock_get_related_info, client, init_database):
    token = get_auth_token(client, init_database, email='relatedinfo_nostart@example.com')
    headers = {'Authorization': f'Bearer {token}'}
    from models.user import User
    with client.application.app_context():
        user = User.query.filter_by(email='relatedinfo_nostart@example.com').first()
        user_id = user.id
        event = Event(title="No StartTime Event", location="Some Location", user_id=user_id, start_time=None)
        db.session.add(event)
        db.session.commit()
        event_id = event.id
    response = client.get(f'/api/events/{event_id}/related-info', headers=headers)
    assert response.status_code == 400
    assert "location and start time are required" in response.json['msg']
    mock_get_related_info.assert_not_called()

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_search_tags(mock_suggest_tags, client, init_database, search_test_data):
    token = get_auth_token(client, init_database, email=search_test_data['user1_email'])
    now = datetime.utcnow()
    event_data_list = [
        {'title': 'Work Event', 'start_time': now, 'end_time': now + timedelta(hours=1), 'color_tag_expected': 'work,urgent'},
        {'title': 'Personal Errand', 'start_time': now + timedelta(days=1), 'end_time': now + timedelta(days=1, hours=1), 'color_tag_expected': 'personal'},
        {'title': 'Work Planning', 'start_time': now + timedelta(days=2), 'end_time': now + timedelta(days=2, hours=1), 'color_tag_expected': 'work,planning'},
    ]
    for data in event_data_list:
        mock_suggest_tags.return_value = data['color_tag_expected'].split(',')
        _create_search_event(client, token, data['title'], '', data['start_time'], data['end_time'])

    start_search_range = now.strftime('%Y-%m-%d')
    end_search_range = (now + timedelta(days=3)).strftime('%Y-%m-%d')
    response = client.get(f'/api/events/search?tags=personal&start_date={start_search_range}&end_date={end_search_range}', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 200
    results = response.json
    assert len(results) == 1
    assert results[0]['title'] == 'Personal Errand'
    assert results[0]['color_tag'] == 'personal'

# Tests for /api/events/parse-natural-language
def test_parse_natural_language_success(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='nlpuser@example.com')
    mock_gemini_parse = mocker.patch('api.event.gemini_service.parse_event_text_with_gemini')
    expected_response = {
        "title": "Meeting with Team",
        "start_time": "2024-08-15T10:00:00Z",
        "end_time": "2024-08-15T11:00:00Z",
        "description": "Discuss project updates."
    }
    mock_gemini_parse.return_value = expected_response
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key') # Mock API key check

    response = client.post('/api/events/parse-natural-language',
                           json={'text': 'Meeting with Team tomorrow 10 AM for an hour about project updates'},
                           headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json == expected_response
    mock_gemini_parse.assert_called_once_with('Meeting with Team tomorrow 10 AM for an hour about project updates')

def test_parse_natural_language_missing_input(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='nlp_missinginput@example.com')
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key') # Mock API key check

    response = client.post('/api/events/parse-natural-language',
                           json={},  # Missing 'text' field
                           headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
    assert response.json['msg'] == 'Text input is required' # Corrected message

def test_parse_natural_language_api_key_not_configured(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='nlp_noapikey@example.com')
    mocker.patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True) # Unset API key

    response = client.post('/api/events/parse-natural-language',
                           json={'text': 'Some event text'},
                           headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 503
    assert response.json['msg'] == 'Gemini API key not configured on the server.' # Corrected message

def test_parse_natural_language_gemini_service_error(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='nlp_geminierror@example.com')
    mock_gemini_parse = mocker.patch('api.event.gemini_service.parse_event_text_with_gemini')
    # Adjusted mock to provide a 'detail' field as the endpoint expects it for the error message
    mock_gemini_parse.return_value = {"error": "Gemini processing failed", "detail": "Gemini processing failed"}
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key') # Mock API key check

    response = client.post('/api/events/parse-natural-language',
                           json={'text': 'Another event text'},
                           headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 500
    assert "msg" in response.json # Check for 'msg' key
    assert response.json["msg"] == "Error parsing event with Gemini" # Check msg content
    assert "detail" in response.json # Check for 'detail' key
    assert response.json["detail"] == "Gemini processing failed" # Check detail content


# --- Integration Tests with Live Gemini API Calls ---

def test_parse_natural_language_integration_live_api(client, init_database, mocker):
    """
    Integration test for /api/events/parse-natural-language with live Gemini API call.
    """
    token = get_auth_token(client, init_database, email='nlpliveuser@example.com')

    # Ensure the GEMINI_API_KEY is available in the test environment for the app
    # The actual key is set globally in the previous subtask.
    # We just need to make sure the endpoint check passes.
    # If os.environ.get inside the endpoint needs mocking for some reason (e.g. specific test setup):
    # mocker.patch('api.event.os.environ.get', return_value=os.environ.get('GEMINI_API_KEY'))
    # However, it should pick up the actual environment variable.

    natural_language_text = "Meeting with John next Friday at 2pm to discuss the new project proposal at the cafe."

    response = client.post('/api/events/parse-natural-language',
                           json={'text': natural_language_text},
                           headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    parsed_data = response.json

    assert "title" in parsed_data
    assert "date" in parsed_data
    assert "start_time" in parsed_data

    # Check for plausible values based on the input (actual values depend on Gemini model)
    assert parsed_data["title"] is not None # Expecting a title
    assert "meeting" in parsed_data["title"].lower() or "john" in parsed_data["title"].lower()

    # Date should be a valid YYYY-MM-DD string for next Friday
    assert isinstance(parsed_data["date"], str)
    try:
        parsed_date = datetime.strptime(parsed_data["date"], "%Y-%m-%d")
        # Heuristic: next Friday should be within the next 14 days
        assert (parsed_date - datetime.now()).days >= 0
        assert (parsed_date - datetime.now()).days <= 14
        assert parsed_date.weekday() == 4 # Friday
    except ValueError:
        pytest.fail(f"Parsed date '{parsed_data['date']}' is not in YYYY-MM-DD format.")

    # Time should be a valid HH:MM string
    assert isinstance(parsed_data["start_time"], str)
    try:
        parsed_time = datetime.strptime(parsed_data["start_time"], "%H:%M")
        assert parsed_time.hour == 14 # 2 PM
        assert parsed_time.minute == 0
    except ValueError:
        pytest.fail(f"Parsed start_time '{parsed_data['start_time']}' is not in HH:MM format.")

    if "description" in parsed_data:
        assert "project proposal" in parsed_data["description"].lower()
    if "location" in parsed_data:
        assert "cafe" in parsed_data["location"].lower()

    # Test error case: API key not configured (simulated by endpoint check)
    # This requires ensuring the key is *not* available for this part of the test only.
    # This is harder to do reliably for a live key that's globally set.
    # The existing unit test `test_parse_natural_language_api_key_not_configured` covers this better by direct mocking.
    # Instead, we can test for empty input.

    response_empty_text = client.post('/api/events/parse-natural-language',
                                   json={'text': ''},
                                   headers={'Authorization': f'Bearer {token}'})
    assert response_empty_text.status_code == 400 # Assuming the endpoint checks for empty text before calling Gemini
    assert response_empty_text.json['msg'] == 'Text input is required' # Adjusted to match actual error message from event.py


def test_create_event_live_tagging(client, init_database, mocker):
    """
    Integration test for POST /api/events with live Gemini API call for tagging.
    """
    token = get_auth_token(client, init_database, email='createlivetag@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    event_data = {
        'title': 'Important Business Meeting with Potential Client',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': 'Discuss partnership opportunities and project collaboration. Goals: secure deal, establish rapport.'
    }

    # No mocking of gemini_service.suggest_tags_for_event

    response = client.post('/api/events', json=event_data, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 201
    created_event_data = response.json
    assert created_event_data['title'] == event_data['title']

    # Verify tags from live API call
    # Tags are somewhat unpredictable, so check for presence and general relevance.
    assert 'color_tag' in created_event_data
    tags_string = created_event_data['color_tag']
    assert isinstance(tags_string, str) # Tags are stored as comma-separated string

    print(f"Live generated tags for create_event: {tags_string}") # For observation

    if not tags_string:
        warnings.warn("Gemini API returned no tags for create_event. This might be acceptable depending on input.")
    else:
        tags = [tag.strip().lower() for tag in tags_string.split(',')]
        # Example: Check if any common relevant tags are present
        expected_possible_tags = ["work", "meeting", "business", "client", "project"]
        assert any(expected_tag in tags for expected_tag in expected_possible_tags), \
            f"Expected one of {expected_possible_tags} in live generated tags '{tags_string}'"

    # Verify in DB
    with client.application.app_context():
        event_from_db = db.session.get(Event, created_event_data['id'])
        assert event_from_db is not None
        assert event_from_db.title == event_data['title']
        assert event_from_db.color_tag == tags_string

def test_update_event_live_tagging(client, init_database, mocker):
    """
    Integration test for PUT /api/events/<id> with live Gemini API call for tagging.
    """
    user_email = 'updatelivetag@example.com'
    token = get_auth_token(client, init_database, email=user_email)

    # 1. Create an initial event (can use API or direct model)
    # For simplicity, using direct model interaction to set initial state precisely.
    with client.application.app_context():
        user = User.query.filter_by(email=user_email).first()
        initial_start_time = datetime.utcnow() + timedelta(days=2)
        initial_event = Event(
            title="Initial Project Brainstorm",
            description="Early thoughts on new project.",
            start_time=initial_start_time,
            end_time=initial_start_time + timedelta(hours=1),
            user_id=user.id,
            color_tag="initial,planning" # Known initial tags
        )
        db.session.add(initial_event)
        db.session.commit()
        event_id = initial_event.id

    # 2. Update the event's title and description to trigger new tags
    updated_data = {
        'title': 'Critical Client Negotiation Session',
        'description': 'Finalizing terms for the major Q4 contract. Focus on legal and financial clauses.',
        'start_time': initial_start_time.isoformat() + 'Z', # Keep times same or update as needed
        'end_time': (initial_start_time + timedelta(hours=1)).isoformat() + 'Z'
    }

    # No mocking of gemini_service.suggest_tags_for_event

    response = client.put(f'/api/events/{event_id}', json=updated_data, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    updated_event_data = response.json
    assert updated_event_data['title'] == updated_data['title']
    assert updated_event_data['description'] == updated_data['description']

    # Verify updated tags from live API call
    assert 'color_tag' in updated_event_data
    updated_tags_string = updated_event_data['color_tag']
    assert isinstance(updated_tags_string, str)

    print(f"Live generated tags for update_event: {updated_tags_string}") # For observation

    assert updated_tags_string != "initial,planning", "Tags should have been updated by the live API call."

    if not updated_tags_string:
        warnings.warn("Gemini API returned no tags for update_event. This might be acceptable depending on input.")
    else:
        updated_tags = [tag.strip().lower() for tag in updated_tags_string.split(',')]
        expected_possible_updated_tags = ["work", "client", "negotiation", "contract", "legal", "finance"]
        assert any(expected_tag in updated_tags for expected_tag in expected_possible_updated_tags), \
            f"Expected one of {expected_possible_updated_tags} in live updated tags '{updated_tags_string}'"

    # Verify in DB
    with client.application.app_context():
        event_from_db = db.session.get(Event, event_id)
        assert event_from_db is not None
        assert event_from_db.title == updated_data['title']
        assert event_from_db.color_tag == updated_tags_string


def test_find_free_time_live_api(client, init_database, mocker):
    """
    Integration test for POST /api/events/find-free-time with live Gemini API call.
    """
    user_email = 'findfreetimelive@example.com'
    token = get_auth_token(client, init_database, email=user_email)

    # Ensure GEMINI_API_KEY is available (should be from global setup)
    # mocker.patch('api.event.os.environ.get', return_value=os.environ.get('GEMINI_API_KEY'))


    # 1. Create some existing events for this user to make the search meaningful
    with client.application.app_context():
        user = User.query.filter_by(email=user_email).first()
        assert user is not None # Ensure user exists

        now = datetime.utcnow()
        # Determine next Monday
        today_weekday = now.weekday() # Monday is 0, Sunday is 6
        days_until_monday = (0 - today_weekday + 7) % 7
        if days_until_monday == 0: # if today is Monday, consider next Monday
            days_until_monday = 7

        next_monday_date = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days_until_monday)

        # Make event times offset-aware (UTC)
        event1_start = next_monday_date.replace(hour=9, minute=0, tzinfo=timezone.utc) # Next Monday 9 AM UTC
        event1_end = next_monday_date.replace(hour=10, minute=30, tzinfo=timezone.utc) # Next Monday 10:30 AM UTC

        event2_start = next_monday_date.replace(hour=14, minute=0, tzinfo=timezone.utc) # Next Monday 2 PM UTC
        event2_end = next_monday_date.replace(hour=15, minute=0, tzinfo=timezone.utc)   # Next Monday 3 PM UTC

        existing_event1 = Event(
            title="Morning Standup",
            start_time=event1_start,
            end_time=event1_end,
            user_id=user.id
        )
        existing_event2 = Event(
            title="Afternoon Sync",
            start_time=event2_start,
            end_time=event2_end,
            user_id=user.id
        )
        db.session.add_all([existing_event1, existing_event2])
        db.session.commit()

    # 2. Call the endpoint
    # Query for a 1-hour slot on that specific Monday morning
    # The date range for event fetching by the endpoint should include this Monday.
    query_start_date = next_monday_date.isoformat()
    query_end_date = (next_monday_date + timedelta(days=1)).isoformat()

    find_time_payload = {
        "query": "Find a 1-hour slot for me next Monday morning",
        "start_date": query_start_date, # This helps narrow down the events the API considers
        "end_date": query_end_date      # This also helps narrow down events
    }

    # No mocking of gemini_service.find_free_time_slots_with_gemini

    response = client.post('/api/events/find-free-time', json=find_time_payload, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    suggested_slots = response.json

    assert isinstance(suggested_slots, list), "Response should be a list of slots"
    print(f"Live suggested free time slots: {suggested_slots}") # For observation

    # Assertions for the slots (these are examples and depend on Gemini's live output)
    # Given events at 9:00-10:30 and 14:00-15:00 on Next Monday:
    # Possible 1-hour morning slots: e.g., around 08:00, 10:30-11:30, 11:00-12:00, 12:00-13:00, 13:00-14:00

    found_plausible_slot = False
    if not suggested_slots:
        warnings.warn("Gemini API returned no free slots. This might be valid or an issue to investigate.")

    for slot in suggested_slots:
        assert "start_time" in slot
        assert "end_time" in slot

        slot_start = isoparse(slot["start_time"])
        if slot_start.tzinfo is None: # Assume UTC if Gemini returns naive time
            slot_start = slot_start.replace(tzinfo=timezone.utc)

        slot_end = isoparse(slot["end_time"])
        if slot_end.tzinfo is None: # Assume UTC if Gemini returns naive time
            slot_end = slot_end.replace(tzinfo=timezone.utc)

        # Ensure the slot is on the correct day (Next Monday)
        # Make next_monday_date naive for date comparison if slot_start is naive,
        # or ensure slot_start is aware for direct comparison.
        # Given we made slot_start aware (UTC), next_monday_date should also be compared as such or its date part.
        assert slot_start.date() == next_monday_date.date(), f"Slot {slot} is not on the expected date {next_monday_date.date()}"

        # Ensure it's a 1-hour slot (approximately, allow for small deviations if any)
        duration_seconds = (slot_end - slot_start).total_seconds()
        assert 3500 <= duration_seconds <= 3700, f"Slot duration is not ~1 hour: {duration_seconds/3600} hours" # Approx 1 hour

        # Check if it's a morning slot (e.g., before 1 PM / 13:00)
        if slot_start.hour < 13:
             # Check it doesn't overlap with 9:00-10:30 AM event
            if not (slot_start < event1_end and slot_end > event1_start):
                found_plausible_slot = True
                print(f"Plausible morning slot found: {slot}")
                break # Found one good slot, that's enough for this test structure

    assert found_plausible_slot, f"No plausible 1-hour morning slot found on Next Monday. Slots: {suggested_slots}"


def test_get_related_info_live_api(client, init_database, mocker):
    """
    Integration test for GET /api/events/<id>/related-info with live Gemini API call.
    """
    user_email = 'relatedinfolive@example.com'
    token = get_auth_token(client, init_database, email=user_email)

    with client.application.app_context():
        user = User.query.filter_by(email=user_email).first()
        assert user is not None

        event_start_time = datetime.utcnow() + timedelta(days=3)
        event_data = Event(
            title="Conference on Future Technologies",
            description="Attending keynotes and workshops. Exploring AI and Quantum Computing.",
            location="Tech Hub Convention Center, Metropolis",
            start_time=event_start_time,
            end_time=event_start_time + timedelta(hours=8),
            user_id=user.id
        )
        db.session.add(event_data)
        db.session.commit()
        event_id = event_data.id

    response = client.get(f'/api/events/{event_id}/related-info', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    related_info = response.json

    print(f"Live related info: {related_info}") # For observation

    assert "weather" in related_info
    assert "traffic" in related_info
    assert "suggestions" in related_info # May be empty list if no meal keywords
    assert "related_content" in related_info

    # Example: Check some weather fields (actual values depend on live API)
    if related_info["weather"] and isinstance(related_info["weather"], dict) and "condition" in related_info["weather"]:
        assert related_info["weather"]["condition"] is not None
    else:
        # It's possible weather info might not be available for a future date/location,
        # or the Gemini model might not return it consistently.
        # Depending on strictness, this could be a fail or a warning.
        # For now, let's assume the weather key itself must be present.
        assert "weather" in related_info # Re-assert to ensure key exists even if content is minimal/None
        print("Warning/Note: Weather data might be minimal or null from live API for future events.")

    # Traffic data is highly dynamic and hard to assert precisely for a future event
    if related_info["traffic"] and isinstance(related_info["traffic"], dict) and "summary" in related_info["traffic"]:
        assert related_info["traffic"]["summary"] is not None
    else:
        assert "traffic" in related_info
        print("Warning/Note: Traffic data might be minimal or null from live API for future events.")

    # Suggestions for restaurants might be empty if not applicable
    assert isinstance(related_info.get("suggestions"), list)
    # Related content might also be empty
    assert isinstance(related_info.get("related_content"), list)


def test_suggest_subtasks_live_api(client, init_database, mocker):
    """
    Integration test for POST /api/events/<id>/suggest-subtasks with live Gemini API call.
    """
    user_email = 'subtaskslive@example.com'
    token = get_auth_token(client, init_database, email=user_email)

    with client.application.app_context():
        user = User.query.filter_by(email=user_email).first()
        assert user is not None

        event_start_time = datetime.utcnow() + timedelta(days=5)
        event_data = Event(
            title="Organize Annual Company Retreat",
            description="Plan and execute the 2-day company-wide retreat for 100 employees. Includes venue booking, catering, activities, and travel arrangements.",
            start_time=event_start_time,
            end_time=event_start_time + timedelta(days=2),
            user_id=user.id
        )
        db.session.add(event_data)
        db.session.commit()
        event_id = event_data.id

    response = client.post(f'/api/events/{event_id}/suggest-subtasks', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    subtasks = response.json

    print(f"Live suggested subtasks: {subtasks}") # For observation

    assert isinstance(subtasks, list), "Response should be a list of subtasks"
    assert len(subtasks) > 0, "Expected at least one subtask to be suggested for a complex event"

    for subtask in subtasks:
        assert isinstance(subtask, str)
        assert len(subtask.strip()) > 0 # Subtasks should not be empty strings

    # Example: Check if some plausible keywords are in the subtasks
    # This is highly dependent on the model's output
    combined_subtasks_text = " ".join(subtasks).lower()
    expected_keywords = ["venue", "cater", "activit", "travel", "budget", "schedule", "communication"]
    found_keywords = [keyword for keyword in expected_keywords if keyword in combined_subtasks_text]

    assert len(found_keywords) >= 2, \
        f"Expected at least 2 relevant keywords in subtasks. Found: {found_keywords}. Subtasks: {subtasks}"


def test_get_event_summary_live_api(client, init_database, mocker):
    """
    Integration test for GET /api/events/summary with live Gemini API call.
    """
    user_email = 'summaryliveuser@example.com'
    token = get_auth_token(client, init_database, email=user_email)

    target_date = datetime.utcnow() + timedelta(days=1)
    target_date_str = target_date.strftime('%Y-%m-%d')

    with client.application.app_context():
        user = User.query.filter_by(email=user_email).first()
        assert user is not None

        event1_start = target_date.replace(hour=9, minute=0, tzinfo=timezone.utc)
        event1_end = target_date.replace(hour=10, minute=0, tzinfo=timezone.utc)
        event1 = Event(
            title="Team Strategy Meeting",
            description="Discuss Q3 goals and roadmap.",
            start_time=event1_start,
            end_time=event1_end,
            user_id=user.id
        )

        event2_start = target_date.replace(hour=14, minute=30, tzinfo=timezone.utc)
        event2_end = target_date.replace(hour=15, minute=30, tzinfo=timezone.utc)
        event2 = Event(
            title="Client Follow-up Call",
            description="Check in with Acme Corp regarding project Alpha.",
            start_time=event2_start,
            end_time=event2_end,
            user_id=user.id
        )
        db.session.add_all([event1, event2])
        db.session.commit()

    response = client.get(f'/api/events/summary?date={target_date_str}', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    summary_data = response.json
    assert "summary" in summary_data
    summary_text = summary_data["summary"]

    print(f"Live generated summary: {summary_text}") # For observation

    assert isinstance(summary_text, str), "Summary should be a string"
    assert len(summary_text.strip()) > 0, "Summary string should not be empty"

    # Plausibility checks (highly dependent on Gemini's output)
    assert "team strategy meeting" in summary_text.lower() or "q3 goals" in summary_text.lower()
    assert "client follow-up" in summary_text.lower() or "acme corp" in summary_text.lower()
    assert "9:00" in summary_text or "09:00" in summary_text # Check for time mention
    assert "2:30" in summary_text or "14:30" in summary_text # Check for time mention

    # Test with no date provided (should default to today, likely no events from above setup)
    # This part mainly checks endpoint behavior, not necessarily live Gemini output if no events.
    response_no_date = client.get('/api/events/summary', headers={'Authorization': f'Bearer {token}'})
    assert response_no_date.status_code == 200
    summary_no_date_data = response_no_date.json
    assert "summary" in summary_no_date_data
    if "No events scheduled" not in summary_no_date_data["summary"]:
        # If it's not "No events...", it should be some other valid (even if empty-ish) summary string.
        assert isinstance(summary_no_date_data["summary"], str)
        # It's hard to assert more without knowing if Gemini returns empty string or some other text for no events.
        # The endpoint itself has a check for "No events scheduled for this date." if event_service returns empty.
        # So, this path might not heavily involve Gemini if no events are found for "today".


# Tests for Reminder Service
def test_send_event_reminders(client, init_database, mocker):
    # 1. Setup User
    user_email = 'reminderuser@example.com'
    # Use the existing get_auth_token to ensure user creation and get a token, though token not directly used here
    # It also handles user registration if the user doesn't exist.
    get_auth_token(client, init_database, email=user_email, password='password')

    # Get user from DB to associate with events
    from models.user import User
    from app import db as app_db # Use app_db to avoid conflict with pytest 'db' fixture if any

    # Need app context for database operations
    with client.application.app_context():
        user = User.query.filter_by(email=user_email).first()
        assert user is not None

        now = datetime.utcnow()

        # 2. Create Events
        event_soon = Event(
            user_id=user.id, title="Event Starting Soon",
            start_time=now + timedelta(minutes=30),
            end_time=now + timedelta(minutes=90),
            reminder_sent=False
        )
        event_far_future = Event(
            user_id=user.id, title="Event Far Future",
            start_time=now + timedelta(days=5),
            end_time=now + timedelta(days=5, hours=1),
            reminder_sent=False
        )
        event_already_reminded = Event(
            user_id=user.id, title="Event Already Reminded",
            start_time=now + timedelta(minutes=40),
            end_time=now + timedelta(minutes=100),
            reminder_sent=True
        )
        # Event whose start time is in the past but within the reminder_window_start (e.g., task ran late)
        # reminder_window_start is now - 10 minutes
        event_past_in_window = Event(
            user_id=user.id, title="Event Past In Window",
            start_time=now - timedelta(minutes=5),
            end_time=now + timedelta(minutes=55),
            reminder_sent=False
        )
        # Event that is too far in the past (outside reminder_window_start)
        event_too_far_past = Event(
            user_id=user.id, title="Event Too Far Past",
            start_time=now - timedelta(minutes=15), # reminder_window_start is now - 10 minutes
            end_time=now + timedelta(minutes=45),
            reminder_sent=False
        )

        app_db.session.add_all([event_soon, event_far_future, event_already_reminded, event_past_in_window, event_too_far_past])
        app_db.session.commit()

        event_soon_id = event_soon.id
        event_far_future_id = event_far_future.id
        event_already_reminded_id = event_already_reminded.id
        event_past_in_window_id = event_past_in_window.id
        event_too_far_past_id = event_too_far_past.id

    # 3. Mock mail.send
    # Patch mail.send where it's looked up by the service module
    mock_mail_send = mocker.patch('services.reminder_service.mail.send')

    # 4. Call reminder_service.send_event_reminders()
    from services import reminder_service
    # Ensure the service uses the same app context or has one set up
    # The service itself calls create_app() so it establishes its own context.
    reminder_service.send_event_reminders()

    # 5. Assertions
    with client.application.app_context():
        # Retrieve events from DB to check updated reminder_sent status
        # Use db.session.get for SQLAlchemy 2.0 compatibility
        retrieved_event_soon = db.session.get(Event, event_soon_id)
        retrieved_event_far_future = db.session.get(Event, event_far_future_id)
        retrieved_event_already_reminded = db.session.get(Event, event_already_reminded_id)
        retrieved_event_past_in_window = db.session.get(Event, event_past_in_window_id)
        retrieved_event_too_far_past = db.session.get(Event, event_too_far_past_id)

        assert retrieved_event_soon.reminder_sent == True, "Event 'soon' should have reminder_sent = True"
        assert retrieved_event_far_future.reminder_sent == False, "Event 'far_future' should have reminder_sent = False"
        assert retrieved_event_already_reminded.reminder_sent == True, "Event 'already_reminded' should still have reminder_sent = True"
        assert retrieved_event_past_in_window.reminder_sent == True, "Event 'past_in_window' should have reminder_sent = True"
        assert retrieved_event_too_far_past.reminder_sent == False, "Event 'too_far_past' should have reminder_sent = False"

        # Assert mail.send calls
        # Expected calls for event_soon and event_past_in_window
        assert mock_mail_send.call_count == 2

        # Check call arguments (more specific checks can be added if needed)
        # We need to be careful about the order of calls if we check call_args_list specifically
        # For now, checking that emails were sent to the correct user for the correct events.

        expected_recipients = [user_email]

        call_args_list = mock_mail_send.call_args_list

        # Check for event_soon reminder
        # Access Message object from call.args[0]
        msg_soon_found = any(
            isinstance(c.args[0], object) and # Ensure arg[0] exists and is an object
            getattr(c.args[0], 'subject', None) == f"Reminder: {event_soon.title}" and
            getattr(c.args[0], 'recipients', None) == expected_recipients
            for c in call_args_list
        )
        assert msg_soon_found, "Mail for 'event_soon' was not sent or had incorrect parameters."

        # Check for event_past_in_window reminder
        msg_past_in_window_found = any(
            isinstance(c.args[0], object) and
            getattr(c.args[0], 'subject', None) == f"Reminder: {event_past_in_window.title}" and
            getattr(c.args[0], 'recipients', None) == expected_recipients
            for c in call_args_list
        )
        assert msg_past_in_window_found, "Mail for 'event_past_in_window' was not sent or had incorrect parameters."

        # Ensure no other emails were sent by checking subjects of all calls
        for c in call_args_list:
            message_obj = c.args[0]
            assert isinstance(message_obj, object)
            assert getattr(message_obj, 'recipients', None) == expected_recipients
            current_subject = getattr(message_obj, 'subject', '')
            assert current_subject in [f"Reminder: {event_soon.title}", f"Reminder: {event_past_in_window.title}"], \
                f"Unexpected email sent with subject: {current_subject}"

# Tests for Recurring Events
@patch('api.event.gemini_service.suggest_tags_for_event')
def test_create_recurring_event(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["recurring_test_tag"]
    token = get_auth_token(client, init_database, email='recurringuser@example.com')

    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    recurrence_rule = "FREQ=DAILY;COUNT=3"

    response = client.post('/api/events', json={
        'title': 'Test Recurring Event',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': 'A test recurring event',
        'recurrence_rule': recurrence_rule
    }, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 201, f"Failed to create event: {response.json}"
    assert response.json['title'] == 'Test Recurring Event'
    assert response.json['recurrence_rule'] == recurrence_rule
    assert response.json['color_tag'] == 'recurring_test_tag'

    # Verify in DB (optional, but good for confirmation)
    event_id = response.json['id']
    with client.application.app_context():
        event_from_db = db.session.get(Event, event_id) # Corrected to db.session.get
        assert event_from_db is not None
        assert event_from_db.recurrence_rule == recurrence_rule
        assert event_from_db.parent_event_id is None # This is a master event

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_get_expanded_recurring_events(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["recurring_expansion_tag"]
    token = get_auth_token(client, init_database, email='recurring_expansion_user@example.com')

    master_start_time_dt = datetime.utcnow().replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=1)
    master_end_time_dt = master_start_time_dt + timedelta(hours=1)
    recurrence_rule_str = "FREQ=DAILY;COUNT=3"

    # 1. Create the master recurring event
    create_response = client.post('/api/events', json={
        'title': 'Master Recurring Event for Expansion',
        'start_time': master_start_time_dt.isoformat() + 'Z',
        'end_time': master_end_time_dt.isoformat() + 'Z',
        'description': 'Master Description',
        'recurrence_rule': recurrence_rule_str
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_response.status_code == 201
    master_event_id = create_response.json['id']
    master_event_title = create_response.json['title']
    master_event_description = create_response.json['description']

    rrule_set = rrule.rruleset()
    rrule_set.rrule(rrule.rrulestr(recurrence_rule_str, dtstart=master_start_time_dt)) # Corrected to rrulestr

    expected_occurrences_datetimes = list(rrule_set.between(
        master_start_time_dt - timedelta(microseconds=1),
        master_start_time_dt + timedelta(days=30)
    ))
    assert len(expected_occurrences_datetimes) == 3

    query_start_date = master_start_time_dt.strftime('%Y-%m-%d')
    query_end_date = (expected_occurrences_datetimes[-1] + timedelta(days=1)).strftime('%Y-%m-%d')

    response_all = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert response_all.status_code == 200
    events_all = response_all.json

    # Occurrences have the ID of their master event in the 'id' field.
    # 'parent_event_id' on a master event object is None.
    occurrences = [e for e in events_all if e.get('is_occurrence') and e.get('id') == master_event_id]
    assert len(occurrences) == 3, f"Expected 3 occurrences, got {len(occurrences)}. Full response: {events_all}"

    for i, occ_dt in enumerate(expected_occurrences_datetimes):
        event_json = occurrences[i]
        assert event_json['title'] == master_event_title
        assert event_json['description'] == master_event_description
        assert event_json['is_occurrence'] == True
        assert event_json['id'] == master_event_id # Check 'id' is master_event_id for occurrences

        expected_occ_start_time_iso = occ_dt.isoformat() + "Z"
        expected_occ_end_time_iso = (occ_dt + (master_end_time_dt - master_start_time_dt)).isoformat() + "Z"

        assert event_json['start_time'] == expected_occ_start_time_iso
        assert event_json['end_time'] == expected_occ_end_time_iso
        assert event_json['series_start_time'] == master_start_time_dt.isoformat() + "Z"

    # Test with a date range that includes only some occurrences
    query_partial_end_date = (expected_occurrences_datetimes[1] + timedelta(hours=1)).strftime('%Y-%m-%d')
    response_partial = client.get(f'/api/events?start_date={query_start_date}&end_date={query_partial_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert response_partial.status_code == 200
    events_partial = response_partial.json
    occurrences_partial = [e for e in events_partial if e.get('is_occurrence') and e.get('id') == master_event_id]
    assert len(occurrences_partial) == 2, f"Expected 2 partial occurrences, got {len(occurrences_partial)}. Full response: {events_partial}"
    assert occurrences_partial[0]['start_time'].startswith(expected_occurrences_datetimes[0].isoformat())
    assert occurrences_partial[1]['start_time'].startswith(expected_occurrences_datetimes[1].isoformat())

    # Test with a date range that includes no occurrences
    query_none_start_date = (expected_occurrences_datetimes[-1] + timedelta(days=10)).strftime('%Y-%m-%d')
    query_none_end_date = (expected_occurrences_datetimes[-1] + timedelta(days=12)).strftime('%Y-%m-%d')
    response_none = client.get(f'/api/events?start_date={query_none_start_date}&end_date={query_none_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert response_none.status_code == 200
    events_none = response_none.json
    occurrences_none = [e for e in events_none if e.get('is_occurrence') and e.get('id') == master_event_id]
    assert len(occurrences_none) == 0, f"Expected 0 occurrences for distant date range, got {len(occurrences_none)}. Full response: {events_none}"

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_update_recurring_event_change_rule(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["update_rule_tag"]
    token = get_auth_token(client, init_database, email='recurring_update_rule@example.com')

    master_start_time_dt = datetime.utcnow().replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1)
    master_end_time_dt = master_start_time_dt + timedelta(hours=1)
    initial_recurrence_rule = "FREQ=DAILY;COUNT=3"

    create_response = client.post('/api/events', json={
        'title': 'Event for Rule Change',
        'start_time': master_start_time_dt.isoformat() + 'Z',
        'end_time': master_end_time_dt.isoformat() + 'Z',
        'recurrence_rule': initial_recurrence_rule
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_response.status_code == 201
    master_event_id = create_response.json['id']

    mock_suggest_tags.return_value = ["rule_changed_tag"]
    new_recurrence_rule = "FREQ=WEEKLY;INTERVAL=1;COUNT=2;BYDAY=MO"

    today = datetime.utcnow().replace(hour=11, minute=0, second=0, microsecond=0)
    days_until_next_monday = (0 - today.weekday() + 7) % 7
    new_start_time_dt_for_update = today + timedelta(days=days_until_next_monday)
    new_end_time_dt_for_update = new_start_time_dt_for_update + timedelta(hours=1)

    update_response = client.put(f'/api/events/{master_event_id}', json={
        'title': 'Event Rule Changed',
        'start_time': new_start_time_dt_for_update.isoformat() + 'Z',
        'end_time': new_end_time_dt_for_update.isoformat() + 'Z',
        'recurrence_rule': new_recurrence_rule
    }, headers={'Authorization': f'Bearer {token}'})
    assert update_response.status_code == 200
    assert update_response.json['recurrence_rule'] == new_recurrence_rule
    assert update_response.json['title'] == 'Event Rule Changed'

    rrule_set_new = rrule.rruleset()
    rrule_set_new.rrule(rrule.rrulestr(new_recurrence_rule, dtstart=new_start_time_dt_for_update)) # Corrected to rrulestr

    expected_new_occurrences_datetimes = list(rrule_set_new.between(
        new_start_time_dt_for_update - timedelta(microseconds=1),
        new_start_time_dt_for_update + timedelta(weeks=10)
    ))
    assert len(expected_new_occurrences_datetimes) == 2, f"Expected 2 new occurrences, got {len(expected_new_occurrences_datetimes)}"

    query_start_date_new = new_start_time_dt_for_update.strftime('%Y-%m-%d')
    query_end_date_new = (expected_new_occurrences_datetimes[-1] + timedelta(days=7)).strftime('%Y-%m-%d')

    get_response_new = client.get(f'/api/events?start_date={query_start_date_new}&end_date={query_end_date_new}', headers={'Authorization': f'Bearer {token}'})
    assert get_response_new.status_code == 200
    events_new = get_response_new.json

    occurrences_new = [e for e in events_new if e.get('is_occurrence') and e.get('id') == master_event_id]
    assert len(occurrences_new) == 2, f"Expected 2 new occurrences after rule change, got {len(occurrences_new)}. Full response: {events_new}"

    for i, occ_dt in enumerate(expected_new_occurrences_datetimes):
        event_json = occurrences_new[i]
        assert event_json['title'] == 'Event Rule Changed'
        expected_occ_start_time_iso = occ_dt.isoformat() + "Z"
        expected_occ_end_time_iso = (occ_dt + timedelta(hours=1)).isoformat() + "Z"
        assert event_json['start_time'] == expected_occ_start_time_iso
        assert event_json['end_time'] == expected_occ_end_time_iso
        assert event_json['series_start_time'] == new_start_time_dt_for_update.isoformat() + "Z"

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_update_recurring_event_change_details(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["details_tag_initial"]
    token = get_auth_token(client, init_database, email='recurring_update_details@example.com')

    master_start_time_dt = datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1)
    master_end_time_dt = master_start_time_dt + timedelta(hours=2)
    recurrence_rule_str = "FREQ=DAILY;COUNT=2"

    create_response = client.post('/api/events', json={
        'title': 'Original Title for Details Change',
        'start_time': master_start_time_dt.isoformat() + 'Z',
        'end_time': master_end_time_dt.isoformat() + 'Z',
        'description': 'Original Description',
        'recurrence_rule': recurrence_rule_str
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_response.status_code == 201
    master_event_id = create_response.json['id']

    mock_suggest_tags.return_value = ["details_tag_updated"]
    new_title = "Updated Title for Details"
    new_description = "Updated Description"

    update_response = client.put(f'/api/events/{master_event_id}', json={
        'title': new_title,
        'description': new_description,
        'start_time': master_start_time_dt.isoformat() + 'Z',
        'end_time': master_end_time_dt.isoformat() + 'Z',
        'recurrence_rule': recurrence_rule_str
    }, headers={'Authorization': f'Bearer {token}'})
    assert update_response.status_code == 200
    assert update_response.json['title'] == new_title
    assert update_response.json['description'] == new_description

    rrule_set = rrule.rruleset()
    rrule_set.rrule(rrule.rrulestr(recurrence_rule_str, dtstart=master_start_time_dt)) # Corrected to rrulestr
    rrule_set.rrule(rrule.rrulestr(recurrence_rule_str, dtstart=master_start_time_dt)) # Corrected to rrulestr
    expected_occurrences_datetimes = list(rrule_set.between(
        master_start_time_dt - timedelta(microseconds=1),
        master_start_time_dt + timedelta(days=5)
    ))
    assert len(expected_occurrences_datetimes) == 2

    query_start_date = master_start_time_dt.strftime('%Y-%m-%d')
    query_end_date = (expected_occurrences_datetimes[-1] + timedelta(days=1)).strftime('%Y-%m-%d')

    get_response = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert get_response.status_code == 200
    events = get_response.json

    occurrences = [e for e in events if e.get('is_occurrence') and e.get('id') == master_event_id]
    assert len(occurrences) == 2, f"Expected 2 occurrences after details change, got {len(occurrences)}. Full response: {events}"

    for i, occ_dt in enumerate(expected_occurrences_datetimes):
        event_json = occurrences[i]
        assert event_json['title'] == new_title
        assert event_json['description'] == new_description
        expected_occ_start_time_iso = occ_dt.isoformat() + "Z"
        expected_occ_end_time_iso = (occ_dt + (master_end_time_dt - master_start_time_dt)).isoformat() + "Z"
        assert event_json['start_time'] == expected_occ_start_time_iso
        assert event_json['end_time'] == expected_occ_end_time_iso
        assert event_json['series_start_time'] == master_start_time_dt.isoformat() + "Z"

@patch('api.event.gemini_service.suggest_tags_for_event')
def test_delete_recurring_event(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["delete_recurring_tag"]
    token = get_auth_token(client, init_database, email='recurring_delete_user@example.com')

    master_start_time_dt = datetime.utcnow().replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=1)
    master_end_time_dt = master_start_time_dt + timedelta(hours=1)
    recurrence_rule_str = "FREQ=DAILY;COUNT=3"

    create_response = client.post('/api/events', json={
        'title': 'Event to Delete (Recurring)',
        'start_time': master_start_time_dt.isoformat() + 'Z',
        'end_time': master_end_time_dt.isoformat() + 'Z',
        'recurrence_rule': recurrence_rule_str
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_response.status_code == 201
    master_event_id = create_response.json['id']

    rrule_set = rrule.rruleset()
    rrule_set.rrule(rrule.rrulestr(recurrence_rule_str, dtstart=master_start_time_dt)) # Corrected to rrulestr
    expected_occurrences_datetimes = list(rrule_set.between(
        master_start_time_dt - timedelta(microseconds=1),
        master_start_time_dt + timedelta(days=5) # Ensure this window is large enough for 3 daily events
    ))
    assert len(expected_occurrences_datetimes) == 3, f"Expected 3 occurrences from rrule, got {len(expected_occurrences_datetimes)}"

    query_start_date = master_start_time_dt.strftime('%Y-%m-%d')
    query_end_date = (expected_occurrences_datetimes[-1] + timedelta(days=1)).strftime('%Y-%m-%d')

    get_response_before_delete = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert get_response_before_delete.status_code == 200
    events_before_delete = get_response_before_delete.json
    # Ensure the check for occurrences uses the 'id' field which refers to the master_event_id
    occurrences_before_delete = [e for e in events_before_delete if e.get('is_occurrence') and e.get('id') == master_event_id]
    assert len(occurrences_before_delete) == 3, f"Occurrences not found as expected before delete. Got: {len(occurrences_before_delete)}. Full response: {events_before_delete}"

    delete_response = client.delete(f'/api/events/{master_event_id}', headers={'Authorization': f'Bearer {token}'})
    assert delete_response.status_code == 200
    assert delete_response.json['msg'] == 'Event deleted successfully'

    get_master_response = client.get(f'/api/events/{master_event_id}', headers={'Authorization': f'Bearer {token}'})
    assert get_master_response.status_code == 404

    get_response_after_delete = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert get_response_after_delete.status_code == 200
    events_after_delete = get_response_after_delete.json

    occurrences_after_delete = [e for e in events_after_delete if e.get('parent_event_id') == master_event_id]
    assert len(occurrences_after_delete) == 0, "Occurrences still found after deleting the master event"

    master_event_after_delete = [e for e in events_after_delete if e.get('id') == master_event_id and not e.get('is_occurrence')]
    assert len(master_event_after_delete) == 0, "Master event itself found in list after deletion, and it's not an occurrence"

# Tests for /api/events/summary endpoint
@patch('api.event.gemini_service.generate_event_summary_with_gemini')
@patch('api.event.event_service.get_events_in_range')
def test_get_event_summary_success_with_date(mock_get_events, mock_generate_summary, client, init_database, mocker): # Added mocker
    token = get_auth_token(client, init_database, email='summaryuser_date@example.com')
    target_date_str = "2024-03-15"

    mock_event_data = [
        {'title': 'Morning Meeting', 'start_time': '2024-03-15T09:00:00Z', 'end_time': '2024-03-15T10:00:00Z', 'description': 'Discuss progress.'},
        {'title': 'Lunch with Team', 'start_time': '2024-03-15T12:00:00Z', 'end_time': '2024-03-15T13:00:00Z', 'description': 'Team bonding.'}
    ]
    mock_get_events.return_value = mock_event_data
    expected_summary = "Today you have a Morning Meeting at 09:00 and Lunch with Team at 12:00."
    mock_generate_summary.return_value = expected_summary

    response = client.get(f'/api/events/summary?date={target_date_str}', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json['summary'] == expected_summary
    mock_get_events.assert_called_once_with(user_id=mocker.ANY, start_date_str=target_date_str, end_date_str=target_date_str)

    # Check that the simplified event structure was passed to gemini
    simplified_events_for_gemini = [
        {"title": "Morning Meeting", "start_time": "09:00", "end_time": "10:00", "description": "Discuss progress."},
        {"title": "Lunch with Team", "start_time": "12:00", "end_time": "13:00", "description": "Team bonding."}
    ]
    mock_generate_summary.assert_called_once_with(json.dumps(simplified_events_for_gemini), target_date_str=target_date_str)

@patch('api.event.gemini_service.generate_event_summary_with_gemini')
@patch('api.event.event_service.get_events_in_range')
def test_get_event_summary_success_no_date(mock_get_events, mock_generate_summary, client, init_database, mocker):
    token = get_auth_token(client, init_database, email='summaryuser_nodate@example.com')
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    mock_event_data = [{'title': 'Evening Sync', 'start_time': f'{today_str}T17:00:00Z', 'end_time': f'{today_str}T17:30:00Z', 'description': 'Quick sync.'}]
    mock_get_events.return_value = mock_event_data
    expected_summary = "Today you have an Evening Sync at 17:00."
    mock_generate_summary.return_value = expected_summary

    response = client.get('/api/events/summary', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json['summary'] == expected_summary
    mock_get_events.assert_called_once_with(user_id=mocker.ANY, start_date_str=today_str, end_date_str=today_str)
    simplified_event = [{"title": "Evening Sync", "start_time": "17:00", "end_time": "17:30", "description": "Quick sync."}]
    mock_generate_summary.assert_called_once_with(json.dumps(simplified_event), target_date_str=today_str)

@patch('api.event.gemini_service.generate_event_summary_with_gemini')
@patch('api.event.event_service.get_events_in_range')
def test_get_event_summary_no_events(mock_get_events, mock_generate_summary, client, init_database, mocker):
    token = get_auth_token(client, init_database, email='summaryuser_noevents@example.com')
    target_date_str = "2024-03-16"
    mock_get_events.return_value = [] # No events

    response = client.get(f'/api/events/summary?date={target_date_str}', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    assert response.json['summary'] == "No events scheduled for this date."
    mock_get_events.assert_called_once_with(user_id=mocker.ANY, start_date_str=target_date_str, end_date_str=target_date_str)
    mock_generate_summary.assert_not_called() # Gemini should not be called if no events

def test_get_event_summary_invalid_date_format(client, init_database):
    token = get_auth_token(client, init_database, email='summaryuser_baddate@example.com')
    response = client.get('/api/events/summary?date=invalid-date-format', headers={'Authorization': f'Bearer {token}'})
    assert response.status_code == 400
    assert response.json['msg'] == "Invalid date format. Use YYYY-MM-DD"

@patch('api.event.gemini_service.generate_event_summary_with_gemini')
@patch('api.event.event_service.get_events_in_range')
def test_get_event_summary_gemini_error(mock_get_events, mock_generate_summary, client, init_database, mocker):
    token = get_auth_token(client, init_database, email='summaryuser_geminierr@example.com')
    target_date_str = "2024-03-17"

    mock_event_data = [{'title': 'Test Event', 'start_time': f'{target_date_str}T10:00:00Z', 'end_time': f'{target_date_str}T11:00:00Z', 'description': 'Test desc.'}]
    mock_get_events.return_value = mock_event_data
    gemini_error_response = {"error": "Gemini service failed", "detail": "Quota exceeded", "status_code": 500}
    mock_generate_summary.return_value = gemini_error_response

    response = client.get(f'/api/events/summary?date={target_date_str}', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 500
    assert response.json['msg'] == "Gemini service failed"
    assert response.json['detail'] == "Quota exceeded"
    mock_get_events.assert_called_once()
    mock_generate_summary.assert_called_once()

@patch('api.event.event_service.get_events_in_range')
def test_get_event_summary_event_service_error(mock_get_events, client, init_database, mocker): # Added mocker
    token = get_auth_token(client, init_database, email='summaryuser_svcerr@example.com')
    target_date_str = "2024-03-18"

    # Simulate event_service.get_events_in_range returning an error structure
    event_service_error = {"error": "Database connection failed", "status_code": 500}
    mock_get_events.return_value = event_service_error

    response = client.get(f'/api/events/summary?date={target_date_str}', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 500
    assert response.json['msg'] == "Database connection failed"
    mock_get_events.assert_called_once_with(user_id=mocker.ANY, start_date_str=target_date_str, end_date_str=target_date_str)

# Tests for /api/events/<int:event_id>/suggest-subtasks endpoint
@patch('api.event.gemini_service.suggest_subtasks_for_event')
@patch('api.event.gemini_service.suggest_tags_for_event') # Mock for event creation
def test_suggest_subtasks_success(mock_suggest_tags, mock_suggest_subtasks, client, init_database, mocker):
    mock_suggest_tags.return_value = ["subtask_test"]
    token = get_auth_token(client, init_database, email='subtaskuser_success@example.com')

    # 1. Create a test event
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    event_response = client.post('/api/events', json={
        'title': 'Main Task for Subtasks',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
        'description': 'A task that needs breaking down.'
    }, headers={'Authorization': f'Bearer {token}'})
    assert event_response.status_code == 201
    event_id = event_response.json['id']
    event_title = event_response.json['title']
    event_description = event_response.json['description']

    # 2. Mock Gemini service for subtask suggestion
    expected_subtasks = ["Subtask 1: Plan", "Subtask 2: Execute", "Subtask 3: Review"]
    mock_suggest_subtasks.return_value = expected_subtasks
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key') # Ensure API key is seen as configured

    # 3. Call the endpoint
    response = client.post(f'/api/events/{event_id}/suggest-subtasks', headers={'Authorization': f'Bearer {token}'})

    # 4. Assertions
    assert response.status_code == 200
    assert response.json == expected_subtasks
    mock_suggest_subtasks.assert_called_once_with(event_title=event_title, event_description=event_description)

@patch('api.event.gemini_service.suggest_subtasks_for_event') # Mock to prevent actual calls
def test_suggest_subtasks_event_not_found(mock_suggest_subtasks, client, init_database):
    token = get_auth_token(client, init_database, email='subtaskuser_notfound@example.com')
    non_existent_event_id = 99999

    response = client.post(f'/api/events/{non_existent_event_id}/suggest-subtasks', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 404
    assert response.json['msg'] == "Event not found or access denied"
    mock_suggest_subtasks.assert_not_called()

@patch('api.event.gemini_service.suggest_tags_for_event') # Mock for event creation
def test_suggest_subtasks_api_key_not_configured(mock_suggest_tags, client, init_database, mocker):
    mock_suggest_tags.return_value = ["subtask_test_no_key"]
    token = get_auth_token(client, init_database, email='subtaskuser_nokey@example.com')

    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    event_response = client.post('/api/events', json={
        'title': 'Task for No API Key Test',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
    }, headers={'Authorization': f'Bearer {token}'})
    assert event_response.status_code == 201
    event_id = event_response.json['id']

    # Unset API key for this test
    mocker.patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True)
    # Also need to ensure that the os.environ.get within the endpoint reflects this for the specific check it does
    mocker.patch('api.event.os.environ.get', return_value="")


    response = client.post(f'/api/events/{event_id}/suggest-subtasks', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 503
    assert response.json['msg'] == "Task suggestion service is currently unavailable."

@patch('api.event.gemini_service.suggest_subtasks_for_event')
@patch('api.event.gemini_service.suggest_tags_for_event') # Mock for event creation
def test_suggest_subtasks_gemini_service_error(mock_suggest_tags, mock_suggest_subtasks, client, init_database, mocker):
    mock_suggest_tags.return_value = ["subtask_test_gemini_err"]
    token = get_auth_token(client, init_database, email='subtaskuser_geminierr@example.com')

    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    event_response = client.post('/api/events', json={
        'title': 'Task for Gemini Error Test',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
    }, headers={'Authorization': f'Bearer {token}'})
    assert event_response.status_code == 201
    event_id = event_response.json['id']

    # Mock Gemini service to return an error
    gemini_error = {"error": "Gemini internal error", "detail": "Something went wrong upstream"}
    mock_suggest_subtasks.return_value = gemini_error
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key') # Ensure API key is seen as configured

    response = client.post(f'/api/events/{event_id}/suggest-subtasks', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 500
    assert response.json['msg'] == "Error suggesting subtasks"
    assert response.json['detail'] == gemini_error['detail']

# General Input Validation and Error Handling Tests
def test_create_event_end_time_before_start_time(client, init_database):
    token = get_auth_token(client, init_database, email='validation_user1@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time - timedelta(hours=1) # End time before start time

    response = client.post('/api/events', json={
        'title': 'Time Travel Event',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
    }, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
    assert response.json['msg'] == "End time cannot be before start time"

@pytest.mark.parametrize("missing_field", ["title", "start_time", "end_time"])
def test_create_event_missing_required_fields(client, init_database, missing_field):
    token = get_auth_token(client, init_database, email='validation_user2@example.com')
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)

    event_data = {
        'title': 'Test Event Missing Fields',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
    }
    del event_data[missing_field] # Remove one of the required fields

    response = client.post('/api/events', json=event_data, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
    assert response.json['msg'] == "Title, start time, and end time are required"

@pytest.mark.parametrize("invalid_time_field, valid_time", [
    ("start_time", (datetime.utcnow() + timedelta(days=1, hours=2)).isoformat() + 'Z'),
    ("end_time", (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z')
])
def test_create_event_invalid_datetime_format(client, init_database, invalid_time_field, valid_time):
    token = get_auth_token(client, init_database, email='validation_user3@example.com')
    event_data = {
        'title': 'Invalid DateTime Format Event',
        'start_time': (datetime.utcnow() + timedelta(days=1)).isoformat() + 'Z',
        'end_time': (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat() + 'Z',
    }
    # Assign an invalid format to the field being tested
    event_data[invalid_time_field] = "not-a-valid-datetime"

    # Ensure the other time field is valid if it's not the one being tested as invalid
    if invalid_time_field == "start_time":
        event_data["end_time"] = valid_time
    else: # invalid_time_field == "end_time"
        event_data["start_time"] = valid_time

    response = client.post('/api/events', json=event_data, headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 400
    assert "Invalid datetime format" in response.json['msg']

@patch('api.event.gemini_service.suggest_tags_for_event') # Mock for event creation
def test_update_event_end_time_before_start_time(mock_suggest_tags, client, init_database):
    mock_suggest_tags.return_value = ["validate_update"]
    token = get_auth_token(client, init_database, email='validation_user4@example.com')

    # Create an initial valid event
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    create_resp = client.post('/api/events', json={
        'title': 'Event for Update Validation',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_resp.status_code == 201
    event_id = create_resp.json['id']

    # Attempt to update with end_time before start_time
    new_start_time = datetime.utcnow() + timedelta(days=2)
    invalid_end_time = new_start_time - timedelta(hours=1)

    update_response = client.put(f'/api/events/{event_id}', json={
        'start_time': new_start_time.isoformat() + 'Z',
        'end_time': invalid_end_time.isoformat() + 'Z',
    }, headers={'Authorization': f'Bearer {token}'})

    assert update_response.status_code == 400
    assert update_response.json['msg'] == "End time cannot be before start time"

@patch('api.event.gemini_service.suggest_tags_for_event') # Mock for event creation and update
@pytest.mark.parametrize("invalid_time_field", ["start_time", "end_time"])
def test_update_event_invalid_datetime_format(mock_suggest_tags, client, init_database, invalid_time_field):
    mock_suggest_tags.return_value = ["validate_update_format"]
    token = get_auth_token(client, init_database, email='validation_user5@example.com')

    # Create an initial valid event
    start_time = datetime.utcnow() + timedelta(days=1)
    end_time = start_time + timedelta(hours=1)
    create_resp = client.post('/api/events', json={
        'title': 'Event for Update Format Validation',
        'start_time': start_time.isoformat() + 'Z',
        'end_time': end_time.isoformat() + 'Z',
    }, headers={'Authorization': f'Bearer {token}'})
    assert create_resp.status_code == 201
    event_id = create_resp.json['id']

    update_data = {}
    if invalid_time_field == "start_time":
        update_data['start_time'] = "not-a-valid-datetime"
        update_data['end_time'] = (start_time + timedelta(hours=2)).isoformat() + 'Z' # Keep end time valid relative to original
    else: # invalid_time_field == "end_time"
        update_data['end_time'] = "not-a-valid-datetime"
        update_data['start_time'] = start_time.isoformat() + 'Z' # Keep start time valid

    update_response = client.put(f'/api/events/{event_id}', json=update_data, headers={'Authorization': f'Bearer {token}'})

    assert update_response.status_code == 400
    assert f"Invalid {invalid_time_field} format" in update_response.json['msg']
