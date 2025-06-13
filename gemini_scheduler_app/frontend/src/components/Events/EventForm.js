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

    // Recurrence state
    const [recurrenceRule, setRecurrenceRule] = useState(''); // Stores the final RRULE string
    const [freq, setFreq] = useState(''); // DAILY, WEEKLY, MONTHLY, YEARLY
    const [interval, setInterval] = useState(1);
    const [byDay, setByDay] = useState([]); // For WEEKLY: MO, TU, WE, etc.
    const [until, setUntil] = useState(''); // End date for recurrence

    const resetRecurrenceFields = () => {
        setFreq('');
        setInterval(1);
        setByDay([]);
        setUntil('');
        setRecurrenceRule('');
    };

    useEffect(() => {
        if (eventToEdit) {
            setTitle(eventToEdit.title || '');
            // If it's an occurrence, use its specific start/end time for the form fields,
            // but the recurrence rule should come from the parent/master event.
            // For this task, we assume eventToEdit is always the master if it has a rule.
            setStartTime(formatDateTimeForInput(eventToEdit.start_time) || '');
            setEndTime(formatDateTimeForInput(eventToEdit.end_time) || '');
            setDescription(eventToEdit.description || '');
            setColorTag(eventToEdit.color_tag || '');

            // Populate recurrence fields if rule exists
            if (eventToEdit.recurrence_rule) {
                setRecurrenceRule(eventToEdit.recurrence_rule); // Store the raw rule
                // Attempt to parse RRULE to populate form - This can be complex.
                // For simplicity, we'll just store the rule and expect user to redefine if they want to change.
                // A full RRULE parser for UI population is a larger feature.
                // Basic parsing for freq:
                const ruleParts = eventToEdit.recurrence_rule.split(';');
                const freqPart = ruleParts.find(part => part.startsWith('FREQ='));
                if (freqPart) {
                    setFreq(freqPart.split('=')[1]);
                }
                const intervalPart = ruleParts.find(part => part.startsWith('INTERVAL='));
                if (intervalPart) {
                    setInterval(parseInt(intervalPart.split('=')[1], 10));
                }
                const byDayPart = ruleParts.find(part => part.startsWith('BYDAY='));
                if (byDayPart) {
                    setByDay(byDayPart.split('=')[1].split(','));
                }
                const untilPart = ruleParts.find(part => part.startsWith('UNTIL='));
                if (untilPart) {
                     //UNTIL=YYYYMMDDTHHMMSSZ format from rrule
                    const untilDateStr = untilPart.split('=')[1];
                    const year = untilDateStr.substring(0,4);
                    const month = untilDateStr.substring(4,6);
                    const day = untilDateStr.substring(6,8);
                    setUntil(`${year}-${month}-${day}`);
                }

            } else {
                resetRecurrenceFields();
            }
        } else {
            // Reset all fields for new event
            setTitle('');
            setStartTime('');
            setEndTime('');
            setDescription('');
            setColorTag('');
            resetRecurrenceFields();
        }
        setMessage('');
        setError('');
    }, [eventToEdit]);

    // Helper to build RRULE string
    const buildRecurrenceRule = () => {
        if (!freq) {
            return null; // Or empty string, depending on backend expectation for "no recurrence"
        }
        let parts = [`FREQ=${freq}`];
        if (interval > 1) {
            parts.push(`INTERVAL=${interval}`);
        }
        if (freq === 'WEEKLY' && byDay.length > 0) {
            parts.push(`BYDAY=${byDay.join(',')}`);
        }
        if (until) {
            // Format for RRULE: YYYYMMDDTHHMMSSZ (use end of day for UNTIL date)
            const date = new Date(until);
            const utcDate = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate(), 23, 59, 59));
            parts.push(`UNTIL=${utcDate.toISOString().replace(/[-:.]/g, '').slice(0, -1)}Z`);
        }
        return parts.join(';');
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage('');
        setError('');

        if (new Date(startTime) >= new Date(endTime)) {
            setError('End time must be after start time.');
            return;
        }

        const constructedRrule = buildRecurrenceRule();

        const eventData = {
            title,
            start_time: formatInputDateTimeToISO(startTime),
            end_time: formatInputDateTimeToISO(endTime),
            description,
            color_tag: colorTag || null, // Send null if empty
            recurrence_rule: constructedRrule
        };

        // If editing an event that was an occurrence, and user now sets 'Does not repeat'
        // we might want to convert it to a single event. For now, all edits to recurring events
        // update the master rule.

        try {
            if (eventToEdit && eventToEdit.id) { // Ensure ID exists for update
                // If eventToEdit.is_occurrence is true, this logic might need to be different
                // e.g. "Do you want to update this and all future events, or just this one?"
                // For now, assume updating the master if recurrence_rule is present or being set.
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

    const handleByDayChange = (day) => {
        setByDay(prev => prev.includes(day) ? prev.filter(d => d !== day) : [...prev, day]);
    };

    // Display existing RRULE if not actively defining a new one
    const displayRecurrenceRule = eventToEdit?.recurrence_rule && !freq;


    return (
        <form onSubmit={handleSubmit}>
            <h3>{eventToEdit ? (eventToEdit.is_occurrence ? 'Edit Occurrence (Modifies Series)' : 'Edit Event') : 'Create Event'}</h3>
            {eventToEdit?.is_occurrence && <p style={{color: 'orange'}}>Note: You are editing an occurrence of a recurring series. Changes will apply to the entire series.</p>}
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

            {/* Recurrence Section */}
            <h4>Recurrence</h4>
            {displayRecurrenceRule && (
                <div>
                    <p>Current rule: {eventToEdit.recurrence_rule}</p>
                    <button type="button" onClick={() => {
                        // Allow user to clear and define new rule
                        // This requires parsing the existing rule to set freq, etc.
                        // For now, let's make them explicitly choose a frequency to redefine
                        const ruleParts = eventToEdit.recurrence_rule.split(';');
                        const freqPart = ruleParts.find(part => part.startsWith('FREQ='));
                         if (freqPart) setFreq(freqPart.split('=')[1]); else setFreq("DAILY"); // Default to daily if cannot parse
                        // More parsing logic would be needed here to fully populate form from any RRULE string.
                        // This is a simplified approach.
                    }}>Modify Rule</button>
                </div>
            )}
            <div>
                <label>Frequency:</label>
                <select value={freq} onChange={(e) => { setFreq(e.target.value); setByDay([]); /* Reset byDay when freq changes */ }}>
                    <option value="">Does not repeat</option>
                    <option value="DAILY">Daily</option>
                    <option value="WEEKLY">Weekly</option>
                    <option value="MONTHLY">Monthly</option>
                    <option value="YEARLY">Yearly</option>
                </select>
            </div>

            {freq && (
                <>
                    <div>
                        <label>Interval (Repeat every X):</label>
                        <input type="number" value={interval} min="1" onChange={(e) => setInterval(parseInt(e.target.value,10))} />
                        <span> {freq.toLowerCase().slice(0,-2)}{(interval > 1 ? 's' : '')}</span>
                    </div>

                    {freq === 'WEEKLY' && (
                        <div>
                            <label>Repeat on:</label>
                            {['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'].map(day => (
                                <label key={day} style={{marginRight: '5px', display: 'inline-block'}}>
                                    <input type="checkbox" checked={byDay.includes(day)} onChange={() => handleByDayChange(day)} />
                                    {day}
                                </label>
                            ))}
                        </div>
                    )}
                    {/* Placeholder for MONTHLY and YEARLY specific options */}
                    {/* For MONTHLY: bymonthday, bysetpos, etc. */}
                    {/* For YEARLY: bymonth, byyearday etc.  */}
                    {/* These are more complex to UI build currently */}


                    <div>
                        <label>Ends (Until Date - Optional):</label>
                        <input type="date" value={until} onChange={(e) => setUntil(e.target.value)} />
                    </div>
                </>
            )}
            <hr style={{margin: '20px 0'}}/>
            <button type="submit">{eventToEdit ? 'Update' : 'Create'}</button>
            {eventToEdit && <button type="button" onClick={() => { resetRecurrenceFields(); if(onCancelEdit) onCancelEdit();}}>Cancel</button>}
        </form>
    );
}
export default EventForm;
