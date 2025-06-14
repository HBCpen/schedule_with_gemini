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
        "- Traffic overview: congestion level and a travel advisory/summary for the time around the event."
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


    prompt_lines.append("\nReturn the information as a single JSON object with keys: 'weather', 'traffic', and 'suggestions'.")
    prompt_lines.append("The 'weather' object should contain: 'forecast_date', 'location', 'condition', 'temperature_high', 'temperature_low', 'precipitation_chance', 'summary'.")
    prompt_lines.append("The 'traffic' object should contain: 'location', 'assessment_time', 'congestion_level', 'expected_travel_advisory', 'summary'.")
    prompt_lines.append("The 'suggestions' key should hold a list of objects, each with 'type', 'name', and 'details'. If no suggestions are applicable or found, it should be an empty list [].")
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
        if not all(k in parsed_json for k in ["weather", "traffic", "suggestions"]):
            # print(f"Warning: Gemini response missing some top-level keys. Got: {parsed_json.keys()}")
            # Attempt to return what we got, or a more specific error
            return {"error": "Malformed response from Gemini", "detail": "Missing one or more top-level keys: 'weather', 'traffic', 'suggestions'.", "raw_response": parsed_json}

        if not isinstance(parsed_json.get("suggestions"), list):
            # print(f"Warning: 'suggestions' field is not a list. Attempting to correct or defaulting to empty list.")
            parsed_json["suggestions"] = [] # Default to empty list if not a list

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
