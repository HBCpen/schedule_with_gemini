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
