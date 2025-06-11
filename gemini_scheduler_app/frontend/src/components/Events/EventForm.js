import React, { useState, useEffect } from 'react';
import eventService from '../../services/eventService';

// Helper to format date for datetime-local input
// Input: ISO string or Date object
// Output: YYYY-MM-DDTHH:MM
const formatDateTimeForInput = (date) => {
    if (!date) return '';
    const d = new Date(date);
    // Adjust for timezone offset to display correctly in local time
    const offset = d.getTimezoneOffset();
    const adjustedDate = new Date(d.getTime() - (offset*60*1000));
    return adjustedDate.toISOString().slice(0, 16);
};

// Helper to convert local datetime-input string to UTC ISO string
const formatInputDateTimeToISO = (localDateTimeString) => {
    if (!localDateTimeString) return null;
    const date = new Date(localDateTimeString);
    return date.toISOString(); // Already in UTC
}

function EventForm({ eventToEdit, onFormSubmit, onCancelEdit }) {
    const [title, setTitle] = useState('');
    const [startTime, setStartTime] = useState('');
    const [endTime, setEndTime] = useState('');
    const [description, setDescription] = useState('');
    const [colorTag, setColorTag] = useState('');
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        if (eventToEdit) {
            setTitle(eventToEdit.title || '');
            setStartTime(formatDateTimeForInput(eventToEdit.start_time) || '');
            setEndTime(formatDateTimeForInput(eventToEdit.end_time) || '');
            setDescription(eventToEdit.description || '');
            setColorTag(eventToEdit.color_tag || '');
        } else {
            setTitle('');
            setStartTime('');
            setEndTime('');
            setDescription('');
            setColorTag('');
        }
        setMessage('');
        setError('');
    }, [eventToEdit]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        setError('');

        if (new Date(startTime) >= new Date(endTime)) {
            setError('End time must be after start time.');
            return;
        }

        const eventData = {
            title,
            start_time: formatInputDateTimeToISO(startTime),
            end_time: formatInputDateTimeToISO(endTime),
            description,
            color_tag: colorTag || null // Send null if empty
        };

        try {
            if (eventToEdit) {
                await eventService.updateEvent(eventToEdit.id, eventData);
                setMessage('Event updated successfully!');
            } else {
                await eventService.createEvent(eventData);
                setMessage('Event created successfully!');
            }
            if(onFormSubmit) onFormSubmit(); // Callback to refresh event list
        } catch (err) {
            setError(err.response?.data?.msg || 'Failed to save event.');
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <h3>{eventToEdit ? 'Edit Event' : 'Create Event'}</h3>
            {message && <p style={{color: 'green'}}>{message}</p>}
            {error && <p style={{color: 'red'}}>{error}</p>}
            <div>
                <label>Title:</label>
                <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} required />
            </div>
            <div>
                <label>Start Time:</label>
                <input type="datetime-local" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
            </div>
            <div>
                <label>End Time:</label>
                <input type="datetime-local" value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
            </div>
            <div>
                <label>Description:</label>
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
            </div>
            <div>
                <label>Color Tag (e.g., blue, red):</label>
                <input type="text" value={colorTag} onChange={(e) => setColorTag(e.target.value)} />
            </div>
            <button type="submit">{eventToEdit ? 'Update' : 'Create'}</button>
            {eventToEdit && <button type="button" onClick={onCancelEdit}>Cancel Edit</button>}
        </form>
    );
}
export default EventForm;
