from flask import Blueprint, request, jsonify
from models.event import Event
from models.user import User
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
import os
import json
from services import gemini_service
# Updated to import event_service module
from services import event_service

# Changed url_prefix to be the full path from /api
event_bp = Blueprint('event_bp', __name__, url_prefix='/api/events')

# Helper to parse datetime strings
def parse_datetime(dt_str):
    if not dt_str:
        return None
    if dt_str.endswith('Z'):
        dt_str = dt_str[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        try:
            return datetime.strptime(dt_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
        except:
            return None


@event_bp.route('', methods=['POST'])
@jwt_required()
def create_event():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    title = data.get('title')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    description = data.get('description')
    # color_tag will be set by Gemini service
    recurrence_rule = data.get('recurrence_rule') # New field

    if not title or not start_time_str or not end_time_str:
        return jsonify({"msg": "Title, start time, and end time are required"}), 400

    start_time = parse_datetime(start_time_str)
    end_time = parse_datetime(end_time_str)

    if not start_time or not end_time:
        return jsonify({"msg": "Invalid datetime format. Use ISO format e.g., YYYY-MM-DDTHH:MM:SS.sssZ or YYYY-MM-DDTHH:MM:SS"}), 400

    if end_time < start_time:
        return jsonify({"msg": "End time cannot be before start time"}), 400

    new_event = Event(
        title=title,
        start_time=start_time,
        end_time=end_time,
        description=description,
        color_tag=None, # Will be updated by Gemini
        user_id=current_user_id,
        recurrence_rule=recurrence_rule # New field
    )

    # Suggest and set tags
    try:
        tags_list = gemini_service.suggest_tags_for_event(new_event.title, new_event.description)
        if tags_list:
            new_event.color_tag = ",".join(tags_list)
        else:
            new_event.color_tag = "" # Explicitly set to empty if no tags suggested
    except Exception as e:
        print(f"Error suggesting tags for new event: {e}")
        # Optionally, set a default tag or leave it None/empty
        new_event.color_tag = "" # Or some default like "general"

    db.session.add(new_event)
    db.session.commit()
    return jsonify(new_event.to_dict()), 201

@event_bp.route('', methods=['GET'])
@jwt_required()
def get_events():
    current_user_id = get_jwt_identity()
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Defer to the event_service to get events, including expanded recurring ones
    # The service will handle parsing dates and applying logic.
    service_response = event_service.get_events_in_range(
        user_id=current_user_id,
        start_date_str=start_date_str,
        end_date_str=end_date_str
    )

    # The service function get_events_in_range might return a tuple (data, status_code)
    # or just data if it's always 200 on success.
    # Based on its current implementation, it returns a list of events (success)
    # or a dict with an error message and a status code (e.g. `{"error": "msg"}, 400`)
    # For simplicity, assuming it now returns a list for success, and error dict for failure.

    if isinstance(service_response, dict) and 'error' in service_response:
        status_code = service_response.get('status_code', 400) # get status_code if provided, else default 400
        return jsonify({"msg": service_response["error"]}), status_code

    return jsonify(service_response), 200

@event_bp.route('/<int:event_id>', methods=['GET'])
@jwt_required()
def get_event(event_id):
    current_user_id = get_jwt_identity()
    event = Event.query.filter_by(id=event_id, user_id=current_user_id).first()
    if not event:
        return jsonify({"msg": "Event not found or access denied"}), 404
    return jsonify(event.to_dict()), 200

@event_bp.route('/<int:event_id>', methods=['PUT'])
@jwt_required()
def update_event(event_id):
    current_user_id = get_jwt_identity()
    event = Event.query.filter_by(id=event_id, user_id=current_user_id).first()
    if not event:
        return jsonify({"msg": "Event not found or access denied"}), 404

    data = request.get_json()
    event.title = data.get('title', event.title)

    start_time_str = data.get('start_time')
    if start_time_str:
        parsed_start = parse_datetime(start_time_str)
        if not parsed_start:
             return jsonify({"msg": "Invalid start_time format"}), 400
        event.start_time = parsed_start

    end_time_str = data.get('end_time')
    if end_time_str:
        parsed_end = parse_datetime(end_time_str)
        if not parsed_end:
             return jsonify({"msg": "Invalid end_time format"}), 400
        event.end_time = parsed_end

    if event.end_time < event.start_time:
        return jsonify({"msg": "End time cannot be before start time"}), 400

    # Update description and title before tag suggestion
    event.description = data.get('description', event.description)
    event.title = data.get('title', event.title) # Ensure title is updated if provided

    # Suggest and set tags based on potentially updated title/description
    try:
        current_title = event.title # Already updated from data.get('title', event.title)
        current_description = event.description # Already updated
        tags_list = gemini_service.suggest_tags_for_event(current_title, current_description)
        if tags_list:
            event.color_tag = ",".join(tags_list)
        else:
            event.color_tag = "" # Explicitly set to empty if no tags suggested
    except Exception as e:
        print(f"Error suggesting tags for updated event {event.id}: {e}")
        # Decide on fallback: keep old tags, clear them, or set a default.
        # For now, if an error occurs, we are not changing existing tags.
        # If specific behavior like clearing or setting default is needed, uncomment below:
        # event.color_tag = "" # Or some default like "general"
        pass # Keep existing tags if an error occurs during suggestion

    event.recurrence_rule = data.get('recurrence_rule', event.recurrence_rule) # New field

    # If recurrence_rule is being cleared, or if it's a simple update to a non-recurring event,
    # ensure parent_event_id is None.
    # More complex logic for "this and future instances" would go here or in the service layer.
    if not event.recurrence_rule:
        event.parent_event_id = None

    db.session.commit()
    return jsonify(event.to_dict()), 200

@event_bp.route('/<int:event_id>', methods=['DELETE'])
@jwt_required()
def delete_event(event_id):
    current_user_id = get_jwt_identity()
    event = Event.query.filter_by(id=event_id, user_id=current_user_id).first()
    if not event:
        return jsonify({"msg": "Event not found or access denied"}), 404

    db.session.delete(event)
    db.session.commit()
    return jsonify({"msg": "Event deleted successfully"}), 200

@event_bp.route('/parse-natural-language', methods=['POST'])
@jwt_required()
def parse_natural_language_event():
    data = request.get_json()
    text_input = data.get('text')

    if not text_input:
        return jsonify({"msg": "Text input is required"}), 400

    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key or gemini_api_key == "YOUR_API_KEY_HERE":
         return jsonify({"msg": "Gemini API key not configured on the server."}), 503

    try:
        parsed_data = gemini_service.parse_event_text_with_gemini(text_input)
        if parsed_data.get("error"):
            print(f"Gemini service returned an error: {parsed_data.get('detail')}")
            return jsonify({"msg": "Error parsing event with Gemini", "detail": parsed_data.get("detail", "Unknown error from service")}), 500
        return jsonify(parsed_data), 200
    except Exception as e:
        print(f"Unexpected error in /parse-natural-language endpoint: {e}")
        return jsonify({"msg": "An unexpected error occurred during parsing."}), 500


@event_bp.route('/find-free-time', methods=['POST'])
@jwt_required()
def find_free_time_api():
    current_user_id = get_jwt_identity()
    data = request.get_json()

    natural_language_query = data.get('query')
    if not natural_language_query:
        return jsonify({"msg": "Natural language query ('query') is required in the request body"}), 400

    gemini_api_key = os.environ.get('GEMINI_API_KEY')
    if not gemini_api_key or gemini_api_key == "YOUR_API_KEY_HERE":
         return jsonify({"msg": "Gemini API key not configured on the server."}), 503

    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    if start_date_str:
        start_date = parse_datetime(start_date_str)
        if not start_date:
            return jsonify({"msg": "Invalid start_date format. Use ISO format."}), 400
    else:
        start_date = datetime.utcnow()

    if end_date_str:
        end_date = parse_datetime(end_date_str)
        if not end_date:
            return jsonify({"msg": "Invalid end_date format. Use ISO format."}), 400
    else:
        end_date = start_date + timedelta(days=7)

    if end_date < start_date:
        return jsonify({"msg": "end_date cannot be before start_date"}), 400

    try:
        user_events = Event.query.filter(
            Event.user_id == current_user_id,
            Event.start_time >= start_date,
            Event.start_time <= end_date
        ).order_by(Event.start_time).all()
    except Exception as e:
        print(f"Database error fetching events: {e}")
        return jsonify({"msg": "Error fetching user events"}), 500

    events_list_for_gemini = []
    for event_obj in user_events:
        event_dict = event_obj.to_dict()
        if isinstance(event_dict.get('start_time'), datetime):
             event_dict['start_time'] = event_dict['start_time'].isoformat()
        if isinstance(event_dict.get('end_time'), datetime):
             event_dict['end_time'] = event_dict['end_time'].isoformat()
        events_list_for_gemini.append({
            "title": event_dict.get("title"),
            "start_time": event_dict.get("start_time"),
            "end_time": event_dict.get("end_time")
        })

    events_json_string = json.dumps(events_list_for_gemini)

    try:
        suggested_slots = gemini_service.find_free_time_slots_with_gemini(
            user_query=natural_language_query,
            events_json=events_json_string
        )

        if isinstance(suggested_slots, dict) and suggested_slots.get("error"):
            error_detail = suggested_slots.get("detail", "Unknown error from Gemini service")
            if "Gemini API not configured" in suggested_slots.get("error", ""):
                 return jsonify({"msg": "Error with Gemini API configuration", "detail": error_detail}), 503
            print(f"Gemini service returned an error for free time search: {error_detail}")
            raw_response = suggested_slots.get("raw_response")
            return jsonify({"msg": "Error finding free time slots with Gemini", "detail": error_detail, "raw_response": raw_response}), 500

        return jsonify(suggested_slots), 200

    except Exception as e:
        print(f"Unexpected error in /find-free-time endpoint: {e}")
        return jsonify({"msg": "An unexpected error occurred while finding free time."}), 500

@event_bp.route('/search', methods=['GET'])
@jwt_required()
def search_events_api():
    current_user_id = get_jwt_identity()
    query = request.args.get('q')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    tags_str = request.args.get('tags') # Expecting comma-separated string like "work,personal"

    # Validate date formats (basic validation, more can be added in service)
    # The service's parse_datetime_flexible will handle more complex validation for search as well
    # No need for redundant validation here if service handles it.
    # However, keeping basic format checks can be a quick feedback mechanism.
    # For now, let's assume event_service.search_events also has robust date parsing or relies on parse_datetime_flexible

    try:
        results = event_service.search_events( # Call using event_service module
            user_id=current_user_id,
            query=query,
            start_date_str=start_date_str,
            end_date_str=end_date_str,
            tags_str=tags_str
        )
        return jsonify(results), 200
    except Exception as e:
        # Log the exception for debugging
        print(f"Error during event search: {e}")
        return jsonify({"msg": "An error occurred during the search."}), 500
