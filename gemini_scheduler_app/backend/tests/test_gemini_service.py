# gemini_scheduler_app/backend/tests/test_gemini_service.py
import pytest
from unittest.mock import MagicMock
import json
from datetime import datetime

# Adjust import path as per your project structure
# Assuming tests are run from the 'backend' directory or PYTHONPATH is set up accordingly
from services.gemini_service import find_free_time_slots_with_gemini

# Test cases for find_free_time_slots_with_gemini

def test_find_free_time_successful_response(monkeypatch):
    """
    Tests successful retrieval and parsing of free time slots from Gemini.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    expected_slots = [
        {"start_time": "2024-08-01T10:00:00", "end_time": "2024-08-01T11:00:00"},
        {"start_time": "2024-08-01T14:00:00", "end_time": "2024-08-01T15:00:00"}
    ]
    mock_gemini_response.text = json.dumps(expected_slots)
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    user_query = "Find a 1-hour slot tomorrow morning"
    events_json = json.dumps([
        {"title": "Existing Meeting", "start_time": "2024-08-01T09:00:00", "end_time": "2024-08-01T09:30:00"}
    ])

    result = find_free_time_slots_with_gemini(user_query, events_json)

    assert result == expected_slots
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()
    # Check that today's date was included in the prompt
    called_prompt = mock_model_instance.generate_content.call_args[0][0]
    assert datetime.now().strftime('%Y-%m-%d') in called_prompt

def test_find_free_time_api_key_not_configured(monkeypatch):
    """
    Tests the scenario where the Gemini API key is not configured.
    """
    mock_get_gemini_model = MagicMock(return_value=None)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = find_free_time_slots_with_gemini("any query", "[]")

    assert isinstance(result, dict)
    assert result.get("error") == "Gemini API not configured"
    assert result.get("detail") == "API key missing or invalid."
    mock_get_gemini_model.assert_called_once()

def test_find_free_time_gemini_api_error(monkeypatch):
    """
    Tests handling of an error during the Gemini API call.
    """
    mock_model_instance = MagicMock()
    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    mock_model_instance.generate_content.side_effect = Exception("Gemini network error")

    result = find_free_time_slots_with_gemini("any query", "[]")

    assert isinstance(result, dict)
    assert result.get("error") == "Gemini API error"
    assert result.get("detail") == "Gemini network error"
    # Ensure raw_response is included, even if it's a generic message for this type of error
    assert "raw_response" in result
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

def test_find_free_time_malformed_json_response(monkeypatch):
    """
    Tests handling of a malformed JSON response from Gemini.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    malformed_json_text = "This is not JSON, it's just a string {oops"
    mock_gemini_response.text = malformed_json_text
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = find_free_time_slots_with_gemini("any query", "[]")

    assert isinstance(result, dict)
    assert result.get("error") == "Invalid JSON response from Gemini"
    assert result.get("raw_response") == malformed_json_text
    assert "detail" in result # Should contain the JSONDecodeError string
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

def test_find_free_time_empty_array_response(monkeypatch):
    """
    Tests handling of an empty array JSON response from Gemini (no slots found).
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "[]"
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = find_free_time_slots_with_gemini("any query", "[]")

    assert result == []
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

def test_find_free_time_json_wrapped_in_markdown_ticks(monkeypatch):
    """
    Tests successful parsing when JSON is wrapped in markdown backticks.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    expected_slots = [{"start_time": "2024-08-05T10:00:00", "end_time": "2024-08-05T11:00:00"}]
    # Test with ```json prefix and ``` suffix
    mock_gemini_response.text = f"```json\n{json.dumps(expected_slots)}\n```"
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = find_free_time_slots_with_gemini("any query", "[]")
    assert result == expected_slots
    mock_get_gemini_model.assert_called_once() # Should be called once per test
    mock_model_instance.generate_content.assert_called_once()


