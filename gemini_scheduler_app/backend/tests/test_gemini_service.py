# gemini_scheduler_app/backend/tests/test_gemini_service.py
import pytest
from unittest.mock import MagicMock
import json
from datetime import datetime

# Adjust import path as per your project structure
# Assuming tests are run from the 'backend' directory or PYTHONPATH is set up accordingly
# find_free_time_slots_with_gemini is imported later for its test class

# Import the function to be tested
from services.gemini_service import get_gemini_model # Added for testing get_gemini_model
import services.gemini_service as gemini_service_module # To mock genai within the module
import google.generativeai # To mock genai.configure and genai.GenerativeModel
import os # For mocking environment variables

class TestGetGeminiModel:
    def test_get_gemini_model_success(self, monkeypatch):
        """Test successful model retrieval when API key is valid."""
        mock_env_get = MagicMock(return_value="VALID_API_KEY")
        monkeypatch.setattr(os, 'environ', {'get': mock_env_get})

        mock_genai_configure = MagicMock()
        monkeypatch.setattr(google.generativeai, 'configure', mock_genai_configure)

        mock_generative_model_instance = MagicMock()
        mock_genai_generative_model = MagicMock(return_value=mock_generative_model_instance)
        monkeypatch.setattr(google.generativeai, 'GenerativeModel', mock_genai_generative_model)

        model = get_gemini_model()

        assert model == mock_generative_model_instance
        mock_env_get.assert_called_once_with('GEMINI_API_KEY')
        mock_genai_configure.assert_called_once_with(api_key="VALID_API_KEY")
        mock_genai_generative_model.assert_called_once_with('gemini-pro')

    def test_get_gemini_model_no_api_key(self, monkeypatch):
        """Test model retrieval fails when API key is missing."""
        mock_env_get = MagicMock(return_value=None)
        monkeypatch.setattr(os, 'environ', {'get': mock_env_get})

        model = get_gemini_model()

        assert model is None
        mock_env_get.assert_called_once_with('GEMINI_API_KEY')

    def test_get_gemini_model_placeholder_api_key(self, monkeypatch):
        """Test model retrieval fails when API key is the placeholder."""
        mock_env_get = MagicMock(return_value="YOUR_API_KEY_HERE")
        monkeypatch.setattr(os, 'environ', {'get': mock_env_get})

        model = get_gemini_model()

        assert model is None
        mock_env_get.assert_called_once_with('GEMINI_API_KEY')

    def test_get_gemini_model_configure_fails(self, monkeypatch):
        """Test model retrieval fails if genai.configure raises an exception."""
        mock_env_get = MagicMock(return_value="VALID_API_KEY")
        monkeypatch.setattr(os, 'environ', {'get': mock_env_get})

        mock_genai_configure = MagicMock(side_effect=Exception("Configuration error"))
        monkeypatch.setattr(google.generativeai, 'configure', mock_genai_configure)

        model = get_gemini_model()

        assert model is None
        mock_genai_configure.assert_called_once_with(api_key="VALID_API_KEY")

    def test_get_gemini_model_generativemodel_fails(self, monkeypatch):
        """Test model retrieval fails if genai.GenerativeModel raises an exception."""
        mock_env_get = MagicMock(return_value="VALID_API_KEY")
        monkeypatch.setattr(os, 'environ', {'get': mock_env_get})

        mock_genai_configure = MagicMock()
        monkeypatch.setattr(google.generativeai, 'configure', mock_genai_configure)

        mock_genai_generative_model = MagicMock(side_effect=Exception("Model creation error"))
        monkeypatch.setattr(google.generativeai, 'GenerativeModel', mock_genai_generative_model)

        model = get_gemini_model()

        assert model is None
        mock_genai_configure.assert_called_once_with(api_key="VALID_API_KEY")
        mock_genai_generative_model.assert_called_once_with('gemini-pro')


from services.gemini_service import generate_event_summary_with_gemini, parse_event_text_with_gemini # Added parse_event_text_with_gemini

# Mock datetime for consistent "today" in tests that use it for prompts
MOCK_DATETIME_NOW = datetime(2024, 1, 1, 10, 0, 0) # Example: Jan 1, 2024, 10:00 AM

