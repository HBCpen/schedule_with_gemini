from models.event import Event
from app import db
from sqlalchemy import or_, and_
from datetime import datetime

def parse_datetime_flexible(dt_str):
    """
    Parses a datetime string in various common ISO formats.
    Handles presence or absence of 'Z' and milliseconds.
    """
    if not dt_str:
        return None
    # Remove 'Z' if present, as Python's fromisoformat handles UTC offset explicitly
    if dt_str.endswith('Z'):
        dt_str = dt_str[:-1] + '+00:00'

    common_formats = [
        '%Y-%m-%dT%H:%M:%S.%f%z',  # With milliseconds and timezone
        '%Y-%m-%dT%H:%M:%S%z',      # Without milliseconds, with timezone
        '%Y-%m-%dT%H:%M:%S.%f',    # With milliseconds, without timezone (naive)
        '%Y-%m-%dT%H:%M:%S',        # Without milliseconds, without timezone (naive)
        '%Y-%m-%d',                 # Date only
    ]

    for fmt in common_formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue

    # Fallback to fromisoformat for more general ISO 8601 parsing
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        return None


def search_events(user_id, query=None, start_date_str=None, end_date_str=None, tags_str=None):
    """
    Searches events based on keywords, date range, and tags.
    """
    filters = [Event.user_id == user_id]

    # Keyword search (title, description, location - assuming location is in description or a future field)
    if query:
        query_filter = or_(
            Event.title.ilike(f"%{query}%"),
            Event.description.ilike(f"%{query}%")
            # If location is a separate field: Event.location.ilike(f"%{query}%")
        )
        filters.append(query_filter)

    # Date range filter
    start_date = parse_datetime_flexible(start_date_str)
    end_date = parse_datetime_flexible(end_date_str)

    if start_date:
        filters.append(Event.start_time >= start_date) # Events starting on or after start_date
    if end_date:
        filters.append(Event.end_time <= end_date) # Events ending on or before end_date

    # Note: A more nuanced date range query might consider events that *overlap* with the range,
    # e.g., Event.start_time <= end_date and Event.end_time >= start_date.
    # For now, sticking to events fully within the range if both dates are given.
    # If only start_date is given, it finds events that start after it.
    # If only end_date is given, it finds events that end before it.

    # Tag search (assuming tags are stored as a comma-separated string in 'color_tag' or a dedicated 'tags' field)
    # For this example, we'll assume 'color_tag' might be used for a single tag.
    # If 'tags' is a list or a relationship, the query would be different (e.g., using 'any' or 'contains').
    if tags_str:
        # Assuming tags are comma-separated. For simplicity, we'll search if the color_tag is one of the provided tags.
        # A more robust solution would involve a separate Tags table or a JSONB field.
        individual_tags = [tag.strip() for tag in tags_str.split(',')]
        tag_filters = []
        for t in individual_tags:
            if t: # ensure no empty tags are processed
                tag_filters.append(Event.color_tag.ilike(f"%{t}%")) # Using color_tag for simplicity

        if tag_filters:
            filters.append(or_(*tag_filters))


    if not filters: # Should always have user_id filter at least
        return []

    print(f"Executing search with filters: {filters}") # For debugging

    events_query = Event.query.filter(and_(*filters))
    # For search, we typically don't expand all occurrences here unless specifically requested
    # and the date range for expansion is well-defined by the search parameters.
    # The current search_events will find the master recurring events if they match criteria.
    # Expansion is primarily for calendar/list views over a defined period.
    events = events_query.order_by(Event.start_time.asc()).all()

    return [event.to_dict() for event in events]


# --- Recurrence Expansion Logic ---
from dateutil import rrule
from dateutil.parser import isoparse # For parsing ISO strings from model to datetime
from datetime import timezone # For making datetimes timezone-aware