def test_find_free_time_json_wrapped_in_simple_markdown_ticks(monkeypatch):
    """
    Tests successful parsing when JSON is wrapped in simple markdown backticks.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    expected_slots = [{"start_time": "2024-08-06T12:00:00", "end_time": "2024-08-06T13:00:00"}]
    # Test with ``` prefix and ``` suffix but no "json" language identifier
    mock_gemini_response.text = f"```{json.dumps(expected_slots)}```" # One line, simple ticks
    mock_model_instance.generate_content.return_value = mock_gemini_response

    # Reset and re-assign mock_get_gemini_model for this specific test case, or ensure it's fresh
    # if tests are run in isolation or monkeypatch is function-scoped (which it is by default in pytest)
    current_mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', current_mock_get_gemini_model)

    result = find_free_time_slots_with_gemini("any query", "[]")
    assert result == expected_slots
    current_mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once() # This will be the second call if instance is shared and not reset

def test_find_free_time_empty_string_response_handled_as_empty_list(monkeypatch):
    """
    Tests that an empty string response from Gemini is handled as an empty list.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "" # Empty string
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = find_free_time_slots_with_gemini("any query", "[]")

    assert result == [] # As per function logic, empty string should result in empty list
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

# To run these tests, navigate to the `backend` directory and run `pytest`
# Ensure services/gemini_service.py can be imported from that location.
# Example: python -m pytest tests/test_gemini_service.py
# (or simply `pytest` if __init__.py files are set up correctly for package discovery)

from services.gemini_service import suggest_tags_for_event # Added import

# Test cases for suggest_tags_for_event

def test_suggest_tags_success(monkeypatch):
    """
    Tests successful tag suggestion from Gemini.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    expected_tags = ["work", "meeting"]
    mock_gemini_response.text = json.dumps(expected_tags)
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = suggest_tags_for_event("Team Meeting", "Discuss project milestones")

    assert result == expected_tags
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()
    # Check that title and description were included in the prompt
    called_prompt = mock_model_instance.generate_content.call_args[0][0]
    assert "Team Meeting" in called_prompt
    assert "Discuss project milestones" in called_prompt

def test_suggest_tags_gemini_error_returns_default(monkeypatch):
    """
    Tests that a Gemini API error results in the default tag list.
    """
    mock_model_instance = MagicMock()
    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    mock_model_instance.generate_content.side_effect = Exception("Gemini network error")

    result = suggest_tags_for_event("Error case", "Test error")

    assert result == ["general"]
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

def test_suggest_tags_invalid_json_returns_default(monkeypatch):
    """
    Tests that an invalid JSON response from Gemini results in the default tag list.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "this is not valid json"
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = suggest_tags_for_event("Invalid JSON", "Test invalid response")

    assert result == ["general"]
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

def test_suggest_tags_empty_list_from_gemini(monkeypatch):
    """
    Tests that an empty list from Gemini is returned as such.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = json.dumps([]) # Gemini returns an empty list
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = suggest_tags_for_event("Empty list", "Test empty list response")

    assert result == []
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

def test_suggest_tags_gemini_model_none(monkeypatch):
    """
    Tests that if get_gemini_model returns None, default tags are returned.
    """
    mock_get_gemini_model = MagicMock(return_value=None)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = suggest_tags_for_event("No model", "Test no model available")

    assert result == ["general"]
    mock_get_gemini_model.assert_called_once()

def test_suggest_tags_markdown_stripping(monkeypatch):
    """
    Tests that markdown backticks are stripped from Gemini response.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    expected_tags = ["project", "update"]
    mock_gemini_response.text = f"```json\n{json.dumps(expected_tags)}\n```"
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = suggest_tags_for_event("Markdown Test", "Check stripping")

    assert result == expected_tags
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

