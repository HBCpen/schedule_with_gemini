import google.generativeai as genai
import os
from datetime import datetime, timedelta # For potential date normalization
import json

# Note: Configuration of genai (genai.configure) will be done within get_gemini_model
# to ensure it uses the most current API key from the environment/config at the time of use.

def get_gemini_model():
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key or api_key == "YOUR_API_KEY_HERE": # Also check for placeholder
        print("Warning: GEMINI_API_KEY not found or is a placeholder in environment.")
        return None # Return None or raise error if key is essential for all calls

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-pro') # Or your preferred model
        return model
    except Exception as e:
        print(f"Error configuring Gemini API with key: {e}")
        return None


def parse_event_text_with_gemini(text_input):
    model = get_gemini_model()
    if not model:
        return {"error": "Gemini API not configured", "detail": "API key missing or invalid."}

    current_year = datetime.now().year
    # Note: For "tomorrow" or "next Monday", actual date calculation would require
    # knowing the current date when this function is called.
    # This can be added here or handled by the client before sending to Gemini.
    # For simplicity in this prompt, we are showing placeholders.
    # A more robust solution would calculate these dates before inserting into the prompt
    # or have Gemini explicitly state "tomorrow" and then the backend service converts it.

    prompt = f"""Extract event details from the following text.
Text: "{text_input}"

Today's year is {current_year}. Assume events are for the current year unless a different year is specified.
If a date is "tomorrow", calculate the actual date based on today being {datetime.now().strftime('%Y-%m-%d')}.
If a date is a day of the week like "next Monday", calculate the actual date based on today being {datetime.now().strftime('%Y-%m-%d')}. Assume "next" means the upcoming day of the week.
If a time is mentioned without AM/PM (e.g., "3 o'clock", "at 9"), infer AM/PM based on context (e.g., "meeting at 9" is likely 9 AM, "dinner at 7" is 7 PM). If ambiguous, prefer AM for times 8-11 and PM for 1-7.

Return the details as a JSON object with the following fields:
- "title": (string) The title of the event.
- "date": (string) The date of the event in "YYYY-MM-DD" format. If not specified, use today's date: {datetime.now().strftime('%Y-%m-%d')}.
- "start_time": (string) The start time in "HH:MM" (24-hour) format. If not specified, try to infer or leave null.
- "end_time": (string, optional) The end time in "HH:MM" (24-hour) format. If not specified, can be null or inferred (e.g. 1 hour after start_time if a typical meeting duration can be assumed).
- "description": (string, optional) Any additional details or notes.
- "location": (string, optional) The location of the event.

Example 1:
Text: "Meeting with Alex tomorrow at 3pm to discuss project Alpha at the main office"
Expected JSON structure (date for tomorrow needs to be calculated by you before putting in prompt if possible, or Gemini infers):
{{
  "title": "Meeting with Alex",
  "date": "YYYY-MM-DD (actual date for tomorrow)",
  "start_time": "15:00",
  "end_time": null,
  "description": "discuss project Alpha",
  "location": "main office"
}}

Example 2:
Text: "Dentist appointment next Tuesday at 10am"
Expected JSON structure (date for next Tuesday needs to be calculated):
{{
  "title": "Dentist appointment",
  "date": "YYYY-MM-DD (actual date for next Tuesday)",
  "start_time": "10:00",
  "end_time": null,
  "description": null,
  "location": null
}}

If you cannot extract some information, set the corresponding JSON field to null.
Provide only the JSON object in your response, without any surrounding text or markdown formatting like ```json ... ```.
"""
    try:
        # print(f"DEBUG: Sending prompt to Gemini: {prompt}")
        response = model.generate_content(prompt)
        # print(f"DEBUG: Raw Gemini Response: {response.text}")

        cleaned_response = response.text.strip()
        # Handle cases where Gemini might still wrap in markdown despite instructions
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
        elif cleaned_response.startswith("```"): # Less common but possible
             cleaned_response = cleaned_response[3:]
             if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

        parsed_json = json.loads(cleaned_response.strip())
        return parsed_json
    except Exception as e:
        raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        print(f"Error calling Gemini API or parsing response: {e}")
        # print(f"Failed prompt: {prompt}") # Be careful logging full prompts if they contain sensitive info
        print(f"Failed raw response: {raw_response_text}")
        return {"error": str(e), "detail": "Failed to parse event text using Gemini.", "raw_response": raw_response_text}


