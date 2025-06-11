from flask import Blueprint, request, jsonify
from models.event import Event
from models.user import User
from app import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import os
from services import gemini_service

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
    color_tag = data.get('color_tag')

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
        color_tag=color_tag,
        user_id=current_user_id
    )
    db.session.add(new_event)
    db.session.commit()
    return jsonify(new_event.to_dict()), 201

@event_bp.route('', methods=['GET'])
@jwt_required()
def get_events():
    current_user_id = get_jwt_identity()
    events = Event.query.filter_by(user_id=current_user_id).order_by(Event.start_time.asc()).all()
    return jsonify([event.to_dict() for event in events]), 200

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

    event.description = data.get('description', event.description)
    event.color_tag = data.get('color_tag', event.color_tag)

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