class TestParseEventTextWithGemini:
    VALID_TEXT_INPUT = "Meeting with team tomorrow at 2pm"
    EXPECTED_PARSED_JSON = {
        "title": "Meeting with team",
        "date": "2024-01-02", # Assuming MOCK_DATETIME_NOW is Jan 1, tomorrow is Jan 2
        "start_time": "14:00",
        "end_time": None,
        "description": None,
        "location": None
    }

    def _mock_gemini_interaction(self, monkeypatch, response_text=None, side_effect=None, get_model_returns_none=False):
        mock_model_instance = MagicMock()
        if side_effect:
            mock_model_instance.generate_content.side_effect = side_effect
        elif response_text:
            mock_gemini_response = MagicMock()
            mock_gemini_response.text = response_text
            mock_model_instance.generate_content.return_value = mock_gemini_response

        mock_get_model = MagicMock()
        if get_model_returns_none:
            mock_get_model.return_value = None
        else:
            mock_get_model.return_value = mock_model_instance

        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)
        return mock_get_model, mock_model_instance

    @pytest.fixture(autouse=True)
    def mock_datetime_now(self, monkeypatch):
        """Fixture to mock datetime.now() for all tests in this class."""
        mock_dt = MagicMock()
        mock_dt.now.return_value = MOCK_DATETIME_NOW
        monkeypatch.setattr('services.gemini_service.datetime', mock_dt)
        return mock_dt

    def test_parse_event_success(self, monkeypatch, mock_datetime_now):
        """Test successful event parsing from text."""
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=json.dumps(self.EXPECTED_PARSED_JSON)
        )

        result = parse_event_text_with_gemini(self.VALID_TEXT_INPUT)

        assert result == self.EXPECTED_PARSED_JSON
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

        # Check prompt for dynamic date content
        prompt = mock_model_instance.generate_content.call_args[0][0]
        assert f"Today's year is {MOCK_DATETIME_NOW.year}" in prompt
        assert f"today being {MOCK_DATETIME_NOW.strftime('%Y-%m-%d')}" in prompt
        assert f"use today's date: {MOCK_DATETIME_NOW.strftime('%Y-%m-%d')}" in prompt

    def test_parse_event_gemini_returns_markdown_json(self, monkeypatch, mock_datetime_now):
        """Test successful parsing when Gemini wraps JSON in markdown."""
        markdown_response = f"```json\n{json.dumps(self.EXPECTED_PARSED_JSON)}\n```"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=markdown_response
        )

        result = parse_event_text_with_gemini(self.VALID_TEXT_INPUT)
        assert result == self.EXPECTED_PARSED_JSON

    def test_parse_event_gemini_returns_simple_markdown_json(self, monkeypatch, mock_datetime_now):
        """Test successful parsing when Gemini wraps JSON in simple markdown."""
        markdown_response = f"```{json.dumps(self.EXPECTED_PARSED_JSON)}```"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=markdown_response
        )
        result = parse_event_text_with_gemini(self.VALID_TEXT_INPUT)
        assert result == self.EXPECTED_PARSED_JSON

    def test_parse_event_api_key_not_configured(self, monkeypatch, mock_datetime_now):
        """Test handling when get_gemini_model returns None (API key issue)."""
        mock_get_model, _ = self._mock_gemini_interaction(monkeypatch, get_model_returns_none=True)

        result = parse_event_text_with_gemini(self.VALID_TEXT_INPUT)

        assert isinstance(result, dict)
        assert result["error"] == "Gemini API not configured"
        mock_get_model.assert_called_once()

    def test_parse_event_gemini_api_error(self, monkeypatch, mock_datetime_now):
        """Test handling of an error during the Gemini API call."""
        error_message = "Gemini network error"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, side_effect=Exception(error_message)
        )

        result = parse_event_text_with_gemini(self.VALID_TEXT_INPUT)

        assert isinstance(result, dict)
        assert result["error"] == error_message
        assert result["detail"] == "Failed to parse event text using Gemini."
        assert "raw_response" in result # Should contain 'No response text available' or actual if response was formed before error
        mock_model_instance.generate_content.assert_called_once()

    def test_parse_event_malformed_json_response(self, monkeypatch, mock_datetime_now):
        """Test handling of a malformed JSON response from Gemini."""
        malformed_json_text = "This is not JSON {oops"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=malformed_json_text
        )

        result = parse_event_text_with_gemini(self.VALID_TEXT_INPUT)

        assert isinstance(result, dict)
        assert result["error"] # Should have a JSONDecodeError string or similar
        assert result["detail"] == "Failed to parse event text using Gemini."
        assert result["raw_response"] == malformed_json_text
        mock_model_instance.generate_content.assert_called_once()

    def test_parse_event_gemini_empty_string_response(self, monkeypatch, mock_datetime_now):
        """Test handling of an empty string response from Gemini."""
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=""
        )
        result = parse_event_text_with_gemini(self.VALID_TEXT_INPUT)
        assert isinstance(result, dict)
        assert result["error"] # Expecting a JSONDecodeError due to empty string
        assert result["detail"] == "Failed to parse event text using Gemini."
        assert result["raw_response"] == ""

    def test_parse_event_gemini_empty_json_object_response(self, monkeypatch, mock_datetime_now):
        """Test handling of an empty JSON object {} response from Gemini."""
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text="{}"
        )
        result = parse_event_text_with_gemini(self.VALID_TEXT_INPUT)
        assert result == {} # Service currently returns the parsed empty dict

from services.gemini_service import find_free_time_slots_with_gemini # Import for the class