def test_suggest_tags_unexpected_json_structure(monkeypatch):
    """
    Tests that an unexpected JSON structure (e.g., dict instead of list) returns default.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    # Gemini returns a dictionary instead of a list of strings
    mock_gemini_response.text = json.dumps({"tag": "work", "confidence": 0.9})
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = suggest_tags_for_event("Unexpected JSON", "Test structure")

    assert result == ["general"] # Fallback for unexpected structure
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()

def test_suggest_tags_empty_string_response_from_gemini(monkeypatch):
    """
    Tests that an empty string response from Gemini results in default tags.
    """
    mock_model_instance = MagicMock()
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "" # Empty string response
    mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_gemini_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_gemini_model)

    result = suggest_tags_for_event("Empty String", "Test empty string response")

    assert result == ["general"] # As per implementation, empty string leads to "general"
    mock_get_gemini_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once()


# Import the function to be tested
from services.gemini_service import get_related_information_for_event

# Test cases for get_related_information_for_event

EVENT_LOCATION = "Conference Center"
EVENT_START_ISO = "2024-09-15T14:00:00Z"
EVENT_TITLE_MEAL = "Lunch with Client"
EVENT_DESC_MEAL = "Discuss project over dinner"
EVENT_TITLE_NO_MEAL = "Project Sync"
EVENT_DESC_NO_MEAL = "Regular team update"

# Define a sample related_content for reuse
SAMPLE_RELATED_CONTENT = [
    {"type": "article", "title": "Local Tech Conference Highlights", "source": "Tech News Daily", "url": "http://example.com/article1"},
    {"type": "document", "title": "Event Agenda", "summary": "Detailed schedule for the conference."}
]

def mock_gemini_model(monkeypatch, response_text=None, side_effect=None):
    """Helper to mock the Gemini model and its response."""
    mock_model_instance = MagicMock()
    if side_effect:
        mock_model_instance.generate_content.side_effect = side_effect
    else:
        mock_gemini_response = MagicMock()
        mock_gemini_response.text = response_text
        mock_model_instance.generate_content.return_value = mock_gemini_response

    mock_get_model = MagicMock(return_value=mock_model_instance)
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)
    return mock_get_model, mock_model_instance

def test_get_related_info_success_with_all_info(monkeypatch):
    """Test successful retrieval of weather, traffic, and restaurant suggestions."""
    expected_response_data = {
        "weather": {"forecast_date": "2024-09-15", "location": EVENT_LOCATION, "condition": "Sunny", "temperature_high": "25C", "temperature_low": "15C", "precipitation_chance": "10%", "summary": "Pleasant weather"},
        "traffic": {"location": EVENT_LOCATION, "assessment_time": "14:00", "congestion_level": "Low", "expected_travel_advisory": "No delays", "summary": "Smooth traffic"},
        "suggestions": [{"type": "restaurant", "name": "The Gourmet Place", "details": "Fine dining"}],
        "related_content": SAMPLE_RELATED_CONTENT
    }
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text=json.dumps(expected_response_data))

    result = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO, EVENT_TITLE_MEAL)

    assert result == expected_response_data
    mock_model_instance.generate_content.assert_called_once()
    prompt = mock_model_instance.generate_content.call_args[0][0]
    assert "Restaurant suggestions" in prompt
    assert "Relevant news articles or documents" in prompt
    assert "related_content" in prompt # Check for key in prompt description of JSON

def test_get_related_info_success_no_restaurant_keywords(monkeypatch):
    """Test successful retrieval when no meal keywords are present, so no restaurant suggestions asked."""
    expected_response_data = {
        "weather": {"forecast_date": "2024-09-15", "location": EVENT_LOCATION, "condition": "Cloudy"},
        "traffic": {"location": EVENT_LOCATION, "congestion_level": "Moderate"},
        "suggestions": [], # Expect empty suggestions as not requested
        "related_content": [] # Expect empty related_content as well for this test case, or could be populated
    }
    # For this test, let's assume Gemini might still return related_content
    response_from_gemini = {
        "weather": expected_response_data["weather"],
        "traffic": expected_response_data["traffic"],
        "suggestions": [], # Gemini returns empty list as per prompt
        "related_content": SAMPLE_RELATED_CONTENT # Gemini might find this anyway
    }
    expected_output = {
        "weather": expected_response_data["weather"],
        "traffic": expected_response_data["traffic"],
        "suggestions": [],
        "related_content": SAMPLE_RELATED_CONTENT
    }

    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text=json.dumps(response_from_gemini))

    result = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO, EVENT_TITLE_NO_MEAL, EVENT_DESC_NO_MEAL)

    assert result == expected_output
    mock_model_instance.generate_content.assert_called_once()
    prompt = mock_model_instance.generate_content.call_args[0][0]
    assert "Restaurant suggestions" not in prompt
    assert "Return an empty list for suggestions" in prompt
    assert "Relevant news articles or documents" in prompt
    assert "related_content" in prompt


def test_get_related_info_success_empty_suggestions_and_content_from_gemini(monkeypatch):
    """Test handling when Gemini returns an empty list for suggestions and related_content."""
    expected_response_data = {
        "weather": {"forecast_date": "2024-09-15", "condition": "Rainy"},
        "traffic": {"congestion_level": "High"},
        "suggestions": [],
        "related_content": []
    }
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text=json.dumps(expected_response_data))

    result = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO, EVENT_TITLE_MEAL) # Meal title, so suggestions asked

    assert result == expected_response_data
    mock_model_instance.generate_content.assert_called_once()
    prompt = mock_model_instance.generate_content.call_args[0][0]
    assert "Restaurant suggestions" in prompt # It was asked for
    assert "Relevant news articles or documents" in prompt # This is always asked for

def test_get_related_info_gemini_api_error(monkeypatch):
    """Test handling of a Gemini API call error."""
    mock_get_model, mock_model_instance = mock_gemini_model(monkeypatch, side_effect=Exception("Gemini API Failure"))

    result = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO)

    assert "error" in result
    assert result["detail"] == "Gemini API Failure"
    mock_get_model.assert_called_once()
    mock_model_instance.generate_content.assert_called_once() # generate_content is called before exception

def test_get_related_info_gemini_json_decode_error(monkeypatch):
    """Test handling of malformed JSON from Gemini."""
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text="not a valid json")

    result = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO)

    assert "error" in result
    assert result["error"] == "Invalid JSON response from Gemini"
    assert result["raw_response"] == "not a valid json"
    mock_model_instance.generate_content.assert_called_once()

def test_get_related_info_gemini_model_unavailable(monkeypatch):
    """Test handling when the Gemini model is unavailable (e.g., API key missing)."""
    mock_get_model = MagicMock(return_value=None) # Simulate get_gemini_model returning None
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)

    result = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO)

    assert "error" in result
    assert result["error"] == "Gemini API not configured"
    mock_get_model.assert_called_once()

def test_get_related_info_invalid_iso_date_input(monkeypatch):
    """Test providing a malformed ISO date string."""
    # No need to mock Gemini model as it shouldn't be called if date parsing fails first
    mock_get_model_func = MagicMock()
    monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model_func)

    result = get_related_information_for_event(EVENT_LOCATION, "invalid-date-format")

    assert "error" in result
    assert result["error"] == "Invalid ISO format for event_start_datetime_iso"
    mock_get_model_func.assert_not_called() # Gemini model should not be retrieved or used

def test_get_related_info_prompt_construction_basic(monkeypatch):
    """Test basic prompt construction for key elements."""
    # Content doesn't matter here, focus is on prompt
    expected_partial_response = {"weather": {}, "traffic": {}, "suggestions": [], "related_content": []}
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text=json.dumps(expected_partial_response))

    # Parse date for prompt checking
    event_dt = datetime.fromisoformat(EVENT_START_ISO.replace("Z", "+00:00"))
    event_date_str = event_dt.strftime('%Y-%m-%d')
    event_time_str = event_dt.strftime('%H:%M')

    get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO, EVENT_TITLE_NO_MEAL)

    mock_model_instance.generate_content.assert_called_once()
    prompt = mock_model_instance.generate_content.call_args[0][0]

    assert EVENT_LOCATION in prompt
    assert event_date_str in prompt
    assert event_time_str in prompt
    assert "Weather forecast" in prompt
    assert "Traffic overview" in prompt
    assert "Relevant news articles or documents" in prompt # Check for related content request
    assert "The 'related_content' key should hold a list of objects" in prompt # Check for related content in JSON spec
    assert "Return an empty list for suggestions" in prompt # Since EVENT_TITLE_NO_MEAL is used

def test_get_related_info_prompt_construction_with_meal_keyword_title(monkeypatch):
    """Test prompt construction when title contains a meal keyword."""
    expected_partial_response = {"weather": {}, "traffic": {}, "suggestions": [], "related_content": []}
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text=json.dumps(expected_partial_response))

    get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO, event_title=EVENT_TITLE_MEAL)

    mock_model_instance.generate_content.assert_called_once()
    prompt = mock_model_instance.generate_content.call_args[0][0]
    assert "Restaurant suggestions" in prompt
    assert "Relevant news articles or documents" in prompt

def test_get_related_info_prompt_construction_with_meal_keyword_description(monkeypatch):
    """Test prompt construction when description contains a meal keyword."""
    expected_partial_response = {"weather": {}, "traffic": {}, "suggestions": [], "related_content": []}
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text=json.dumps(expected_partial_response))

    get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO, event_title=EVENT_TITLE_NO_MEAL, event_description=EVENT_DESC_MEAL)

    mock_model_instance.generate_content.assert_called_once()
    prompt = mock_model_instance.generate_content.call_args[0][0]
    assert "Restaurant suggestions" in prompt
    assert "Relevant news articles or documents" in prompt

def test_get_related_info_missing_top_level_keys_from_gemini(monkeypatch):
    """Test Gemini response missing 'weather', 'traffic', 'suggestions', or 'related_content' keys."""
    malformed_data_missing_traffic = {
        "weather": {"condition": "Sunny"},
        # "traffic" key is missing
        "suggestions": [],
        "related_content": []
    }
    _, mock_model_instance_traffic = mock_gemini_model(monkeypatch, response_text=json.dumps(malformed_data_missing_traffic))
    result_traffic = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO)
    assert "error" in result_traffic
    assert "Missing one or more top-level keys" in result_traffic["detail"]
    assert "traffic" in result_traffic["detail"] # Check if the message mentions traffic
    mock_model_instance_traffic.generate_content.assert_called_once()

    malformed_data_missing_content = {
        "weather": {"condition": "Sunny"},
        "traffic": {"congestion_level": "Low"},
        "suggestions": []
        # "related_content" key is missing
    }
    # Need to re-mock as the previous call consumed the mock
    _, mock_model_instance_content = mock_gemini_model(monkeypatch, response_text=json.dumps(malformed_data_missing_content))
    result_content = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO)
    assert "error" in result_content
    assert "Missing one or more top-level keys" in result_content["detail"]
    assert "related_content" in result_content["detail"] # Check if the message mentions related_content
    mock_model_instance_content.generate_content.assert_called_once()


def test_get_related_info_field_not_a_list(monkeypatch):
    """Test Gemini response where 'suggestions' or 'related_content' is not a list."""
    # Test for suggestions not being a list
    malformed_suggestions = {
        "weather": {"condition": "Cloudy"}, "traffic": {"congestion_level": "Low"},
        "suggestions": {"error": "should be a list"}, # Incorrect type
        "related_content": []
    }
    expected_corrected_suggestions = {
        "weather": {"condition": "Cloudy"}, "traffic": {"congestion_level": "Low"},
        "suggestions": [], "related_content": []
    }
    _, mock_model_instance_sugg = mock_gemini_model(monkeypatch, response_text=json.dumps(malformed_suggestions))
    result_sugg = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO)
    assert result_sugg == expected_corrected_suggestions
    mock_model_instance_sugg.generate_content.assert_called_once()

    # Test for related_content not being a list
    malformed_related_content = {
        "weather": {"condition": "Cloudy"}, "traffic": {"congestion_level": "Low"},
        "suggestions": [],
        "related_content": "should be a list" # Incorrect type
    }
    expected_corrected_content = {
        "weather": {"condition": "Cloudy"}, "traffic": {"congestion_level": "Low"},
        "suggestions": [], "related_content": []
    }
    _, mock_model_instance_rc = mock_gemini_model(monkeypatch, response_text=json.dumps(malformed_related_content))
    result_rc = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO)
    assert result_rc == expected_corrected_content
    mock_model_instance_rc.generate_content.assert_called_once()


def test_get_related_info_empty_response_from_gemini(monkeypatch):
    """Test handling of an empty string response from Gemini."""
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text="") # Empty string

    result = get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO)

    assert "error" in result
    assert result["error"] == "Empty response from Gemini"
    mock_model_instance.generate_content.assert_called_once()
