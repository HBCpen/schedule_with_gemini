import pytest
import json
import os # Added os import
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from models.event import Event
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
    assert response.json['msg'] == 'No input text provided.'

def test_parse_natural_language_api_key_not_configured(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='nlp_noapikey@example.com')
    mocker.patch.dict(os.environ, {"GEMINI_API_KEY": ""}, clear=True) # Unset API key

    response = client.post('/api/events/parse-natural-language',
                           json={'text': 'Some event text'},
                           headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 503
    assert response.json['msg'] == 'Gemini API key not configured.'

def test_parse_natural_language_gemini_service_error(client, init_database, mocker):
    token = get_auth_token(client, init_database, email='nlp_geminierror@example.com')
    mock_gemini_parse = mocker.patch('api.event.gemini_service.parse_event_text_with_gemini')
    mock_gemini_parse.return_value = {"error": "Gemini processing failed"}
    mocker.patch('api.event.os.environ.get', return_value='fake_gemini_api_key') # Mock API key check

    response = client.post('/api/events/parse-natural-language',
                           json={'text': 'Another event text'},
                           headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 500 # Assuming the main function relays this as a 500
    assert "error" in response.json
    assert response.json["error"] == "Gemini processing failed"

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
    mock_mail_send = mocker.patch('app.mail.send')

    # 4. Call reminder_service.send_event_reminders()
    from services import reminder_service
    # Ensure the service uses the same app context or has one set up
    # The service itself calls create_app() so it establishes its own context.
    reminder_service.send_event_reminders()

    # 5. Assertions
    with client.application.app_context():
        # Retrieve events from DB to check updated reminder_sent status
        retrieved_event_soon = Event.query.get(event_soon_id)
        retrieved_event_far_future = Event.query.get(event_far_future_id)
        retrieved_event_already_reminded = Event.query.get(event_already_reminded_id)
        retrieved_event_past_in_window = Event.query.get(event_past_in_window_id)
        retrieved_event_too_far_past = Event.query.get(event_too_far_past_id)

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
        sent_for_soon = any(
            call.kwargs['subject'] == f"Reminder: {event_soon.title}" and
            call.kwargs['recipients'] == expected_recipients
            for call in call_args_list
        )
        assert sent_for_soon, "Mail for 'event_soon' was not sent or had incorrect parameters."

        # Check for event_past_in_window reminder
        sent_for_past_in_window = any(
            call.kwargs['subject'] == f"Reminder: {event_past_in_window.title}" and
            call.kwargs['recipients'] == expected_recipients
            for call in call_args_list
        )
        assert sent_for_past_in_window, "Mail for 'event_past_in_window' was not sent or had incorrect parameters."

        # Ensure no other emails were sent
        for call in call_args_list:
            assert call.kwargs['recipients'] == expected_recipients
            if call.kwargs['subject'] != f"Reminder: {event_soon.title}" and \
               call.kwargs['subject'] != f"Reminder: {event_past_in_window.title}":
                assert False, f"Unexpected email sent: {call.kwargs['subject']}"

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
        event_from_db = Event.query.get(event_id)
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
    rrule_set.rrule(rrule.fromdomain(recurrence_rule_str, dtstart=master_start_time_dt))

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

    occurrences = [e for e in events_all if e.get('is_occurrence') and e.get('parent_event_id') == master_event_id]
    assert len(occurrences) == 3, f"Expected 3 occurrences, got {len(occurrences)}. Full response: {events_all}"

    for i, occ_dt in enumerate(expected_occurrences_datetimes):
        event_json = occurrences[i]
        assert event_json['title'] == master_event_title
        assert event_json['description'] == master_event_description
        assert event_json['is_occurrence'] == True
        assert event_json['parent_event_id'] == master_event_id

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
    occurrences_partial = [e for e in events_partial if e.get('is_occurrence') and e.get('parent_event_id') == master_event_id]
    assert len(occurrences_partial) == 2, f"Expected 2 partial occurrences, got {len(occurrences_partial)}. Full response: {events_partial}"
    assert occurrences_partial[0]['start_time'].startswith(expected_occurrences_datetimes[0].isoformat())
    assert occurrences_partial[1]['start_time'].startswith(expected_occurrences_datetimes[1].isoformat())

    # Test with a date range that includes no occurrences
    query_none_start_date = (expected_occurrences_datetimes[-1] + timedelta(days=10)).strftime('%Y-%m-%d')
    query_none_end_date = (expected_occurrences_datetimes[-1] + timedelta(days=12)).strftime('%Y-%m-%d')
    response_none = client.get(f'/api/events?start_date={query_none_start_date}&end_date={query_none_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert response_none.status_code == 200
    events_none = response_none.json
    occurrences_none = [e for e in events_none if e.get('is_occurrence') and e.get('parent_event_id') == master_event_id]
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
    rrule_set_new.rrule(rrule.fromdomain(new_recurrence_rule, dtstart=new_start_time_dt_for_update))

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

    occurrences_new = [e for e in events_new if e.get('is_occurrence') and e.get('parent_event_id') == master_event_id]
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
    rrule_set.rrule(rrule.fromdomain(recurrence_rule_str, dtstart=master_start_time_dt))
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

    occurrences = [e for e in events if e.get('is_occurrence') and e.get('parent_event_id') == master_event_id]
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
    rrule_set.rrule(rrule.fromdomain(recurrence_rule_str, dtstart=master_start_time_dt))
    expected_occurrences_datetimes = list(rrule_set.between(
        master_start_time_dt - timedelta(microseconds=1),
        master_start_time_dt + timedelta(days=5)
    ))
    assert len(expected_occurrences_datetimes) == 3

    query_start_date = master_start_time_dt.strftime('%Y-%m-%d')
    query_end_date = (expected_occurrences_datetimes[-1] + timedelta(days=1)).strftime('%Y-%m-%d')

    get_response_before_delete = client.get(f'/api/events?start_date={query_start_date}&end_date={query_end_date}', headers={'Authorization': f'Bearer {token}'})
    assert get_response_before_delete.status_code == 200
    events_before_delete = get_response_before_delete.json
    occurrences_before_delete = [e for e in events_before_delete if e.get('is_occurrence') and e.get('parent_event_id') == master_event_id]
    assert len(occurrences_before_delete) == 3, "Occurrences not found before delete operation"

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
def test_get_event_summary_success_with_date(mock_get_events, mock_generate_summary, client, init_database):
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
def test_get_event_summary_event_service_error(mock_get_events, client, init_database):
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