def get_events_in_range(user_id, start_date_str, end_date_str):
    """
    Fetches all events for a user within a given date range,
    expanding recurring events.
    """
    if not start_date_str or not end_date_str:
        # Or fetch all events if no range, though usually range is provided for calendar
        # For now, require range for expansion.
        # Fallback to fetching all non-expanded events for the user if desirable:
        # all_db_events = Event.query.filter_by(user_id=user_id, parent_event_id=None).order_by(Event.start_time.asc()).all()
        # return [event.to_dict() for event in all_db_events]
        return {"error": "Start and end date are required for fetching events with recurrence."}, 400


    query_start_dt = parse_datetime_flexible(start_date_str)
    query_end_dt = parse_datetime_flexible(end_date_str)

    if not query_start_dt or not query_end_dt:
        return {"error": "Invalid date format for start_date or end_date."}, 400

    # Make them timezone-aware if they are naive (assuming UTC if naive)
    # The database stores times in UTC.
    if query_start_dt.tzinfo is None:
        query_start_dt = query_start_dt.replace(tzinfo=timezone.utc)
    if query_end_dt.tzinfo is None:
        # For end date, consider it as end of the day for range inclusion
        query_end_dt = query_end_dt.replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)


    all_events_for_display = []

    # 1. Fetch non-recurring events and master recurring events (parent_event_id is None)
    #    that could potentially have occurrences in the range.
    #    A master event starting before query_end_dt could have occurrences in range.
    #    A non-recurring event must overlap with the query range.
    potential_events = Event.query.filter(
        Event.user_id == user_id,
        Event.parent_event_id.is_(None), # Master or non-recurring
        # Non-recurring must overlap: Event.start_time <= query_end_dt AND Event.end_time >= query_start_dt
        # Recurring masters: Event.start_time <= query_end_dt (rule will determine actual occurrences)
        or_(
            # Non-recurring events condition
            and_(Event.recurrence_rule.is_(None), Event.start_time <= query_end_dt, Event.end_time >= query_start_dt),
            # Master recurring events condition (their own start_time must be before or at the end of the query window)
            and_(Event.recurrence_rule.isnot(None), Event.start_time <= query_end_dt)
        )
    ).order_by(Event.start_time.asc()).all()

    for event in potential_events:
        if event.recurrence_rule:
            # Ensure event.start_time is timezone-aware (should be, as it's from DB)
            # If not, make it UTC: dtstart = event.start_time.replace(tzinfo=timezone.utc)
            dtstart = event.start_time
            if dtstart.tzinfo is None: # Should already be UTC from DB
                dtstart = dtstart.replace(tzinfo=timezone.utc)

            try:
                rule = rrule.rrulestr(event.recurrence_rule, dtstart=dtstart)
            except Exception as e:
                print(f"Error parsing RRULE for event {event.id}: {e}")
                # Add the master event itself if it falls in range, as rule is broken
                if event.start_time >= query_start_dt and event.end_time <= query_end_dt :
                    all_events_for_display.append(event.to_dict())
                continue

            # Generate occurrences within the query window
            # Note: rrule generates datetimes, ensure they are UTC like db times
            occurrences = rule.between(query_start_dt, query_end_dt, inc=True)

            event_duration = event.end_time - event.start_time

            for occ_start_utc in occurrences:
                # Ensure occurrence start time is UTC
                if occ_start_utc.tzinfo is None:
                     occ_start_utc = occ_start_utc.replace(tzinfo=timezone.utc)
                else:
                    occ_start_utc = occ_start_utc.astimezone(timezone.utc)

                occ_end_utc = occ_start_utc + event_duration

                # Double check if this specific occurrence is still within the precise query window
                # (esp. if event_duration is long, or rule generates something just outside due to dtstart)
                if occ_start_utc < query_end_dt and occ_end_utc > query_start_dt:
                    all_events_for_display.append(event.to_dict(
                        is_occurrence=True,
                        occurrence_start_time=occ_start_utc,
                        occurrence_end_time=occ_end_utc
                    ))
        else:
            # Standard non-recurring event, add if it's in range
            # This condition is already part of the SQL query for non-recurring events
            all_events_for_display.append(event.to_dict())

    # Sort all collected events by their actual start time
    all_events_for_display.sort(key=lambda x: isoparse(x['start_time']))

    return all_events_for_display
