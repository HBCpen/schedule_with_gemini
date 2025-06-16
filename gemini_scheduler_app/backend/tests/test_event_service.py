import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session
from gemini_scheduler_app.backend.services import event_service
from gemini_scheduler_app.backend.models import Event as EventModel
from gemini_scheduler_app.backend.schemas import EventCreate, EventUpdate

class TestEventService(unittest.TestCase):

    def setUp(self):
        self.db_session_mock = MagicMock(spec=Session)

    def test_create_event_success(self):
        event_create = EventCreate(
            name="Team Meeting",
            start_time="2024-08-15T10:00:00",
            end_time="2024-08-15T11:00:00",
            description="Weekly team sync"
        )

        # Mock the database interactions
        self.db_session_mock.add.return_value = None
        self.db_session_mock.commit.return_value = None
        self.db_session_mock.refresh.return_value = None

        created_event = event_service.create_event(self.db_session_mock, event_create)

        self.assertIsNotNone(created_event)
        self.assertEqual(created_event.name, event_create.name)
        self.assertEqual(created_event.start_time, event_create.start_time)
        self.assertEqual(created_event.end_time, event_create.end_time)
        self.assertEqual(created_event.description, event_create.description)
        self.db_session_mock.add.assert_called_once()
        self.db_session_mock.commit.assert_called_once()
        self.db_session_mock.refresh.assert_called_once()

    def test_get_event_success(self):
        event_id = 1
        mock_event = EventModel(
            id=event_id,
            name="Team Meeting",
            start_time="2024-08-15T10:00:00",
            end_time="2024-08-15T11:00:00",
            description="Weekly team sync"
        )
        self.db_session_mock.query(EventModel).filter(EventModel.id == event_id).first.return_value = mock_event

        retrieved_event = event_service.get_event(self.db_session_mock, event_id)

        self.assertIsNotNone(retrieved_event)
        self.assertEqual(retrieved_event.id, event_id)
        self.db_session_mock.query(EventModel).filter(EventModel.id == event_id).first.assert_called_once()

    def test_get_event_not_found(self):
        event_id = 99 # Non-existent ID
        self.db_session_mock.query(EventModel).filter(EventModel.id == event_id).first.return_value = None

        retrieved_event = event_service.get_event(self.db_session_mock, event_id)

        self.assertIsNone(retrieved_event)
        self.db_session_mock.query(EventModel).filter(EventModel.id == event_id).first.assert_called_once()

    def test_get_events_success(self):
        mock_events = [
            EventModel(id=1, name="Event 1", start_time="2024-08-15T10:00:00", end_time="2024-08-15T11:00:00"),
            EventModel(id=2, name="Event 2", start_time="2024-08-16T14:00:00", end_time="2024-08-16T15:00:00")
        ]
        self.db_session_mock.query(EventModel).offset(0).limit(100).all.return_value = mock_events

        retrieved_events = event_service.get_events(self.db_session_mock, skip=0, limit=100)

        self.assertEqual(len(retrieved_events), 2)
        self.db_session_mock.query(EventModel).offset(0).limit(100).all.assert_called_once()

    def test_update_event_success(self):
        event_id = 1
        event_update = EventUpdate(
            name="Updated Team Meeting",
            description="Updated weekly team sync"
        )
        mock_existing_event = EventModel(
            id=event_id,
            name="Team Meeting",
            start_time="2024-08-15T10:00:00",
            end_time="2024-08-15T11:00:00",
            description="Weekly team sync"
        )

        self.db_session_mock.query(EventModel).filter(EventModel.id == event_id).first.return_value = mock_existing_event
        self.db_session_mock.commit.return_value = None
        self.db_session_mock.refresh.return_value = None

        updated_event = event_service.update_event(self.db_session_mock, event_id, event_update)

        self.assertIsNotNone(updated_event)
        self.assertEqual(updated_event.name, event_update.name)
        self.assertEqual(updated_event.description, event_update.description)
        # Ensure other fields are not changed if not in update schema
        self.assertEqual(updated_event.start_time, mock_existing_event.start_time)
        self.db_session_mock.commit.assert_called_once()
        self.db_session_mock.refresh.assert_called_once()

    def test_update_event_not_found(self):
        event_id = 99 # Non-existent ID
        event_update = EventUpdate(name="Updated Non Existent Event")

        self.db_session_mock.query(EventModel).filter(EventModel.id == event_id).first.return_value = None

        updated_event = event_service.update_event(self.db_session_mock, event_id, event_update)

        self.assertIsNone(updated_event)
        self.db_session_mock.commit.assert_not_called() # Commit should not be called if event not found

    def test_delete_event_success(self):
        event_id = 1
        mock_existing_event = EventModel(id=event_id, name="Event to delete")

        self.db_session_mock.query(EventModel).filter(EventModel.id == event_id).first.return_value = mock_existing_event
        self.db_session_mock.delete.return_value = None
        self.db_session_mock.commit.return_value = None

        deleted_event = event_service.delete_event(self.db_session_mock, event_id)

        self.assertIsNotNone(deleted_event)
        self.assertEqual(deleted_event.id, event_id)
        self.db_session_mock.delete.assert_called_once_with(mock_existing_event)
        self.db_session_mock.commit.assert_called_once()

    def test_delete_event_not_found(self):
        event_id = 99 # Non-existent ID
        self.db_session_mock.query(EventModel).filter(EventModel.id == event_id).first.return_value = None

        deleted_event = event_service.delete_event(self.db_session_mock, event_id)

        self.assertIsNone(deleted_event)
        self.db_session_mock.delete.assert_not_called()
        self.db_session_mock.commit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
