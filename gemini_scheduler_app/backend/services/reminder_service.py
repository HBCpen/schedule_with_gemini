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

        print(f"[{datetime.utcnow()}] Checking for events between {reminder_window_start} and {reminder_window_end}")

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
                # mail.send(msg) # Actual sending is commented out for now
                print(f"Simulating email to {user_email} for event: '{event.title}' (ID: {event.id})")
                event.reminder_sent = True
                db.session.add(event)
                sent_count += 1
            except Exception as e:
                print(f"Error sending reminder for event ID {event.id} to {user_email}: {e}")

        if sent_count > 0:
            db.session.commit()
            print(f"Successfully sent {sent_count} reminders and updated their status in DB.")

        return f"Processed {len(events_to_remind)} events. Simulated sending {sent_count} reminders."
