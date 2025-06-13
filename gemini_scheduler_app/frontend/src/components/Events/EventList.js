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
                    // Use a unique key for list items. If occurrences don't have unique IDs (using parent ID),
                    // combine with start time for a more unique key.
                    <li key={event.is_occurrence ? `${event.id}-${event.occurrence_start_time}` : event.id}
                        style={{
                            border: '1px solid #ccc',
                            margin: '10px',
                            padding: '10px',
                            backgroundColor: event.color_tag || (event.is_occurrence ? '#f0f0f0' : 'transparent')
                        }}>
                        <h5>{event.title} {event.is_occurrence ? '(Occurrence)' : ''}</h5>
                        <p>
                            <strong>Start:</strong> {format(new Date(event.is_occurrence ? event.occurrence_start_time : event.start_time), 'Pp')}
                        </p>
                        <p>
                            <strong>End:</strong> {format(new Date(event.is_occurrence ? event.occurrence_end_time : event.end_time), 'Pp')}
                        </p>
                        {event.is_occurrence && event.series_start_time && (
                            <p><small>Part of a series that started on: {format(new Date(event.series_start_time), 'P')}</small></p>
                        )}
                        {event.description && <p><strong>Description:</strong> {event.description}</p>}
                        {/* Editing an occurrence still edits the whole series as per current design */}
                        <button onClick={() => onEdit(event)}>Edit Series</button>
                        {/* Deleting an occurrence deletes the whole series */}
                        <button onClick={() => onDelete(event.id, event)}>Delete Series</button>
                    </li>
                ))}
            </ul>
        </div>
    );
}
export default EventList;