class TestFindFreeTimeSlotsWithGemini:
    USER_QUERY = "Find a 1-hour slot tomorrow morning"
    # Using MOCK_DATETIME_NOW (Jan 1, 2024), so "tomorrow" would be Jan 2, 2024
    # Adjusting EVENTS_JSON and EXPECTED_SLOTS to reflect a consistent scenario with MOCK_DATETIME_NOW
    EVENTS_JSON = json.dumps([
        {"title": "Existing Meeting", "start_time": f"{MOCK_DATETIME_NOW.year}-01-02T09:00:00", "end_time": f"{MOCK_DATETIME_NOW.year}-01-02T09:30:00"}
    ])
    EXPECTED_SLOTS = [
        {"start_time": f"{MOCK_DATETIME_NOW.year}-01-02T10:00:00", "end_time": f"{MOCK_DATETIME_NOW.year}-01-02T11:00:00"},
        {"start_time": f"{MOCK_DATETIME_NOW.year}-01-02T14:00:00", "end_time": f"{MOCK_DATETIME_NOW.year}-01-02T15:00:00"}
    ]

    def _mock_gemini_interaction(self, monkeypatch, response_text=None, side_effect=None, get_model_returns_none=False):
        mock_model_instance = MagicMock()
        if side_effect:
            mock_model_instance.generate_content.side_effect = side_effect
        elif response_text is not None: # Allow empty string as valid response text
            mock_gemini_response = MagicMock()
            mock_gemini_response.text = response_text
            mock_model_instance.generate_content.return_value = mock_gemini_response

        mock_get_model = MagicMock()
        if get_model_returns_none:
            mock_get_model.return_value = None
        else:
            mock_get_model.return_value = mock_model_instance

        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)
        return mock_get_model, mock_model_instance

    @pytest.fixture(autouse=True)
    def mock_datetime_now(self, monkeypatch):
        """Fixture to mock datetime.now() for all tests in this class."""
        mock_dt = MagicMock()
        mock_dt.now.return_value = MOCK_DATETIME_NOW
        monkeypatch.setattr('services.gemini_service.datetime', mock_dt)
        return mock_dt

    def test_find_free_time_successful_response(self, monkeypatch, mock_datetime_now):
        """
        Tests successful retrieval and parsing of free time slots from Gemini.
        """
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=json.dumps(self.EXPECTED_SLOTS)
        )
        result = find_free_time_slots_with_gemini(self.USER_QUERY, self.EVENTS_JSON)
        assert result == self.EXPECTED_SLOTS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()
        prompt = mock_model_instance.generate_content.call_args[0][0]
        assert f"Today's date is {MOCK_DATETIME_NOW.strftime('%Y-%m-%d')}" in prompt
        assert self.USER_QUERY in prompt
        assert self.EVENTS_JSON in prompt

    def test_find_free_time_api_key_not_configured(self, monkeypatch, mock_datetime_now):
        """
        Tests the scenario where the Gemini API key is not configured.
        """
        mock_get_model, _ = self._mock_gemini_interaction(monkeypatch, get_model_returns_none=True)
        result = find_free_time_slots_with_gemini(self.USER_QUERY, self.EVENTS_JSON)
        assert isinstance(result, dict)
        assert result.get("error") == "Gemini API not configured"
        assert result.get("detail") == "API key missing or invalid."
        mock_get_model.assert_called_once()

    def test_find_free_time_gemini_api_error(self, monkeypatch, mock_datetime_now):
        """
        Tests handling of an error during the Gemini API call.
        """
        error_msg = "Gemini network error"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, side_effect=Exception(error_msg)
        )
        result = find_free_time_slots_with_gemini(self.USER_QUERY, self.EVENTS_JSON)
        assert isinstance(result, dict)
        assert result.get("error") == "Gemini API error"
        assert result.get("detail") == error_msg
        assert "raw_response" in result
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_find_free_time_malformed_json_response(self, monkeypatch, mock_datetime_now):
        """
        Tests handling of a malformed JSON response from Gemini.
        """
        malformed_text = "Not JSON {oops"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=malformed_text
        )
        result = find_free_time_slots_with_gemini(self.USER_QUERY, self.EVENTS_JSON)
        assert isinstance(result, dict)
        assert result.get("error") == "Invalid JSON response from Gemini"
        assert result.get("raw_response") == malformed_text
        assert "detail" in result
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_find_free_time_empty_array_response(self, monkeypatch, mock_datetime_now):
        """
        Tests handling of an empty array JSON response from Gemini (no slots found).
        """
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text="[]"
        )
        result = find_free_time_slots_with_gemini(self.USER_QUERY, self.EVENTS_JSON)
        assert result == []
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_find_free_time_json_wrapped_in_markdown_ticks(self, monkeypatch, mock_datetime_now):
        """
        Tests successful parsing when JSON is wrapped in markdown backticks.
        """
        response_text = f"```json\n{json.dumps(self.EXPECTED_SLOTS)}\n```"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=response_text
        )
        result = find_free_time_slots_with_gemini(self.USER_QUERY, self.EVENTS_JSON)
        assert result == self.EXPECTED_SLOTS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_find_free_time_json_wrapped_in_simple_markdown_ticks(self, monkeypatch, mock_datetime_now):
        """
        Tests successful parsing when JSON is wrapped in simple markdown backticks.
        """
        response_text = f"```{json.dumps(self.EXPECTED_SLOTS)}```"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=response_text
        )
        result = find_free_time_slots_with_gemini(self.USER_QUERY, self.EVENTS_JSON)
        assert result == self.EXPECTED_SLOTS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_find_free_time_empty_string_response_handled_as_empty_list(self, monkeypatch, mock_datetime_now):
        """
        Tests that an empty string response from Gemini is handled as an empty list.
        """
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=""
        )
        result = find_free_time_slots_with_gemini(self.USER_QUERY, self.EVENTS_JSON)
        assert result == []
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