def find_free_time_slots_with_gemini(user_query: str, events_json: str):
    model = get_gemini_model()
    if not model:
        return {"error": "Gemini API not configured", "detail": "API key missing or invalid."}

    today_date_str = datetime.now().strftime('%Y-%m-%d')
    prompt = f"""
Analyze the user's request to find free time slots based on their current schedule.
User's request: "{user_query}"
User's current events (JSON format):
{events_json}

Today's date is {today_date_str}. Use this to resolve relative date queries like "tomorrow", "next Friday", etc.
Consider standard working hours (e.g., 9 AM to 6 PM) if the request is general (e.g., "afternoon") unless specified otherwise.
The free time slots should not overlap with any of the events in the provided schedule.
The duration of the free slots should align with the user's request if specified (e.g., "a 2-hour slot"). If no duration is specified, identify reasonable blocks of free time.

Return the available free time slots as a JSON array of objects. Each object in the array should have a "start_time" and "end_time", both in "YYYY-MM-DDTHH:MM:SS" ISO format.
If no suitable free time slots are found, return an empty JSON array: [].

Example of expected output for a query like "Find a 1-hour slot tomorrow morning":
[
  {{"start_time": "YYYY-MM-DDTHH:MM:SS (actual date and time for tomorrow morning slot 1)", "end_time": "YYYY-MM-DDTHH:MM:SS (1 hour after start_time)"}},
  {{"start_time": "YYYY-MM-DDTHH:MM:SS (actual date and time for tomorrow morning slot 2)", "end_time": "YYYY-MM-DDTHH:MM:SS (1 hour after start_time)"}}
]

Provide only the JSON array in your response, without any surrounding text or markdown formatting like ```json ... ```.
"""
    try:
        # print(f"DEBUG: Sending find_free_time prompt to Gemini: {prompt}") # Uncomment for debugging if needed
        response = model.generate_content(prompt)
        # print(f"DEBUG: Raw Gemini Response for find_free_time: {response.text}") # Uncomment for debugging

        cleaned_response = response.text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
        elif cleaned_response.startswith("```"):
             cleaned_response = cleaned_response[3:]
             if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

        # Gemini might return a plain list, or a string that needs to be parsed.
        # If it's already a list (less likely for text model), use it directly.
        # More likely, it's a string representation of a list.
        if not cleaned_response: # Handle empty string response
            return []

        parsed_json = json.loads(cleaned_response)
        return parsed_json
    except json.JSONDecodeError as e:
        raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        print(f"Error decoding JSON from Gemini for free time: {e}")
        print(f"Failed raw response: {raw_response_text}")
        return {{"error": "Invalid JSON response from Gemini", "detail": str(e), "raw_response": raw_response_text}}
    except Exception as e:
        raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        print(f"Error calling Gemini API or processing response for free time: {e}")
        # print(f"Failed prompt: {prompt}") # Be careful logging sensitive info
        print(f"Failed raw response: {raw_response_text}")
        return {{"error": "Gemini API error", "detail": str(e), "raw_response": raw_response_text}}


