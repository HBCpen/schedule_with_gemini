from app import db # Assuming db is initialized in app.py
from datetime import datetime

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Corrected: removed extra parenthesis
    description = db.Column(db.Text, nullable=True)
    color_tag = db.Column(db.Text, nullable=True) # Optional, for comma-separated tags
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)

    # Fields for recurrence
    recurrence_rule = db.Column(db.String(255), nullable=True)  # To store RRULE string
    parent_event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True) # Link to master recurring event

    user = db.relationship('User', backref=db.backref('events', lazy=True))
    # Relationship for recurring event instances (children)
    # occurrences = db.relationship('Event', backref=db.backref('parent', remote_side=[id]), lazy='dynamic')


    def __repr__(self):
        return f'<Event {self.title}>'

    def to_dict(self, is_occurrence=False, occurrence_start_time=None, occurrence_end_time=None):
        data = {
            'id': self.id,
            'title': self.title,
            'start_time': (occurrence_start_time or self.start_time).isoformat() + 'Z',
            'end_time': (occurrence_end_time or self.end_time).isoformat() + 'Z',
            'description': self.description,
            'color_tag': self.color_tag,
            'user_id': self.user_id,
            'reminder_sent': self.reminder_sent,
            'recurrence_rule': self.recurrence_rule,
            'parent_event_id': self.parent_event_id
        }
        if is_occurrence:
            # For occurrences, 'id' might be the parent's id if not stored separately,
            # or a newly generated one if needed. For now, use parent's ID.
            # We might also want a unique identifier for an occurrence, e.g., parent_id + occurrence_start_time
            data['is_occurrence'] = True
            # The original start_time of the series is still useful to know
            data['series_start_time'] = self.start_time.isoformat() + 'Z'
        return data