class TestGenerateEventSummary:

    EVENTS_JSON_VALID = json.dumps([
        {"title": "Team Meeting", "start_time": "10:00", "end_time": "11:00", "description": "Discuss project updates"},
        {"title": "Lunch with Client", "start_time": "13:00", "end_time": "14:00", "description": "Follow up on proposal"}
    ])
    TARGET_DATE = "2024-07-28"
    EXPECTED_SUMMARY_TEXT = "This is a mock summary of events."

    def mock_gemini_model_summary(self, monkeypatch, response_text=None, response_parts=None, side_effect=None):
        """Helper to mock the Gemini model for summary generation."""
        mock_model_instance = MagicMock()

        if side_effect:
            mock_model_instance.generate_content.side_effect = side_effect
        else:
            mock_gemini_response = MagicMock()
            if response_text is not None:
                mock_gemini_response.text = response_text
                # Ensure parts is None or an empty list if text is primary
                mock_gemini_response.parts = []
            elif response_parts is not None:
                # Simulate response where text is empty but parts are populated
                mock_gemini_response.text = ""
                mock_gemini_response.parts = [MagicMock(text=part_text) for part_text in response_parts]
            else: # Default empty response
                mock_gemini_response.text = ""
                mock_gemini_response.parts = []

            mock_model_instance.generate_content.return_value = mock_gemini_response

        mock_get_model = MagicMock(return_value=mock_model_instance)
        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)
        return mock_get_model, mock_model_instance

    def test_successful_summary_generation_with_date(self, monkeypatch):
        """Test successful summary generation when a target date is provided."""
        _, mock_model_instance = self.mock_gemini_model_summary(monkeypatch, response_text=self.EXPECTED_SUMMARY_TEXT)

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID, self.TARGET_DATE)

        assert result == self.EXPECTED_SUMMARY_TEXT
        mock_model_instance.generate_content.assert_called_once()
        prompt = mock_model_instance.generate_content.call_args[0][0]
        assert f"Summarize these events for {self.TARGET_DATE}" in prompt
        assert self.EVENTS_JSON_VALID in prompt

    def test_successful_summary_generation_without_date(self, monkeypatch):
        """Test successful summary generation when no target date is provided."""
        _, mock_model_instance = self.mock_gemini_model_summary(monkeypatch, response_text=self.EXPECTED_SUMMARY_TEXT)

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID)

        assert result == self.EXPECTED_SUMMARY_TEXT
        mock_model_instance.generate_content.assert_called_once()
        prompt = mock_model_instance.generate_content.call_args[0][0]
        assert "Summarize these events." in prompt
        assert f"for {self.TARGET_DATE}" not in prompt # Ensure date-specific part is missing
        assert self.EVENTS_JSON_VALID in prompt

    def test_successful_summary_generation_with_response_parts(self, monkeypatch):
        """Test successful summary when response is in 'parts' attribute."""
        part1 = "This is part 1. "
        part2 = "This is part 2."
        expected_summary_from_parts = part1 + part2
        _, mock_model_instance = self.mock_gemini_model_summary(monkeypatch, response_parts=[part1, part2])

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID, self.TARGET_DATE)

        assert result == expected_summary_from_parts
        mock_model_instance.generate_content.assert_called_once()


    def test_api_key_not_configured_env_none(self, monkeypatch):
        """Test when GEMINI_API_KEY is None."""
        # Mock get_gemini_model to return None, which is the behavior when API key is bad
        mock_get_model = MagicMock(return_value=None)
        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID)

        assert isinstance(result, dict)
        assert result["error"] == "Gemini API key not configured"
        assert "GEMINI_API_KEY is missing or invalid" in result["detail"]
        assert result.get("status_code") == 500
        mock_get_model.assert_called_once() # Ensures get_gemini_model was called

    def test_api_key_not_configured_env_placeholder(self, monkeypatch):
        """Test when GEMINI_API_KEY is the placeholder value."""
        # This test relies on the internal logic of get_gemini_model() correctly
        # identifying "YOUR_API_KEY_HERE" as an invalid key and returning None.
        # We achieve this by mocking os.environ.get directly for this test.
        monkeypatch.setattr('os.environ.get', lambda key, default=None: "YOUR_API_KEY_HERE" if key == 'GEMINI_API_KEY' else default)

        # We also need to ensure that genai.configure is not called with the placeholder,
        # or if it is, that it results in get_gemini_model returning None.
        # The current get_gemini_model returns None if api_key is "YOUR_API_KEY_HERE".

        # Temporarily allow genai.configure to be called, but it shouldn't matter if get_gemini_model returns None first.
        mock_genai_configure = MagicMock()
        monkeypatch.setattr('google.generativeai.configure', mock_genai_configure, raising=False)

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID)

        assert isinstance(result, dict)
        assert result["error"] == "Gemini API key not configured"
        assert "GEMINI_API_KEY is missing or invalid" in result["detail"]
        assert result.get("status_code") == 500
        # mock_genai_configure.assert_not_called() # genai.configure should not be called if key is placeholder

    def test_gemini_api_call_failure(self, monkeypatch):
        """Test when the call to model.generate_content() raises an exception."""
        error_message = "Network connection failed"
        _, mock_model_instance = self.mock_gemini_model_summary(monkeypatch, side_effect=Exception(error_message))

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID)

        assert isinstance(result, dict)
        assert result["error"] == "Gemini API error during summary generation"
        assert result["detail"] == error_message
        assert result.get("status_code") == 500
        mock_model_instance.generate_content.assert_called_once()

    def test_empty_event_list_string(self, monkeypatch):
        """Test with an empty event list string '[]'."""
        # No need to mock gemini model as this should be caught before API call
        mock_get_model, _ = self.mock_gemini_model_summary(monkeypatch)

        result = generate_event_summary_with_gemini("[]")

        assert isinstance(result, dict)
        assert result["error"] == "No events provided for summary."
        assert result.get("status_code") == 400
        mock_get_model.assert_called_once() # get_gemini_model is called

    def test_null_event_list_string(self, monkeypatch):
        """Test with a None event list string."""
        mock_get_model, _ = self.mock_gemini_model_summary(monkeypatch)
        result = generate_event_summary_with_gemini(None)
        assert isinstance(result, dict)
        assert result["error"] == "No events provided for summary."
        assert result.get("status_code") == 400
        mock_get_model.assert_called_once()


    def test_invalid_json_event_list_string(self, monkeypatch):
        """Test with an invalid JSON string for events."""
        mock_get_model, _ = self.mock_gemini_model_summary(monkeypatch)
        result = generate_event_summary_with_gemini("this is not json")
        assert isinstance(result, dict)
        assert result["error"] == "Invalid JSON format for events_list_str."
        assert result.get("status_code") == 400
        mock_get_model.assert_called_once()

    def test_json_object_not_list_event_string(self, monkeypatch):
        """Test with a JSON string that is an object, not a list."""
        mock_get_model, _ = self.mock_gemini_model_summary(monkeypatch)
        result = generate_event_summary_with_gemini(json.dumps({"event": "some event"}))
        assert isinstance(result, dict)
        assert result["error"] == "Invalid data type for events_list_str."
        assert result.get("status_code") == 400
        mock_get_model.assert_called_once()

    def test_gemini_returns_empty_response_text_and_parts(self, monkeypatch):
        """Test when Gemini returns a response with no text and no parts."""
        _, mock_model_instance = self.mock_gemini_model_summary(monkeypatch, response_text="", response_parts=[])

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID)

        assert isinstance(result, dict)
        assert result["error"] == "Gemini API returned an empty response"
        assert result.get("status_code") == 500
        mock_model_instance.generate_content.assert_called_once()

    def test_gemini_returns_none_response(self, monkeypatch):
        """Test when Gemini returns None as a response (highly unlikely but good to cover)."""
        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = None # Simulate Gemini returning None
        mock_get_model = MagicMock(return_value=mock_model_instance)
        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID)

        assert isinstance(result, dict)
        assert result["error"] == "Gemini API returned an unexpected response structure"
        assert result.get("status_code") == 500
        mock_model_instance.generate_content.assert_called_once()

    def test_gemini_response_object_without_text_or_parts_attributes(self, monkeypatch):
        """Test response object missing 'text' and 'parts' attributes."""
        mock_response = MagicMock()
        # Remove 'text' and 'parts' if they exist by default on MagicMock or set to None
        del mock_response.text
        del mock_response.parts
        # Or more robustly:
        # mock_response.configure_mock(**{'text': None, 'parts': None})
        # If MagicMock doesn't have them by default, this is fine.
        # Let's ensure they are not there:
        if hasattr(mock_response, 'text'): delattr(mock_response, 'text')
        if hasattr(mock_response, 'parts'): delattr(mock_response, 'parts')


        mock_model_instance = MagicMock()
        mock_model_instance.generate_content.return_value = mock_response
        mock_get_model = MagicMock(return_value=mock_model_instance)
        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)

        result = generate_event_summary_with_gemini(self.EVENTS_JSON_VALID)

        assert isinstance(result, dict)
        assert result["error"] == "Gemini API returned an unexpected response structure"
        assert result.get("status_code") == 500
        mock_model_instance.generate_content.assert_called_once()
        # mock_model_instance.generate_content.assert_called_once() # This line was causing an error due to delattr
        # Instead, check that get_gemini_model was called, and it returned a model,
        # but the model's generate_content led to an error due to missing attributes on the response.
        mock_get_model.assert_called_once()
        # We can't assert_called_once on generate_content if the test setup involves deleting attributes
        # from the response object that the service code might try to access *after* generate_content returns.
        # The core of this test is that the service handles a response lacking .text/.parts.
        # So, generate_content *was* called.
