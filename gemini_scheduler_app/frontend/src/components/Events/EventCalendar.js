import React, { useState } from 'react'; // Import useState
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';

// Basic modal styles
const modalOverlayStyle = {
  position: 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0, 0, 0, 0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000, // Ensure it's on top
};

const modalContentStyle = {
  background: 'white',
  padding: '20px',
  borderRadius: '5px',
  minWidth: '300px',
  maxWidth: '500px',
};

const EventCalendar = ({ events, onEventEdit, onEventDelete }) => { // Destructure props
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);

  const handleEventClick = (clickInfo) => {
    const event = clickInfo.event;
    setSelectedEvent({
      id: event.id, // FullCalendar event ID, which we set from backend event.id
      title: event.title,
      start: event.startStr, // Use startStr for string representation
      end: event.endStr,     // Use endStr for string representation
      description: event.extendedProps.description,
      colorTag: event.extendedProps.colorTag,
      rawEvent: event.extendedProps.rawEvent // Store the original event object
    });
    setModalOpen(true);
  };

  const closeModal = () => {
    setModalOpen(false);
    setSelectedEvent(null);
  };

  const handleEditClick = () => {
    if (selectedEvent && selectedEvent.rawEvent) {
      onEventEdit(selectedEvent.rawEvent); // Pass the original event object
    }
    closeModal();
  };

  const handleDeleteClick = () => {
    if (selectedEvent && selectedEvent.id) {
      onEventDelete(selectedEvent.id); // Pass the event ID
    }
    closeModal();
  };

  const formattedEvents = events.map(backendEvent => ({
    id: backendEvent.id.toString(), // Ensure ID is a string for FullCalendar if it's not already
    title: backendEvent.title,
    start: backendEvent.start_time,
    end: backendEvent.end_time,
    allDay: false, // Assuming events are not all-day by default
    extendedProps: {
      description: backendEvent.description,
      colorTag: backendEvent.color_tag,
      rawEvent: backendEvent // Store the original backend event
    }
  }));

  return (
    <> {/* Use Fragment to return multiple elements */}
      <FullCalendar
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        headerToolbar={{
          left: 'prev,next today',
          center: 'title',
          right: 'dayGridMonth,timeGridWeek,timeGridDay'
        }}
        events={formattedEvents}
        eventClick={handleEventClick}
        editable={true}
        selectable={true}
        selectMirror={true}
        dayMaxEvents={true}
      />

      {modalOpen && selectedEvent && (
        <div style={modalOverlayStyle} onClick={closeModal}> {/* Close modal on overlay click */}
          <div style={modalContentStyle} onClick={e => e.stopPropagation()}> {/* Prevent content click from closing */}
            <h3>{selectedEvent.title}</h3>
            <p><strong>Starts:</strong> {new Date(selectedEvent.start).toLocaleString()}</p>
            <p><strong>Ends:</strong> {new Date(selectedEvent.end).toLocaleString()}</p>
            <p><strong>Description:</strong> {selectedEvent.description || 'N/A'}</p>
            {selectedEvent.colorTag && <p><strong>Tag:</strong> <span style={{color: selectedEvent.colorTag}}>{selectedEvent.colorTag}</span></p>}

            <button onClick={handleEditClick} style={{marginRight: '10px'}}>Edit</button>
            <button onClick={handleDeleteClick} style={{marginRight: '10px'}}>Delete</button>
            <button onClick={closeModal}>Close</button>
          </div>
        </div>
      )}
    </>
  );
};

export default EventCalendar;
