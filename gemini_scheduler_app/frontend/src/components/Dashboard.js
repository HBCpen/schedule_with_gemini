import React, { useState, useEffect, useCallback } from 'react';
import eventService from '../services/eventService';
import authService from '../services/authService'; // Needed for token for NLP call
import EventForm from './Events/EventForm';
import EventList from './Events/EventList';
import EventCalendar from './Events/EventCalendar'; // Import EventCalendar
import SuggestedTimeSlots from './Events/SuggestedTimeSlots'; // Import SuggestedTimeSlots
// import axios from 'axios'; // Not needed if using eventService for parseNaturalLanguageEvent

function Dashboard() {
    const [events, setEvents] = useState([]);
    const [originalEvents, setOriginalEvents] = useState([]); // Store all events before filtering
    const [editingEvent, setEditingEvent] = useState(null);
    const [showForm, setShowForm] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    // State for NLP input
    const [nlpText, setNlpText] = useState('');
    const [nlpError, setNlpError] = useState('');
    const [nlpLoading, setNlpLoading] = useState(false);

    // State for Search
    const [searchQuery, setSearchQuery] = useState('');
    const [searchStartDate, setSearchStartDate] = useState('');
    const [searchEndDate, setSearchEndDate] = useState('');
    const [searchTags, setSearchTags] = useState('');
    const [searchError, setSearchError] = useState('');
    const [isSearching, setIsSearching] = useState(false); // To indicate search is active
    const [currentCalendarView, setCurrentCalendarView] = useState({ start: null, end: null }); // For storing current calendar view range

    // State for Free Time Search
    const [freeTimeQuery, setFreeTimeQuery] = useState('');
    const [freeTimeStartDate, setFreeTimeStartDate] = useState('');
    const [freeTimeEndDate, setFreeTimeEndDate] = useState('');
    const [suggestedSlots, setSuggestedSlots] = useState([]);
    const [freeTimeSearchLoading, setFreeTimeSearchLoading] = useState(false);
    const [freeTimeSearchError, setFreeTimeSearchError] = useState('');

    // State for Event Summary
    const [eventSummary, setEventSummary] = useState('');
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [summaryError, setSummaryError] = useState('');

    // Modified fetchEvents to accept date range for recurrence expansion
    const fetchEvents = useCallback(async (startDate, endDate) => {
        try {
            setLoading(true);
            // Construct params for getEvents to pass date range
            const params = {};
            if (startDate) params.start_date = startDate.toISOString().split('T')[0]; // YYYY-MM-DD
            if (endDate) params.end_date = endDate.toISOString().split('T')[0];     // YYYY-MM-DD

            // If no dates (e.g. initial load, or search active), fetch without range or rely on search
            // The backend's get_events_in_range requires dates.
            // For initial load, we might need a default range or a different endpoint.
            // For now, only fetch with params if we have them for recurrence.
            let response;
            if(params.start_date && params.end_date){
                response = await eventService.getEvents(params);
            } else {
                 // Fallback: getEvents without specific range (might not expand all recurrences from backend)
                 // Or, if search is active, this fetch might be skipped or search results used.
                 // This part needs careful consideration of initial load vs. view change.
                 // For now, let's assume getEvents without params fetches non-expanded, or a default range.
                 // The backend currently returns error if no dates for get_events_in_range.
                 // So, we must provide *some* default range for the initial load.
                if (!params.start_date) { // Default to a sensible range if not provided
                    const today = new Date();
                    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
                    const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
                    params.start_date = firstDayOfMonth.toISOString().split('T')[0];
                    params.end_date = lastDayOfMonth.toISOString().split('T')[0];
                }
                 response = await eventService.getEvents(params);
            }

            if (response.data.msg && response.status !== 200) { // Handle error response from service
                 setError(response.data.msg);
                 setEvents([]);
                 setOriginalEvents([]);
            } else {
                // Backend now returns events with 'start_time' and 'end_time' potentially adjusted for occurrences
                // and includes 'is_occurrence'. Sorting should still work with these adjusted times.
                const sortedEvents = response.data.sort((a,b) => new Date(a.start_time) - new Date(b.start_time));
                setEvents(sortedEvents);
                if (!isSearching) { // Only update originalEvents if not in a search context
                    setOriginalEvents(sortedEvents);
                }
                setError('');
            }
        } catch (err) {
            console.error("Fetch Events error: ", err);
            const errorMessage = err.response?.data?.msg || 'Failed to fetch events.';
            setError(errorMessage);
            // Potentially set events to empty array or keep stale data, depending on desired UX
            // setEvents([]);
            // setOriginalEvents([]);
        } finally {
            setLoading(false);
        }
    }, [isSearching]); // isSearching is a dependency now

    // Initial fetch and refetch when calendar view changes
    useEffect(() => {
        if (currentCalendarView.start && currentCalendarView.end) {
            fetchEvents(currentCalendarView.start, currentCalendarView.end);
        } else {
            // Initial load with a default range (e.g., current month)
            const today = new Date();
            const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
            const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            fetchEvents(firstDayOfMonth, lastDayOfMonth);
        }
    }, [fetchEvents, currentCalendarView]);

    // Fetch event summary
    const fetchEventSummary = async (dateStr = null) => {
        setSummaryLoading(true);
        setSummaryError('');
        try {
            const response = await eventService.getEventSummary(dateStr);
            setEventSummary(response.data.summary);
        } catch (err) {
            console.error("Fetch Event Summary error: ", err);
            const errorMessage = err.response?.data?.msg || err.response?.data?.detail || 'Failed to fetch event summary.';
            setSummaryError(errorMessage);
            setEventSummary('');
        } finally {
            setSummaryLoading(false);
        }
    };

    useEffect(() => {
        // Fetch summary for today on component mount
        const todayStr = new Date().toISOString().split('T')[0];
        fetchEventSummary(todayStr);
    }, []); // Empty dependency array means this runs once on mount


    // Callback for EventCalendar to update current view range
    const handleViewChange = useCallback((viewInfo) => {
        // viewInfo should contain start and end dates of the new view
        // e.g., viewInfo.start, viewInfo.end (actual properties depend on calendar library)
        // For FullCalendar, it's often view.activeStart and view.activeEnd
        // This is a placeholder for actual integration with a calendar library's event
        console.log("Calendar view changed:", viewInfo);
        // Assuming viewInfo has { start: Date, end: Date }
        if (viewInfo.start && viewInfo.end) {
             setCurrentCalendarView({ start: viewInfo.start, end: viewInfo.end });
        }
        // fetchEvents will be called by useEffect reacting to currentCalendarView change
    }, []);

    const handleSlotSelect = (slot) => {
        console.log('Selected slot:', slot);
        const eventDataForForm = {
            title: slot.description || slot.reason || freeTimeQuery || "New Event from Suggestion",
            // Ensure start_time and end_time are in the format EventForm expects (e.g. YYYY-MM-DDTHH:MM)
            // The API should provide ISO strings like "2024-03-15T10:00:00Z"
            // EventForm's formatDateTimeForInput utility or direct datetime-local input compatibility needs to be kept in mind.
            // If slot.start_time is "2024-03-15T10:00:00Z", it needs to be "2024-03-15T10:00" for datetime-local.
            // Let's assume EventForm can handle ISO strings or we have a utility, for now direct pass.
            start_time: slot.start_time,
            end_time: slot.end_time,
            description: slot.reason || slot.details || "", // Or a more structured description from slot if available
        };
        setEditingEvent(eventDataForForm);
        setShowForm(true);
        setSuggestedSlots([]); // Clear suggestions after selection
        // Consider scrolling to the form: document.getElementById('event-form-id')?.scrollIntoView({ behavior: 'smooth' });
    };

    const handleFindFreeTime = async () => {
        if (!freeTimeQuery.trim()) {
            setFreeTimeSearchError("Please enter a query for the free time search.");
            setSuggestedSlots([]);
            return;
        }
        setFreeTimeSearchLoading(true);
        setFreeTimeSearchError('');
        setSuggestedSlots([]); // Clear previous suggestions

        try {
            // Use eventService.findFreeTime (ensure it's imported)
            const response = await eventService.findFreeTime(freeTimeQuery, freeTimeStartDate, freeTimeEndDate);
            if (response.data && response.data.length > 0) {
                setSuggestedSlots(response.data);
                console.log("Suggested slots:", response.data); // Log for now
                setFreeTimeSearchError(''); // Clear any previous error
            } else if (response.data && response.data.length === 0) {
                setSuggestedSlots([]);
                setFreeTimeSearchError("No available slots found for your query.");
            } else { // Handle cases where response.data might be missing or not an array
                setSuggestedSlots([]);
                setFreeTimeSearchError("Received an unexpected response from the server.");
                console.warn("Unexpected response structure for free time search:", response);
            }
        } catch (err) {
            console.error("Find Free Time error:", err);
            const errorMessage = err.response?.data?.error || err.response?.data?.message || err.message || "Failed to find free time slots.";
            setFreeTimeSearchError(`Failed to find free time slots. ${errorMessage}`);
            setSuggestedSlots([]);
        } finally {
            setFreeTimeSearchLoading(false);
        }
    };

    const handleSearch = async () => {
        const params = {};
        if (searchQuery) params.q = searchQuery;
        if (searchStartDate) params.start_date = searchStartDate;
        if (searchEndDate) params.end_date = searchEndDate;
        if (searchTags) params.tags = searchTags;

        if (Object.keys(params).length === 0) {
            setSearchError("Please enter at least one search criteria.");
            return;
        }
        setSearchError('');
        setLoading(true); // Use main loading indicator for search
        setIsSearching(true);

        try {
            const response = await eventService.searchEvents(params);
            setEvents(response.data.sort((a,b) => new Date(a.start_time) - new Date(b.start_time)));
            setError(''); // Clear main error
        } catch (err) {
            console.error("Search error:", err);
            setSearchError(err.response?.data?.msg || "Failed to search events.");
            setEvents(originalEvents); // Revert to original events on search failure
        } finally {
            setLoading(false);
        }
    };

    const clearSearch = () => {
        setSearchQuery('');
        setSearchStartDate('');
        setSearchEndDate('');
        setSearchTags('');
        setSearchError('');
        if (isSearching) { // Only refetch if a search was active
           setEvents(originalEvents); // Revert to the full list of events
        }
        setIsSearching(false);
    };

    const handleFormSubmit = () => {
        // Refetch events for the current view after form submission
        if (currentCalendarView.start && currentCalendarView.end) {
            fetchEvents(currentCalendarView.start, currentCalendarView.end);
        } else {
            const today = new Date();
            fetchEvents(new Date(today.getFullYear(), today.getMonth(), 1), new Date(today.getFullYear(), today.getMonth() + 1, 0));
        }
        setShowForm(false);
        setEditingEvent(null);
    };

    const handleEdit = (event) => {
        // When editing an occurrence, the event object from backend contains parent's recurrence_rule.
        // The EventForm is designed to handle this by populating from event.recurrence_rule.
        // The 'id' will be the master event's ID if it's an occurrence not stored separately,
        // or the specific occurrence's ID if it's an exception (future enhancement).
        // For now, backend sends master event ID for occurrences.
        setEditingEvent(event); // event object from backend already has necessary fields
        setShowForm(true);
    };

    const handleCancelEdit = () => {
        setEditingEvent(null);
        setShowForm(false);
    }

    const handleDelete = async (eventId, eventInstanceInfo = null) => {
        // For recurring events, need to decide: delete series or just this instance?
        // Current backend deletes master and all implied occurrences.
        // eventId should be the master event's ID if deleting a series.
        // eventInstanceInfo is the event object itself, which might be an occurrence or a master.
        let confirmMessage = 'Are you sure you want to delete this event?';

        // Check if the event to be deleted (or its series) is recurring.
        // eventInstanceInfo.recurrence_rule will exist if it's a master recurring event.
        // eventInstanceInfo.is_occurrence will be true if it's an occurrence.
        if (eventInstanceInfo?.recurrence_rule || eventInstanceInfo?.is_occurrence) {
            confirmMessage = 'This is a recurring event or part of a series. Deleting it will remove the master event and all its occurrences. Are you sure?';
        }

        if (window.confirm(confirmMessage)) {
            try {
                // eventId is already the master ID (from event.id, which is master's ID for occurrences too)
                await eventService.deleteEvent(eventId);
                if (currentCalendarView.start && currentCalendarView.end) {
                    fetchEvents(currentCalendarView.start, currentCalendarView.end);
                } else {
                     const today = new Date();
                     fetchEvents(new Date(today.getFullYear(), today.getMonth(), 1), new Date(today.getFullYear(), today.getMonth() + 1, 0));
                }
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

    if (loading && !nlpLoading && !summaryLoading) return <p>Loading events...</p>; // Adjusted loading condition
    if (error) return <p style={{color: 'red'}}>{error}</p>; // Main event loading error

    return (
        <div>
            <h2>My Schedule</h2>

            {/* Event Summary Section */}
            <div style={{ border: '1px solid #eee', padding: '15px', marginBottom: '20px', borderRadius: '5px', backgroundColor: '#f9f9f9' }}>
                <h4>Today's Summary</h4>
                {summaryLoading && <p>Loading summary...</p>}
                {summaryError && <p style={{ color: 'red' }}>Error: {summaryError}</p>}
                {eventSummary && !summaryLoading && !summaryError && <p>{eventSummary}</p>}
                {!eventSummary && !summaryLoading && !summaryError && <p>No summary available for today.</p>}
            </div>

            {/* Search Section */}
            <div style={{ border: '1px solid #ccc', padding: '15px', marginBottom: '20px', borderRadius: '5px' }}>
                <h4>Search Events</h4>
                <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', marginBottom: '10px' }}>
                    <input
                        type="text"
                        placeholder="Keywords (title, description)"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        style={{ padding: '8px', flexGrow: 1 }}
                    />
                    <input
                        type="date"
                        value={searchStartDate}
                        onChange={(e) => setSearchStartDate(e.target.value)}
                        style={{ padding: '8px' }}
                    />
                    <input
                        type="date"
                        value={searchEndDate}
                        onChange={(e) => setSearchEndDate(e.target.value)}
                        style={{ padding: '8px' }}
                    />
                    <input
                        type="text"
                        placeholder="Tags (comma-separated)"
                        value={searchTags}
                        onChange={(e) => setSearchTags(e.target.value)}
                        style={{ padding: '8px', flexGrow: 1 }}
                    />
                </div>
                <button onClick={handleSearch} style={{ padding: '8px 15px', marginRight: '10px' }}>Search</button>
                <button onClick={clearSearch} style={{ padding: '8px 15px' }}>Clear Search</button>
                {searchError && <p style={{ color: 'red', marginTop: '10px' }}>{searchError}</p>}
            </div>
            <hr />

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

            {/* Free Time Search Section */}
            <div style={{ border: '1px solid #ccc', padding: '15px', marginBottom: '20px', borderRadius: '5px' }}>
                <h4>Find Available Time Slots</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '10px' }}>
                    <input
                        type="text"
                        placeholder="e.g., a 30-minute meeting next Monday"
                        value={freeTimeQuery}
                        onChange={(e) => setFreeTimeQuery(e.target.value)}
                        style={{ padding: '8px' }}
                    />
                    <div style={{ display: 'flex', gap: '10px' }}>
                        <input
                            type="date"
                            value={freeTimeStartDate}
                            onChange={(e) => setFreeTimeStartDate(e.target.value)}
                            style={{ padding: '8px', flexGrow: 1 }}
                            title="Start date for search range (optional)"
                        />
                        <input
                            type="date"
                            value={freeTimeEndDate}
                            onChange={(e) => setFreeTimeEndDate(e.target.value)}
                            style={{ padding: '8px', flexGrow: 1 }}
                            title="End date for search range (optional)"
                        />
                    </div>
                </div>
                <button
                    onClick={handleFindFreeTime}
                    style={{ padding: '8px 15px' }}
                    disabled={freeTimeSearchLoading}
                >
                    {freeTimeSearchLoading ? 'Searching...' : 'Find Time'}
                </button>
                {freeTimeSearchLoading && <p>Loading suggestions...</p>}
                {freeTimeSearchError && <p style={{ color: 'red' }}>{freeTimeSearchError}</p>}
                {!freeTimeSearchLoading && !freeTimeSearchError && (
                    <SuggestedTimeSlots
                        slots={suggestedSlots}
                        onSlotSelect={handleSlotSelect} // Pass the new handler
                    />
                )}
            </div>
            <hr />

            <button onClick={() => { setEditingEvent(null); setShowForm(!showForm); if (showForm) handleCancelEdit(); }}>
                {showForm && !editingEvent ? 'Cancel New Event Creation' : (editingEvent ? 'Cancel Editing' : 'Create New Event Manually')}
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
                onEventDelete={handleDelete} // Pass the possibly enhanced handleDelete
                onViewChange={handleViewChange} // Pass callback to get view changes from calendar
            />
            <hr />
            <h3>Event List View</h3>
            {/* EventList might also need to be aware of is_occurrence for display */}
            <EventList events={events} onEdit={handleEdit} onDelete={handleDelete} />
        </div>
    );
}
export default Dashboard;