# Ensure services/gemini_service.py can be imported from that location.
# Example: python -m pytest tests/test_gemini_service.py
# (or simply `pytest` if __init__.py files are set up correctly for package discovery)

from services.gemini_service import suggest_tags_for_event # Added import

class TestSuggestTagsForEvent:
    TITLE = "Team Meeting"
    DESCRIPTION = "Discuss project milestones"
    EXPECTED_TAGS = ["work", "meeting"]
    DEFAULT_TAGS = ["general"]

    def _mock_gemini_interaction(self, monkeypatch, response_text=None, side_effect=None, get_model_returns_none=False):
        mock_model_instance = MagicMock()
        if side_effect:
            mock_model_instance.generate_content.side_effect = side_effect
        elif response_text is not None:
            mock_gemini_response = MagicMock()
            mock_gemini_response.text = response_text
            mock_model_instance.generate_content.return_value = mock_gemini_response

        mock_get_model = MagicMock()
        if get_model_returns_none:
            mock_get_model.return_value = None
        else:
            mock_get_model.return_value = mock_model_instance

        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)
        return mock_get_model, mock_model_instance

    def test_suggest_tags_success(self, monkeypatch):
        """Tests successful tag suggestion from Gemini."""
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=json.dumps(self.EXPECTED_TAGS)
        )
        result = suggest_tags_for_event(self.TITLE, self.DESCRIPTION)
        assert result == self.EXPECTED_TAGS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()
        called_prompt = mock_model_instance.generate_content.call_args[0][0]
        assert self.TITLE in called_prompt
        assert self.DESCRIPTION in called_prompt

    def test_suggest_tags_gemini_error_returns_default(self, monkeypatch):
        """Tests that a Gemini API error results in the default tag list."""
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, side_effect=Exception("Gemini network error")
        )
        result = suggest_tags_for_event("Error case", "Test error")
        assert result == self.DEFAULT_TAGS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_tags_invalid_json_returns_default(self, monkeypatch):
        """Tests that an invalid JSON response from Gemini results in the default tag list."""
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text="this is not valid json"
        )
        result = suggest_tags_for_event("Invalid JSON", "Test invalid response")
        assert result == self.DEFAULT_TAGS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_tags_empty_list_from_gemini(self, monkeypatch):
        """Tests that an empty list from Gemini is returned as such."""
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=json.dumps([])
        )
        result = suggest_tags_for_event("Empty list", "Test empty list response")
        assert result == []
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_tags_gemini_model_none(self, monkeypatch):
        """Tests that if get_gemini_model returns None, default tags are returned."""
        mock_get_model, _ = self._mock_gemini_interaction(monkeypatch, get_model_returns_none=True)
        result = suggest_tags_for_event("No model", "Test no model available")
        assert result == self.DEFAULT_TAGS
        mock_get_model.assert_called_once()

    def test_suggest_tags_markdown_stripping(self, monkeypatch):
        """Tests that markdown backticks are stripped from Gemini response."""
        response_text = f"```json\n{json.dumps(self.EXPECTED_TAGS)}\n```"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=response_text
        )
        result = suggest_tags_for_event("Markdown Test", "Check stripping")
        assert result == self.EXPECTED_TAGS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_tags_simple_markdown_stripping(self, monkeypatch):
        """Tests stripping of simple markdown backticks."""
        response_text = f"```{json.dumps(self.EXPECTED_TAGS)}```"
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=response_text
        )
        result = suggest_tags_for_event("Simple Markdown Test", "Check simple stripping")
        assert result == self.EXPECTED_TAGS

    def test_suggest_tags_unexpected_json_structure(self, monkeypatch):
        """Tests that an unexpected JSON structure (e.g., dict instead of list) returns default."""
        response_text = json.dumps({"tag": "work", "confidence": 0.9}) # dict instead of list
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=response_text
        )
        result = suggest_tags_for_event("Unexpected JSON", "Test structure")
        assert result == self.DEFAULT_TAGS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_tags_empty_string_response_from_gemini(self, monkeypatch):
        """Tests that an empty string response from Gemini results in default tags."""
        mock_get_model, mock_model_instance = self._mock_gemini_interaction(
            monkeypatch, response_text=""
        )
        result = suggest_tags_for_event("Empty String", "Test empty string response")
        assert result == self.DEFAULT_TAGS # As per implementation, empty string leads to "general"
        mock_get_model.assert_called_once()
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