def suggest_tags_for_event(title: str, description: str):
    """
    Suggests relevant tags for an event based on its title and description using Gemini.
    """
    model = get_gemini_model()
    if not model:
        print("Error: Gemini API not configured. Cannot suggest tags.")
        return ["general"] # Default or empty list on configuration error

    prompt = f"""Analyze the following event details and suggest 1 to 3 relevant tags or categories.
Event Title: "{title}"
Event Description: "{description if description else 'No description provided.'}"

Consider common event categories like: "meeting", "work", "personal", "appointment", "reminder", "call", "errand", "project", "deadline", "social", "exercise", "health", "finance", "education", "travel", "hobby", "family".

Return your answer as a JSON array of strings. For example: ["work", "meeting"].
If no specific tags come to mind, you can return an empty array [] or a single tag like ["general"].
Provide only the JSON array in your response, without any surrounding text or markdown formatting like ```json ... ```.
"""

    try:
        # print(f"DEBUG: Sending tag suggestion prompt to Gemini: {prompt}")
        response = model.generate_content(prompt)
        # print(f"DEBUG: Raw Gemini Response for tags: {response.text}")

        cleaned_response = response.text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:] # Remove ```json\n
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3] # Remove ```
        elif cleaned_response.startswith("```"): # Less common but possible
             cleaned_response = cleaned_response[3:] # Remove ```
             if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3] # Remove ```

        if not cleaned_response: # Handle empty string response from Gemini
            print("Warning: Received empty response from Gemini for tag suggestion.")
            return ["general"]

        tags = json.loads(cleaned_response)
        if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
            return tags
        else:
            print(f"Warning: Gemini response for tags was not a list of strings: {tags}")
            return ["general"] # Fallback for unexpected structure

    except json.JSONDecodeError as e:
        raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        print(f"Error decoding JSON from Gemini for tag suggestion: {e}")
        print(f"Failed raw response for tags: {raw_response_text}")
        return ["general"] # Fallback for JSON parsing error
    except Exception as e:
        raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        print(f"Error calling Gemini API or processing response for tag suggestion: {e}")
        # print(f"Failed prompt for tags: {prompt}") # Be careful logging sensitive info
        print(f"Failed raw response for tags: {raw_response_text}")
        return ["general"] # Fallback for other API errors


def suggest_subtasks_for_event(event_title: str, event_description: str = None):
    """
    Suggests 3-5 actionable subtasks for a given event using the Gemini API.
    """
    model = get_gemini_model()
    if not model:
        return {"error": "Gemini API not configured", "detail": "API key missing or invalid."}

    prompt_lines = [
        "Given the following event:",
        f"Title: {event_title}"
    ]
    if event_description:
        prompt_lines.append(f"Description: {event_description}")

    prompt_lines.extend([
        "Please suggest 3 to 5 actionable subtasks or steps to prepare for or complete this event.",
        "Return your suggestions as a JSON formatted list of strings, like:",
        '["Subtask 1", "Subtask 2", "Subtask 3"]',
        "Provide only the JSON array in your response, without any surrounding text or markdown."
    ])
    prompt = "\n".join(prompt_lines)

    try:
        # print(f"DEBUG: Sending subtask suggestion prompt to Gemini: {prompt}")
        response = model.generate_content(prompt)
        # print(f"DEBUG: Raw Gemini Response for subtasks: {response.text}")

        raw_response_text = response.text if hasattr(response, 'text') else ''
        cleaned_response = raw_response_text.strip()

        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:] # Remove ```json\n
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3] # Remove ```
        elif cleaned_response.startswith("```"):
             cleaned_response = cleaned_response[3:] # Remove ```
             if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3] # Remove ```

        cleaned_response = cleaned_response.strip() # Ensure no leading/trailing whitespace after markdown removal

        if not cleaned_response:
            # print("Warning: Received empty response from Gemini for subtask suggestion.")
            return []

        subtasks = json.loads(cleaned_response)
        if isinstance(subtasks, list) and all(isinstance(task, str) for task in subtasks):
            return subtasks
        else:
            # print(f"Warning: Gemini response for subtasks was not a list of strings: {subtasks}")
            # Consider returning an error or trying to salvage, for now, error out
            return {"error": "Gemini API response format error", "detail": "Response was not a list of strings.", "raw_response": raw_response_text}

    except json.JSONDecodeError as e:
        # print(f"Error decoding JSON from Gemini for subtask suggestion: {e}")
        # print(f"Failed raw response for subtasks: {raw_response_text}")
        return {"error": "Invalid JSON response from Gemini", "detail": str(e), "raw_response": raw_response_text}
    except Exception as e:
        # print(f"Error calling Gemini API or processing response for subtask suggestion: {e}")
        # print(f"Failed prompt for subtasks: {prompt}")
        # print(f"Failed raw response for subtasks: {raw_response_text}")
        return {"error": "Gemini API error", "detail": str(e), "raw_response": raw_response_text if 'raw_response_text' in locals() else 'No response text available'}


