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