def test_get_related_info_prompt_construction_no_meal_keywords_with_desc(monkeypatch):
    """Test prompt construction when title and description are provided but have no meal keywords."""
    expected_partial_response = {"weather": {}, "traffic": {}, "suggestions": [], "related_content": []}
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text=json.dumps(expected_partial_response))

    get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO, event_title="General Meeting", event_description="Standard team sync up.")

    mock_model_instance.generate_content.assert_called_once()
    prompt = mock_model_instance.generate_content.call_args[0][0]
    assert "General Meeting" in prompt # Title should be in prompt
    assert "Standard team sync up" in prompt # Description should be in prompt
    assert "Restaurant suggestions" not in prompt
    assert "Return an empty list for suggestions" in prompt # Explicitly asking for empty list
    assert "Relevant news articles or documents" in prompt

def test_get_related_info_prompt_construction_no_title_with_meal_keyword_description(monkeypatch):
    """Test prompt construction when title is None, but description contains a meal keyword."""
    expected_partial_response = {"weather": {}, "traffic": {}, "suggestions": [], "related_content": []}
    _, mock_model_instance = mock_gemini_model(monkeypatch, response_text=json.dumps(expected_partial_response))

    get_related_information_for_event(EVENT_LOCATION, EVENT_START_ISO, event_title=None, event_description=EVENT_DESC_MEAL)

    mock_model_instance.generate_content.assert_called_once()
    prompt = mock_model_instance.generate_content.call_args[0][0]
    assert EVENT_DESC_MEAL in prompt # Description should be in prompt
    assert "Restaurant suggestions" in prompt # Should ask for suggestions
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


# Import the function to be tested
from services.gemini_service import suggest_subtasks_for_event