def get_related_information_for_event(event_location: str, event_start_datetime_iso: str, event_title: str = None, event_description: str = None):
    """
    Retrieves weather, traffic, and optionally restaurant suggestions for a given event.
    """
    model = get_gemini_model()
    if not model:
        return {"error": "Gemini API not configured", "detail": "API key missing or invalid."}

    try:
        event_dt = datetime.fromisoformat(event_start_datetime_iso.replace("Z", "+00:00"))
        event_date_str = event_dt.strftime('%Y-%m-%d')
        event_time_str = event_dt.strftime('%H:%M')
    except ValueError as e:
        return {"error": "Invalid ISO format for event_start_datetime_iso", "detail": str(e)}

    # Construct the core prompt
    prompt_lines = [
        f"For an event at '{event_location}' on {event_date_str} around {event_time_str}, provide:",
        "- Weather forecast: general condition, high/low temperature, precipitation chance, and a brief summary.",
        "- Traffic overview: congestion level and a travel advisory/summary for the time around the event.",
        "- Relevant news articles or documents related to the event's title or description (if provided). If found, return these as a list under a 'related_content' key. Each item should be an object with 'type' (e.g., 'article', 'document'), 'title', 'source' (if available), and 'url' or 'summary'. If none found, 'related_content' should be an empty list []."
    ]

    # Optional: Add restaurant suggestions if title or description hint at a meal
    meal_keywords = ["lunch", "dinner", "breakfast", "brunch", "meal", "restaurant", "cafe", "food", "eat"]
    ask_for_suggestions = False
    if event_title and any(keyword in event_title.lower() for keyword in meal_keywords):
        ask_for_suggestions = True
    if not ask_for_suggestions and event_description and any(keyword in event_description.lower() for keyword in meal_keywords):
        ask_for_suggestions = True

    if ask_for_suggestions:
        prompt_lines.append("- Restaurant suggestions: 1-2 nearby places suitable for the event. Include name and brief details.")
    else:
        # Ensure the JSON structure still expects 'suggestions' as an empty list
        prompt_lines.append("- Suggestions: Return an empty list for suggestions as they were not requested or applicable.")


    prompt_lines.append("\nReturn the information as a single JSON object with keys: 'weather', 'traffic', 'suggestions', and 'related_content'.")
    prompt_lines.append("The 'weather' object should contain: 'forecast_date', 'location', 'condition', 'temperature_high', 'temperature_low', 'precipitation_chance', 'summary'.")
    prompt_lines.append("The 'traffic' object should contain: 'location', 'assessment_time', 'congestion_level', 'expected_travel_advisory', 'summary'.")
    prompt_lines.append("The 'suggestions' key should hold a list of objects, each with 'type', 'name', and 'details'. If no suggestions are applicable or found, it should be an empty list [].")
    prompt_lines.append("The 'related_content' key should hold a list of objects, each with 'type', 'title', 'source', and 'url' (or 'summary'). If none found, it should be an empty list [].")
    prompt_lines.append("Provide only the JSON object in your response, without any surrounding text or markdown formatting like ```json ... ```.")

    prompt = "\n".join(prompt_lines)

    try:
        # print(f"DEBUG: Sending get_related_information_for_event prompt to Gemini: {prompt}")
        response = model.generate_content(prompt)
        # print(f"DEBUG: Raw Gemini Response: {response.text}")

        cleaned_response = response.text.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
        elif cleaned_response.startswith("```"):
             cleaned_response = cleaned_response[3:]
             if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

        if not cleaned_response:
             return {"error": "Empty response from Gemini", "detail": "Received no content."}

        parsed_json = json.loads(cleaned_response.strip())

        # Basic validation for expected keys, can be expanded
        if not all(k in parsed_json for k in ["weather", "traffic", "suggestions", "related_content"]):
            # print(f"Warning: Gemini response missing some top-level keys. Got: {parsed_json.keys()}")
            # Attempt to return what we got, or a more specific error
            return {"error": "Malformed response from Gemini", "detail": "Missing one or more top-level keys: 'weather', 'traffic', 'suggestions', 'related_content'.", "raw_response": parsed_json}

        if not isinstance(parsed_json.get("suggestions"), list):
            # print(f"Warning: 'suggestions' field is not a list. Attempting to correct or defaulting to empty list.")
            parsed_json["suggestions"] = [] # Default to empty list if not a list

        if not isinstance(parsed_json.get("related_content"), list):
            # print(f"Warning: 'related_content' field is not a list. Attempting to correct or defaulting to empty list.")
            parsed_json["related_content"] = [] # Default to empty list if not a list


        return parsed_json

    except json.JSONDecodeError as e:
        raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        print(f"Error decoding JSON from Gemini for event information: {e}")
        print(f"Failed raw response: {raw_response_text}")
        return {"error": "Invalid JSON response from Gemini", "detail": str(e), "raw_response": raw_response_text}
    except Exception as e:
        raw_response_text = response.text if 'response' in locals() and hasattr(response, 'text') else 'No response text available'
        print(f"Error calling Gemini API or processing response for event information: {e}")
        # print(f"Failed prompt: {prompt}") # Be careful logging sensitive info
        print(f"Failed raw response: {raw_response_text}")
        return {"error": "Gemini API error", "detail": str(e), "raw_response": raw_response_text}


