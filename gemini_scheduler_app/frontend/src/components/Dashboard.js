import React, { useState, useEffect, useCallback } from 'react';
import eventService from '../services/eventService';
import authService from '../services/authService'; // Needed for token for NLP call
import EventForm from './Events/EventForm';
import EventList from './Events/EventList';
import EventCalendar from './Events/EventCalendar'; // Import EventCalendar
// import axios from 'axios'; // Not needed if using eventService for parseNaturalLanguageEvent

function Dashboard() {
    const [events, setEvents] = useState([]);
    const [editingEvent, setEditingEvent] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // State for NLP input
    const [nlpText, setNlpText] = useState('');
    const [nlpError, setNlpError] = useState('');
    const [nlpLoading, setNlpLoading] = useState(false);

    const fetchEvents = useCallback(async () => {
        try {
            setLoading(true);
            const response = await eventService.getEvents();
            setEvents(response.data.sort((a,b) => new Date(a.start_time) - new Date(b.start_time)));
            setError('');
        } catch (err) {
            setError('Failed to fetch events.');
            console.error(err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchEvents();
    }, [fetchEvents]);

    const handleFormSubmit = () => {
        fetchEvents();
        setShowForm(false);
        setEditingEvent(null);
    };

    const handleEdit = (event) => {
        setEditingEvent(event);
        setShowForm(true);
    };

    const handleCancelEdit = () => {
        setEditingEvent(null);
        setShowForm(false);
    }

    const handleDelete = async (id) => {
        if (window.confirm('Are you sure you want to delete this event?')) {
            try {
                await eventService.deleteEvent(id);
                fetchEvents();
            } catch (err) {
                setError('Failed to delete event.');
                console.error(err);
            }
        }
    };

    const handleNlpSubmit = async () => {
        if (!nlpText.trim()) {
            setNlpError('Please enter some text to parse.');
            return;
        }
        setNlpLoading(true);
        setNlpError('');
        setEditingEvent(null);
        setShowForm(false);

        try {
            const response = await eventService.parseNaturalLanguageEvent(nlpText);

            if (response.data && !response.data.error) {
                const parsed = response.data;

                let initialStartTime = '';
                if (parsed.date && parsed.start_time) {
                    // Ensure time part has seconds if missing, e.g. "15:00" -> "15:00:00"
                    const timeParts = parsed.start_time.split(':');
                    const formattedStartTime = `${timeParts[0]}:${timeParts[1] || '00'}:${timeParts[2] || '00'}`;
                    initialStartTime = `${parsed.date}T${formattedStartTime}`;
                }

                let initialEndTime = '';
                if (parsed.date && parsed.end_time) {
                    const timeParts = parsed.end_time.split(':');
                    const formattedEndTime = `${timeParts[0]}:${timeParts[1] || '00'}:${timeParts[2] || '00'}`;
                    initialEndTime = `${parsed.date}T${formattedEndTime}`;
                } else if (initialStartTime && !parsed.end_time) {
                    try {
                        const startDate = new Date(initialStartTime);
                        startDate.setHours(startDate.getHours() + 1);
                        // formatDateTimeForInput in EventForm produces YYYY-MM-DDTHH:MM
                        // We need to match that for consistency if passing directly
                        const offset = startDate.getTimezoneOffset();
                        const adjustedDate = new Date(startDate.getTime() - (offset*60*1000));
                        initialEndTime = adjustedDate.toISOString().slice(0,16);

                    } catch (e) { console.error("Error calculating default end time", e); }
                }

                const eventDataForForm = {
                    // No ID for NLP-parsed new events
                    title: parsed.title || '',
                    start_time: initialStartTime, // Expected by EventForm's formatDateTimeForInput logic
                    end_time: initialEndTime,     // or directly by datetime-local input
                    description: parsed.description || '',
                    // color_tag: '', // Gemini doesn't provide this
                    // location: parsed.location || '', // EventForm doesn't have location
                };

                setEditingEvent(eventDataForForm);
                setShowForm(true);
                setNlpText('');
            } else {
                setNlpError(response.data.msg || response.data.detail || 'Failed to parse event text.');
            }
        } catch (err) {
            setNlpError(err.response?.data?.msg || err.response?.data?.detail || 'Error calling NLP parser.');
            console.error("NLP Parsing Error:", err);
        } finally {
            setNlpLoading(false);
        }
    };

    if (loading && !nlpLoading) return <p>Loading events...</p>; // Show event loading only if NLP is not also loading
    if (error) return <p style={{color: 'red'}}>{error}</p>;

    return (
        <div>
            <h2>My Schedule</h2>

            <div>
                <h4>Add Event with Natural Language (Beta)</h4>
                <textarea
                    value={nlpText}
                    onChange={(e) => setNlpText(e.target.value)}
                    placeholder="e.g., Meeting with team tomorrow at 2pm for 1 hour about project X"
                    rows="3"
                    style={{width: '80%', marginBottom: '10px', padding: '5px'}}
                    disabled={nlpLoading}
                />
                <button onClick={handleNlpSubmit} disabled={nlpLoading}>
                    {nlpLoading ? 'Parsing...' : 'Parse & Add Event'}
                </button>
                {nlpError && <p style={{color: 'red'}}>{nlpError}</p>}
            </div>
            <hr />

            <button onClick={() => { setEditingEvent(null); setShowForm(!showForm); if (showForm) handleCancelEdit(); }}>
                {showForm && !editingEvent ? 'Cancel New Event Creation' : 'Create New Event Manually'}
            </button>

            {showForm && (
                <EventForm
                    eventToEdit={editingEvent} // This can be a new event object from NLP (no id) or existing event (with id)
                    onFormSubmit={handleFormSubmit}
                    onCancelEdit={handleCancelEdit}
                />
            )}
            <hr />
            {/* Render EventCalendar above EventList */}
            <h3>Event Calendar View</h3>
            <EventCalendar
                events={events}
                onEventEdit={handleEdit}
                onEventDelete={handleDelete}
            />
            <hr />
            <h3>Event List View</h3>
            <EventList events={events} onEdit={handleEdit} onDelete={handleDelete} />
        </div>
    );
}
export default Dashboard;
