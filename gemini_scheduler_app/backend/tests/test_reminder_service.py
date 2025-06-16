import unittest
from unittest.mock import patch, MagicMock, ANY
from datetime import datetime, timedelta

# Assuming models and app structure
from gemini_scheduler_app.backend.models import Event as EventModel, User as UserModel
from gemini_scheduler_app.backend.services import reminder_service

class TestReminderService(unittest.TestCase):

    @patch('gemini_scheduler_app.backend.services.reminder_service.get_flask_app')
    @patch('gemini_scheduler_app.backend.services.reminder_service.db')
    @patch('gemini_scheduler_app.backend.services.reminder_service.mail') # Even if commented out, good to have if it becomes active
    @patch('gemini_scheduler_app.backend.services.reminder_service.datetime')
    def test_send_event_reminders_events_found(
        self, mock_datetime, mock_mail, mock_db, mock_get_flask_app
    ):
        # --- Setup Mocks ---
        # Mock Flask App and App Context
        mock_app = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = None # Mock context manager
        mock_app.app_context.return_value.__exit__.return_value = None
        mock_app.config = {'MAIL_DEFAULT_SENDER': 'test@example.com'}
        mock_get_flask_app.return_value = mock_app

        # Mock datetime.utcnow()
        fixed_now = datetime(2024, 8, 15, 10, 0, 0) # 10:00 AM UTC
        mock_datetime.utcnow.return_value = fixed_now

        # Mock Event and User data
        user1 = UserModel(id=1, email='user1@example.com')
        event1_time = fixed_now + timedelta(minutes=30) # Event at 10:30 AM
        event1 = EventModel(
            id=101,
            title='Upcoming Event 1',
            start_time=event1_time,
            description='Test Description 1',
            user_id=user1.id,
            reminder_sent=False,
            user=user1 # Simulate relationship for easy access to email if needed by service directly
        )

        user2 = UserModel(id=2, email='user2@example.com')
        event2_time = fixed_now + timedelta(minutes=45) # Event at 10:45 AM
        event2 = EventModel(
            id=102,
            title='Upcoming Event 2',
            start_time=event2_time,
            description='Test Description 2',
            user_id=user2.id,
            reminder_sent=False,
            user=user2
        )

        # Mock DB query result
        # The service expects a list of (Event, User.email) tuples
        mock_events_to_remind = [
            (event1, user1.email),
            (event2, user2.email)
        ]
        mock_db.session.query(EventModel).join(UserModel).filter(ANY).with_entities(EventModel, UserModel.email).all.return_value = mock_events_to_remind
        mock_db.session.add.return_value = None
        mock_db.session.commit.return_value = None

        # --- Call the service function ---
        result = reminder_service.send_event_reminders()

        # --- Assertions ---
        self.assertEqual(result, "Processed 2 events. Simulated sending 2 reminders.")

        # Check if events were marked as reminder_sent
        self.assertTrue(event1.reminder_sent)
        self.assertTrue(event2.reminder_sent)

        # Check DB interactions
        self.assertEqual(mock_db.session.add.call_count, 2)
        mock_db.session.add.assert_any_call(event1)
        mock_db.session.add.assert_any_call(event2)
        mock_db.session.commit.assert_called_once()

        # Check mail interactions (even if simulated)
        # We expect two messages to be constructed
        self.assertEqual(len(mock_mail.Message.call_args_list), 2)

        # Check first email
        args1, kwargs1 = mock_mail.Message.call_args_list[0]
        self.assertEqual(kwargs1['subject'], f"Reminder: {event1.title}")
        self.assertIn(user1.email, kwargs1['recipients'])
        self.assertIn(event1.title, kwargs1['body'])
        self.assertIn(event1.start_time.strftime('%Y-%m-%d %H:%M'), kwargs1['body'])
        self.assertEqual(kwargs1['sender'], 'test@example.com')

        # Check second email (optional, if details are important)
        args2, kwargs2 = mock_mail.Message.call_args_list[1]
        self.assertEqual(kwargs2['subject'], f"Reminder: {event2.title}")
        self.assertIn(user2.email, kwargs2['recipients'])

        # Verify that get_flask_app was called
        mock_get_flask_app.assert_called_once()

    @patch('gemini_scheduler_app.backend.services.reminder_service.get_flask_app')
    @patch('gemini_scheduler_app.backend.services.reminder_service.db')
    @patch('gemini_scheduler_app.backend.services.reminder_service.mail')
    @patch('gemini_scheduler_app.backend.services.reminder_service.datetime')
    def test_send_event_reminders_no_events_found(
        self, mock_datetime, mock_mail, mock_db, mock_get_flask_app
    ):
        # --- Setup Mocks ---
        mock_app = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = None
        mock_app.app_context.return_value.__exit__.return_value = None
        mock_get_flask_app.return_value = mock_app

        fixed_now = datetime(2024, 8, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        # Mock DB query result to be empty
        mock_db.session.query(EventModel).join(UserModel).filter(ANY).with_entities(EventModel, UserModel.email).all.return_value = []

        # --- Call the service function ---
        result = reminder_service.send_event_reminders()

        # --- Assertions ---
        self.assertEqual(result, "No events needing reminders.")
        mock_db.session.add.assert_not_called()
        mock_db.session.commit.assert_not_called()
        mock_mail.Message.assert_not_called() # No messages should be created
        mock_get_flask_app.assert_called_once()

    @patch('gemini_scheduler_app.backend.services.reminder_service.get_flask_app')
    @patch('gemini_scheduler_app.backend.services.reminder_service.db')
    @patch('gemini_scheduler_app.backend.services.reminder_service.mail')
    @patch('gemini_scheduler_app.backend.services.reminder_service.datetime')
    def test_send_event_reminders_event_outside_window_too_early(
        self, mock_datetime, mock_mail, mock_db, mock_get_flask_app
    ):
        mock_app = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = None
        mock_app.app_context.return_value.__exit__.return_value = None
        mock_get_flask_app.return_value = mock_app

        fixed_now = datetime(2024, 8, 15, 10, 0, 0) # 10:00 AM
        mock_datetime.utcnow.return_value = fixed_now
        # Reminder window ends at 11:00 AM (fixed_now + 1 hour)

        # This event starts at 11:05 AM, which is outside the +1 hour window
        # The service logic itself filters these out, so query returns empty
        mock_db.session.query(EventModel).join(UserModel).filter(ANY).with_entities(EventModel, UserModel.email).all.return_value = []

        result = reminder_service.send_event_reminders()

        self.assertEqual(result, "No events needing reminders.")
        mock_mail.Message.assert_not_called()
        mock_db.session.commit.assert_not_called()

    @patch('gemini_scheduler_app.backend.services.reminder_service.get_flask_app')
    @patch('gemini_scheduler_app.backend.services.reminder_service.db')
    @patch('gemini_scheduler_app.backend.services.reminder_service.mail')
    @patch('gemini_scheduler_app.backend.services.reminder_service.datetime')
    def test_send_event_reminders_event_outside_window_too_late(
        self, mock_datetime, mock_mail, mock_db, mock_get_flask_app
    ):
        mock_app = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = None
        mock_app.app_context.return_value.__exit__.return_value = None
        mock_get_flask_app.return_value = mock_app

        fixed_now = datetime(2024, 8, 15, 10, 0, 0) # 10:00 AM
        mock_datetime.utcnow.return_value = fixed_now
        # Reminder window starts at 9:50 AM (fixed_now - 10 minutes)

        # This event started at 9:45 AM, which is before the -10min window
        # The service logic filters these out, so query returns empty
        mock_db.session.query(EventModel).join(UserModel).filter(ANY).with_entities(EventModel, UserModel.email).all.return_value = []

        result = reminder_service.send_event_reminders()

        self.assertEqual(result, "No events needing reminders.")
        mock_mail.Message.assert_not_called()
        mock_db.session.commit.assert_not_called()

    @patch('gemini_scheduler_app.backend.services.reminder_service.get_flask_app')
    @patch('gemini_scheduler_app.backend.services.reminder_service.db')
    @patch('gemini_scheduler_app.backend.services.reminder_service.mail')
    @patch('gemini_scheduler_app.backend.services.reminder_service.datetime')
    def test_send_event_reminders_event_reminder_already_sent(
        self, mock_datetime, mock_mail, mock_db, mock_get_flask_app
    ):
        mock_app = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = None
        mock_app.app_context.return_value.__exit__.return_value = None
        mock_get_flask_app.return_value = mock_app

        fixed_now = datetime(2024, 8, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        # Event is within window, but reminder_sent is True
        # The service logic filters these out, so query returns empty
        mock_db.session.query(EventModel).join(UserModel).filter(ANY).with_entities(EventModel, UserModel.email).all.return_value = []

        result = reminder_service.send_event_reminders()

        self.assertEqual(result, "No events needing reminders.")
        mock_mail.Message.assert_not_called()
        mock_db.session.commit.assert_not_called()

    @patch('gemini_scheduler_app.backend.services.reminder_service.get_flask_app')
    @patch('gemini_scheduler_app.backend.services.reminder_service.db')
    @patch('gemini_scheduler_app.backend.services.reminder_service.mail')
    @patch('gemini_scheduler_app.backend.services.reminder_service.datetime')
    def test_send_event_reminders_error_during_one_email(
        self, mock_datetime, mock_mail, mock_db, mock_get_flask_app
    ):
        # --- Setup Mocks ---
        mock_app = MagicMock()
        mock_app.app_context.return_value.__enter__.return_value = None
        mock_app.app_context.return_value.__exit__.return_value = None
        mock_app.config = {'MAIL_DEFAULT_SENDER': 'test@example.com'}
        mock_get_flask_app.return_value = mock_app

        fixed_now = datetime(2024, 8, 15, 10, 0, 0)
        mock_datetime.utcnow.return_value = fixed_now

        user1 = UserModel(id=1, email='user1@example.com')
        event1_time = fixed_now + timedelta(minutes=30)
        event1 = EventModel(id=101, title='Event 1 (Success)', start_time=event1_time, user_id=user1.id, reminder_sent=False, user=user1)

        user2 = UserModel(id=2, email='user2@example.com')
        event2_time = fixed_now + timedelta(minutes=35)
        event2 = EventModel(id=102, title='Event 2 (Fail)', start_time=event2_time, user_id=user2.id, reminder_sent=False, user=user2)

        user3 = UserModel(id=3, email='user3@example.com')
        event3_time = fixed_now + timedelta(minutes=40)
        event3 = EventModel(id=103, title='Event 3 (Success)', start_time=event3_time, user_id=user3.id, reminder_sent=False, user=user3)

        mock_events_to_remind = [
            (event1, user1.email),
            (event2, user2.email),
            (event3, user3.email)
        ]
        mock_db.session.query(EventModel).join(UserModel).filter(ANY).with_entities(EventModel, UserModel.email).all.return_value = mock_events_to_remind
        mock_db.session.add.return_value = None
        mock_db.session.commit.return_value = None

        # Mock Message constructor to fail for the second event
        # Store original Message class to use for successful calls
        original_message_class = mock_mail.Message
        def message_side_effect(*args, **kwargs):
            if kwargs.get('subject') == f"Reminder: {event2.title}":
                raise Exception("Simulated email sending failure")
            # Call the original Message constructor for other cases
            return original_message_class(*args, **kwargs)

        mock_mail.Message = MagicMock(side_effect=message_side_effect)
        # Ensure the mock_mail.Message has a `return_value` for successful calls,
        # so that `mail.send(msg)` (if it were active) could be called on it.
        # Since mail.send is commented out, this is less critical, but good practice.
        # The side_effect should return an instance of a mock that can be "sent".
        # However, the current code only constructs Message, then prints.
        # If mail.send was active, the side_effect would need to return a mock that could be sent.
        # For now, just ensuring the constructor is what we mock for failure.

        # --- Call the service function ---
        result = reminder_service.send_event_reminders()

        # --- Assertions ---
        # Processed 3 events, simulated sending for 2 (event1, event3)
        self.assertEqual(result, "Processed 3 events. Simulated sending 2 reminders.")

        self.assertTrue(event1.reminder_sent)
        self.assertFalse(event2.reminder_sent) # Failed email, so reminder_sent should be False
        self.assertTrue(event3.reminder_sent)

        self.assertEqual(mock_db.session.add.call_count, 2) # Only event1 and event3 added
        mock_db.session.add.assert_any_call(event1)
        mock_db.session.add.assert_any_call(event3)
        # mock_db.session.add.assert_never(event2) # This is tricky with side effects, easier to check reminder_sent status

        mock_db.session.commit.assert_called_once() # Commit should still be called for successful ones

        # Message constructor called for all three, but one failed
        self.assertEqual(mock_mail.Message.call_count, 3)


if __name__ == '__main__':
    unittest.main()