def generate_event_summary_with_gemini(events_list_str: str, target_date_str: str = None):
    """
    Generates a concise, natural-language summary of events using the Gemini API.
    Focuses on a target_date_str if provided.
    """
    model = get_gemini_model()
    if not model:
        return {"error": "Gemini API key not configured", "detail": "GEMINI_API_KEY is missing or invalid in environment variables.", "status_code": 500}

    try:
        # Validate events_list_str
        if not events_list_str or events_list_str.strip() == "[]":
            return {"error": "No events provided for summary.", "detail": "The events list string is empty or contains no events.", "status_code": 400}

        # Basic validation that events_list_str is a valid JSON string representing a list
        try:
            events_test = json.loads(events_list_str)
            if not isinstance(events_test, list):
                raise ValueError("events_list_str is not a JSON list")
        except json.JSONDecodeError:
            return {"error": "Invalid JSON format for events_list_str.", "detail": "The provided events string is not valid JSON.", "status_code": 400}
        except ValueError: # Catches the custom ValueError from above
             return {"error": "Invalid data type for events_list_str.", "detail": "The provided events string is not a JSON list.", "status_code": 400}


        if target_date_str:
            prompt = f"Summarize these events for {target_date_str}. What are the key activities? Keep the summary concise and in natural language.\nEvents:\n{events_list_str}"
        else:
            prompt = f"Summarize these events. What are the key activities? Keep the summary concise and in natural language.\nEvents:\n{events_list_str}"

        # print(f"DEBUG: Sending summary prompt to Gemini: {prompt}")
        response = model.generate_content(prompt)

        if response and hasattr(response, 'text') and response.text:
            return response.text.strip()
        elif response and hasattr(response, 'parts') and response.parts:
             # Handle cases where response.text might be empty but parts exist
            all_text_parts = "".join([part.text for part in response.parts if hasattr(part, 'text')])
            if all_text_parts:
                return all_text_parts.strip()
            else: # If no text in parts either
                # print(f"Warning: Gemini response for summary was empty or had no text content. Prompt: {prompt}")
                return {"error": "Gemini API returned an empty response", "detail": "The API generated no text content for the summary.", "status_code": 500}
        else:
            # print(f"Warning: Gemini response for summary was empty or malformed. Prompt: {prompt}")
            return {"error": "Gemini API returned an unexpected response structure", "detail": "The API response did not contain the expected text data.", "status_code": 500}

    except Exception as e:
        # print(f"Error calling Gemini API for summary: {e}")
        # print(f"Failed prompt for summary: {prompt}") # Be careful with sensitive data in logs
        raw_response_text = getattr(e, 'response', {}).get('text', 'No direct response text in exception.')
        # It's also good to check if the exception itself has useful details if it's a google.api_core.exceptions type
        # For example, e.message or str(e) might be more informative for API errors.
        error_detail = str(e)
        if hasattr(e, 'message'): # some google exceptions have a message attribute
            error_detail = e.message

        return {"error": "Gemini API error during summary generation", "detail": error_detail, "raw_response": raw_response_text, "status_code": 500}
