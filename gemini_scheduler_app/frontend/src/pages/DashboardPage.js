import React, { useState, useEffect } from 'react';
import EventCalendar from '../components/Events/EventCalendar';
import EventForm from '../components/Events/EventForm';
import eventService from '../services/eventService';

const DashboardPage = () => {
  const [events, setEvents] = useState([]);
  const [isEventFormModalOpen, setIsEventFormModalOpen] = useState(false);
  const [eventToEdit, setEventToEdit] = useState(null);
  const [viewRange, setViewRange] = useState(null);

  const fetchEvents = async () => {
    if (!viewRange || !viewRange.start || !viewRange.end) {
      // console.log("fetchEvents called without viewRange, returning");
      return;
    }
    try {
      // console.log("Fetching events for range:", viewRange.start, viewRange.end);
      const fetchedEvents = await eventService.getEvents(viewRange.start, viewRange.end);
      // console.log("Fetched events:", fetchedEvents);
      setEvents(fetchedEvents);
    } catch (error) {
      console.error('Error fetching events:', error);
      // Optionally, set an error state here to display to the user
    }
  };

  useEffect(() => {
    // console.log("useEffect triggered, viewRange:", viewRange);
    if (viewRange) {
      fetchEvents();
    }
  }, [viewRange]);

  const handleOpenEventFormModal = (event = null) => {
    setEventToEdit(event);
    setIsEventFormModalOpen(true);
  };

  const handleCloseEventFormModal = () => {
    setIsEventFormModalOpen(false);
    setEventToEdit(null);
  };

  const handleEventFormSubmit = async () => {
    await fetchEvents();
    handleCloseEventFormModal();
  };

  const handleEventEdit = (event) => {
    // console.log("handleEventEdit called with event:", event);
    handleOpenEventFormModal(event);
  };

  const handleEventDelete = async (eventToDelete) => {
    // console.log("handleEventDelete called with event:", eventToDelete);
    if (window.confirm('Are you sure you want to delete this event? This may delete the entire series if it\'s a recurring event.')) {
      try {
        await eventService.deleteEvent(eventToDelete.id, eventToDelete);
        await fetchEvents(); // Refresh events after deletion
      } catch (error) {
        console.error('Error deleting event:', error);
        // Optionally, set an error state here or show a notification
      }
    }
  };

  const handleViewChange = (newView) => {
    // console.log("handleViewChange called with newView:", newView);
    setViewRange({ start: newView.startStr, end: newView.endStr });
  };

  // Initial fetch for default view (e.g., current month) if viewRange is not set
  // This might be handled by the calendar's initialLoad or viewDidMount
  // For now, let EventCalendar trigger the first handleViewChange
  useEffect(() => {
    // console.log("Initial mount effect, viewRange:", viewRange);
    if (!viewRange) {
        // This is a common way to set an initial range for FullCalendar
        // It will trigger the first fetchEvents via handleViewChange -> useEffect[viewRange]
        const now = new Date();
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        setViewRange({ start: start.toISOString(), end: end.toISOString() });
    }
  }, []); // Empty dependency array ensures this runs only once on mount


  return (
    <div>
      <h2>Dashboard Page</h2>
      <button onClick={() => handleOpenEventFormModal()} style={{ marginBottom: '20px' }}>
        Add New Event
      </button>
      <EventCalendar
        events={events}
        onEventEdit={handleEventEdit} // Make sure EventCalendar calls this with the event object
        onEventDelete={handleEventDelete} // Make sure EventCalendar calls this with the event object
        onViewChange={handleViewChange} // This should be called by FullCalendar's datesSet or viewDidMount
      />
      {isEventFormModalOpen && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1001 }}>
          <div style={{ background: 'white', padding: '20px', borderRadius: '5px', minWidth: '400px', maxWidth: '600px', zIndex: 1002 }}>
            <EventForm
              eventToEdit={eventToEdit}
              onFormSubmit={handleEventFormSubmit}
              onCancelEdit={handleCloseEventFormModal}
            />
            {/* <button onClick={handleCloseEventFormModal} style={{ marginTop: '10px' }}>Close Form</button> */}
          </div>
        </div>
      )}
    </div>
  );
};

export default DashboardPage;
