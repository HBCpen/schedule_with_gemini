from flask_mail import Message
# To get app instance for app_context and config, and db instance
from app import mail, db, create_app as get_flask_app
from models.event import Event
from models.user import User
from datetime import datetime, timedelta

def send_event_reminders():
    current_app = get_flask_app() # Get a Flask app instance
    with current_app.app_context():
        now = datetime.utcnow()
        # Define a window for reminders: events starting from 10 mins ago to 1 hour from now.
        # This handles cases where the task might run slightly late.
        reminder_window_start = now - timedelta(minutes=10)
        reminder_window_end = now + timedelta(hours=1)

        # print(f"[{datetime.utcnow()}] Reminder Service: Current UTC time (now): {now}")
        # print(f"[{datetime.utcnow()}] Reminder Service: Calculated reminder_window_start: {reminder_window_start}")
        # print(f"[{datetime.utcnow()}] Reminder Service: Calculated reminder_window_end: {reminder_window_end}")

        # # Debug: Query a few events to see if test data is visible
        # try:
        #     all_events_in_db = Event.query.limit(5).all()
        #     if all_events_in_db:
        #         print(f"[{datetime.utcnow()}] Reminder Service: Found some events in DB ({len(all_events_in_db)}):")
        #         for ev_debug in all_events_in_db:
        #             print(f"  - ID: {ev_debug.id}, Title: {ev_debug.title}, Start: {ev_debug.start_time}, ReminderSent: {ev_debug.reminder_sent}")
        #     else:
        #         print(f"[{datetime.utcnow()}] Reminder Service: No events found with a simple limit(5) query.")
        # except Exception as e_debug:
        #     print(f"[{datetime.utcnow()}] Reminder Service: Debug query failed: {e_debug}")

        # print(f"[{datetime.utcnow()}] Checking for events between {reminder_window_start} and {reminder_window_end}")

        events_to_remind = Event.query.join(User).filter(
            Event.start_time >= reminder_window_start,
            Event.start_time <= reminder_window_end,
            Event.reminder_sent == False
        ).with_entities(Event, User.email).all()

        if not events_to_remind:
            print(f"[{datetime.utcnow()}] No events found needing reminders.")
            return "No events needing reminders."

        sent_count = 0
        for event, user_email in events_to_remind:
            try:
                msg = Message(
                    subject=f"Reminder: {event.title}",
                    recipients=[user_email],
                    body=f"Hello,\n\nThis is a reminder for your event:\n\nEvent: {event.title}\nStarts at: {event.start_time.strftime('%Y-%m-%d %H:%M')} UTC\nDescription: {event.description or 'N/A'}",
                    sender=current_app.config.get('MAIL_DEFAULT_SENDER')
                )
                mail.send(msg) # Actual sending is now UNCOMMENTED
                # print(f"Simulating email to {user_email} for event: '{event.title}' (ID: {event.id})") # Keep for now if needed, or remove
                event.reminder_sent = True
                db.session.add(event)
                sent_count += 1
            except Exception as e:
                print(f"Error sending reminder for event ID {event.id} to {user_email}: {e}")

        if sent_count > 0:
            db.session.commit()
            # print(f"Successfully sent {sent_count} reminders and updated their status in DB.") # Keep for now or remove

        return f"Processed {len(events_to_remind)} events. Sent {sent_count} reminders." # Adjusted return message
