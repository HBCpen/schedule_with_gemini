import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from models.event import Event
from app import db # Assuming db is the SQLAlchemy instance from app.py

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
# The following line was the duplicated end-of-file marker and is now removed.
# [end of gemini_scheduler_app/backend/tests/test_event_api.py]
