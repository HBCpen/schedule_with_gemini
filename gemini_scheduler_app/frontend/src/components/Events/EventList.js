import React from 'react';
import { format } from 'date-fns'; // Using date-fns installed earlier

function EventList({ events, onEdit, onDelete }) {
    if (!events || events.length === 0) {
        return <p>No events scheduled.</p>;
    }

    return (
        <div>
            <h4>Your Events</h4>
            <ul style={{ listStyleType: 'none', padding: 0 }}>
                {events.map(event => (
                    <li key={event.id} style={{ border: '1px solid #ccc', margin: '10px', padding: '10px', backgroundColor: event.color_tag || 'transparent' }}>
                        <h5>{event.title}</h5>
                        <p>
                            <strong>Start:</strong> {format(new Date(event.start_time), 'Pp')}
                        </p>
                        <p>
                            <strong>End:</strong> {format(new Date(event.end_time), 'Pp')}
                        </p>
                        {event.description && <p><strong>Description:</strong> {event.description}</p>}
                        <button onClick={() => onEdit(event)}>Edit</button>
                        <button onClick={() => onDelete(event.id)}>Delete</button>
                    </li>
                ))}
            </ul>
        </div>
    );
}
export default EventList;