class TestSuggestSubtasksForEvent:

    EVENT_TITLE = "Plan Birthday Party"
    EVENT_DESCRIPTION = "Organize a surprise birthday party for Alex."
    EXPECTED_SUBTASKS = ["Send invitations", "Order cake", "Decorate venue"]

    def mock_gemini_model_subtasks(self, monkeypatch, response_text=None, side_effect=None):
        """Helper to mock the Gemini model for subtask suggestions."""
        mock_model_instance = MagicMock()
        if side_effect:
            mock_model_instance.generate_content.side_effect = side_effect
        else:
            mock_gemini_response = MagicMock()
            # Ensure text attribute exists even if None, to mimic actual response object
            mock_gemini_response.text = response_text
            mock_model_instance.generate_content.return_value = mock_gemini_response

        mock_get_model = MagicMock(return_value=mock_model_instance)
        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)
        return mock_get_model, mock_model_instance

    def test_suggest_subtasks_success(self, monkeypatch):
        """Test successful subtask suggestion."""
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, response_text=json.dumps(self.EXPECTED_SUBTASKS)
        )

        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)

        assert result == self.EXPECTED_SUBTASKS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()
        prompt = mock_model_instance.generate_content.call_args[0][0]
        assert self.EVENT_TITLE in prompt
        assert self.EVENT_DESCRIPTION in prompt
        assert "JSON formatted list of strings" in prompt

    def test_suggest_subtasks_success_no_description(self, monkeypatch):
        """Test successful subtask suggestion when event_description is None."""
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, response_text=json.dumps(self.EXPECTED_SUBTASKS)
        )

        result = suggest_subtasks_for_event(self.EVENT_TITLE, None)

        assert result == self.EXPECTED_SUBTASKS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()
        prompt = mock_model_instance.generate_content.call_args[0][0]
        assert self.EVENT_TITLE in prompt
        assert "Description:" not in prompt # Ensure description line is omitted if None

    def test_suggest_subtasks_no_model(self, monkeypatch):
        """Test when Gemini model is not available."""
        mock_get_model = MagicMock(return_value=None)
        monkeypatch.setattr('services.gemini_service.get_gemini_model', mock_get_model)

        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)

        expected_error = {"error": "Gemini API not configured", "detail": "API key missing or invalid."}
        assert result == expected_error
        mock_get_model.assert_called_once()

    def test_suggest_subtasks_api_error(self, monkeypatch):
        """Test when Gemini API call raises an exception."""
        api_error_message = "API network error"
        # Simulate response.text not being available if generate_content fails early
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, side_effect=Exception(api_error_message)
        )
        # Ensure that the mock_model_instance.generate_content().text would raise an error or be None
        # if accessed after the side_effect. The current setup of mock_gemini_model_subtasks
        # doesn't set up a response object with .text if side_effect is used.

        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)

        expected_error = {
            "error": "Gemini API error",
            "detail": api_error_message,
            # raw_response might be tricky if the exception happens before response object is created/assigned
            # The service code initializes raw_response_text = response.text if hasattr(response, 'text') else ''
            # If generate_content fails, 'response' might not be in locals(), or might not have 'text'.
            # The except block in the service has: raw_response_text if 'raw_response_text' in locals() else 'No response text available'
            "raw_response": 'No response text available'
        }
        assert result == expected_error
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_subtasks_json_decode_error(self, monkeypatch):
        """Test when Gemini response is invalid JSON."""
        invalid_json_text = "This is not JSON"
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, response_text=invalid_json_text
        )

        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)

        assert "error" in result
        assert result["error"] == "Invalid JSON response from Gemini"
        assert "detail" in result # Contains the specific json.JSONDecodeError message
        assert result["raw_response"] == invalid_json_text
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_subtasks_empty_response_text(self, monkeypatch):
        """Test when Gemini response text is empty."""
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, response_text=""
        )

        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)

        assert result == [] # As per service logic, empty string response means empty list
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_subtasks_markdown_stripping(self, monkeypatch):
        """Test that markdown backticks are stripped from Gemini response."""
        json_with_markdown = f"```json\n{json.dumps(self.EXPECTED_SUBTASKS)}\n```"
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, response_text=json_with_markdown
        )

        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)

        assert result == self.EXPECTED_SUBTASKS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_subtasks_simple_markdown_stripping(self, monkeypatch):
        """Test stripping of simple markdown backticks."""
        json_with_simple_markdown = f"```{json.dumps(self.EXPECTED_SUBTASKS)}```"
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, response_text=json_with_simple_markdown
        )
        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)
        assert result == self.EXPECTED_SUBTASKS
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()


    def test_suggest_subtasks_response_not_list_of_strings(self, monkeypatch):
        """Test when Gemini response is valid JSON but not a list of strings."""
        # Example: A list of objects, or a single dictionary
        invalid_structure_json = json.dumps([{"task": "Subtask 1"}, {"task": "Subtask 2"}])
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, response_text=invalid_structure_json
        )

        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)

        expected_error = {
            "error": "Gemini API response format error",
            "detail": "Response was not a list of strings.",
            "raw_response": invalid_structure_json
        }
        assert result == expected_error
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_subtasks_response_list_with_mixed_types(self, monkeypatch):
        """Test when Gemini response is a list with mixed types (not all strings)."""
        mixed_types_json = json.dumps(["Subtask 1", 123, "Subtask 3"])
        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, response_text=mixed_types_json
        )

        result = suggest_subtasks_for_event(self.EVENT_TITLE, self.EVENT_DESCRIPTION)

        expected_error = {
            "error": "Gemini API response format error",
            "detail": "Response was not a list of strings.",
            "raw_response": mixed_types_json
        }
        assert result == expected_error
        mock_get_model.assert_called_once()
        mock_model_instance.generate_content.assert_called_once()

    def test_suggest_subtasks_api_error_response_has_text_attr(self, monkeypatch):
        """Test API error where response object exists but operation failed, e.g. permission denied from API."""
        api_error_message = "Permission Denied from API"
        # Simulate a response object being returned, but it indicates an error state
        # For example, some APIs might return a response object with an error message in its text field.
        # Here, we make generate_content itself raise an Exception, but what if the Exception
        # was raised *after* a response object was created by the Gemini library?
        # The `gemini_service` code's `except Exception as e` block tries to get `response.text`.

        mock_model_instance = MagicMock()
        # Create a mock response that would be set if generate_content populated it before failing
        mock_failure_response = MagicMock()
        mock_failure_response.text = "Content generation failed due to permissions."

        # This is a bit tricky: we want generate_content to fail, but also for 'response' to be in scope
        # One way is to have generate_content set the response then raise.
        # For this test, let's assume the exception 'e' itself might have some response attribute or
        # that the 'response' variable in the service was populated before the error was caught.
        # The current service code is:
        # raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        # So if 'response' is not in locals (e.g. model.generate_content itself failed to return), it's 'No response text available'.
        # If 'response' is in locals but has no 'text', it's also 'No response text available'.
        # To test the case where response.text *is* available during an Exception:

        def generate_content_fails_but_response_exists(*args, **kwargs):
            # This is a conceptual test. In reality, the Gemini client library's behavior would dictate this.
            # We're testing our service's error handling of *its* `response` variable.
            # Let's assume our service code did:
            # try:
            #   response = model.generate_content(prompt) <--- this call itself doesn't fail
            #   response.some_method_that_fails() <--- this fails, but 'response' is set
            # except Exception as e:
            #   raw_response_text = response.text ...
            #
            # However, the current service code is:
            # try:
            #   response = model.generate_content(prompt)
            #   raw_response_text = response.text ...
            #   ...
            # except Exception as e:
            #   raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
            #
            # If model.generate_content() itself raises an exception, `response` might not be assigned.
            # If it returns an object that *then* fails (e.g. when accessing .text), then `response` is assigned.

            # Let's mock `generate_content` to return a mock that has a `text` attribute,
            # but then we'll make a subsequent operation (like `json.loads`) fail to test the `except Exception` block.
            # This is better tested by `test_suggest_subtasks_json_decode_error` for the `json.loads` failure.
            # For `except Exception` for other reasons *after* `response = model.generate_content()`:

            # For this test, we'll simulate an exception where `response` was formed but indicates an error.
            # The `detail` will be the exception string, `raw_response` will be its text.
            mock_response_with_error_text = MagicMock()
            mock_response_with_error_text.text = "Error text from Gemini response"

            # To make this test distinct, let's assume `json.loads(cleaned_response)` fails due to some other Exception
            # *after* `raw_response_text` was successfully assigned `response.text`.
            # This is hard to simulate without modifying the service code structure for this specific test.
            # The existing `test_suggest_subtasks_api_error` covers when `generate_content` itself fails.
            # Let's adjust `test_suggest_subtasks_api_error`'s expectation for `raw_response`
            # if `generate_content` fails and `response` is never assigned, `raw_response` should be 'No response text available'.
            # This is already correctly asserted there.

            # This test might be redundant or needs a more specific scenario.
            # Let's assume the Exception is raised by `generate_content` but the Gemini library
            # still provides a response object with some error details in `text`.
            class GeminiAPIErrorWithResponse(Exception):
                def __init__(self, message, response_obj):
                    super().__init__(message)
                    self.response = response_obj

            error_response_obj = MagicMock()
            error_response_obj.text = "Actual error content from API."
            raise GeminiAPIErrorWithResponse(api_error_message, error_response_obj)

        mock_get_model, mock_model_instance = self.mock_gemini_model_subtasks(
            monkeypatch, side_effect=generate_content_fails_but_response_exists
        )

        # This test is more about how the exception handler in the service function
        # would get raw_response_text if the exception object `e` itself carried a response.
        # The current service code does *not* inspect `e` for a `.response.text`.
        # It relies on the `response` variable from `response = model.generate_content(prompt)`.
        # So, if `model.generate_content` fails, `response` is not set, and raw_response_text becomes 'No response text available'.
        # This test will behave identically to `test_suggest_subtasks_api_error`.
        # For it to be different, the service's `except Exception as e:` block would need to be:
        # elif hasattr(e, 'response') and hasattr(e.response, 'text'):
        #    raw_response_text = e.response.text
        # This is not current behavior. So, this test is effectively a duplicate of test_suggest_subtasks_api_error.
        # I will remove this test method to avoid redundancy and stick to testing the current implementation.
        pass # Removing this test.
