from app import db # Assuming db is initialized in app.py
from datetime import datetime

class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow) # Corrected: removed extra parenthesis
    description = db.Column(db.Text, nullable=True)
    color_tag = db.Column(db.String(20), nullable=True) # Optional
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reminder_sent = db.Column(db.Boolean, default=False, nullable=False) # New field

    user = db.relationship('User', backref=db.backref('events', lazy=True))

    def __repr__(self):
        return f'<Event {self.title}>'

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'start_time': self.start_time.isoformat() + 'Z', # ISO format UTC
            'end_time': self.end_time.isoformat() + 'Z',   # ISO format UTC
            'description': self.description,
            'color_tag': self.color_tag,
            'user_id': self.user_id,
            'reminder_sent': self.reminder_sent # Added to dict
        }
