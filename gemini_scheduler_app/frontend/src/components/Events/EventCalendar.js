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
  textAlign: 'left', // Ensure text is aligned left
};

// Added onViewChange to props
const EventCalendar = ({ events, onEventEdit, onEventDelete, onViewChange }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedEvent, setSelectedEvent] = useState(null);

  const handleEventClick = (clickInfo) => {
    const fcEvent = clickInfo.event;
    const backendEvent = fcEvent.extendedProps.rawEvent; // Get the original event data

    // Use occurrence times if available for display in modal
    const displayStartTime = backendEvent.is_occurrence ? backendEvent.occurrence_start_time : backendEvent.start_time;
    const displayEndTime = backendEvent.is_occurrence ? backendEvent.occurrence_end_time : backendEvent.end_time;

    setSelectedEvent({
      id: backendEvent.id.toString(), // Use actual backend ID (master ID for occurrences)
      title: backendEvent.title,
      start: displayStartTime,
      end: displayEndTime,
      description: backendEvent.description,
      colorTag: backendEvent.color_tag, // Corrected: was colorTag from extendedProps
      is_occurrence: backendEvent.is_occurrence, // Pass this info
      series_start_time: backendEvent.series_start_time, // if it's an occurrence
      rawEvent: backendEvent
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
    if (selectedEvent && selectedEvent.rawEvent) { // selectedEvent.id is master ID here
      // Pass the master event's ID and the rawEvent which contains is_occurrence flag
      onEventDelete(selectedEvent.rawEvent.id, selectedEvent.rawEvent);
    }
    closeModal();
  };

  const formattedEvents = events.map(backendEvent => {
    // Use occurrence-specific start/end times if this event is an occurrence
    const startTime = backendEvent.is_occurrence ? backendEvent.occurrence_start_time : backendEvent.start_time;
    const endTime = backendEvent.is_occurrence ? backendEvent.occurrence_end_time : backendEvent.end_time;

    return {
      // FullCalendar's event 'id' is used for its internal management.
      // We use backendEvent.id (master event's ID) for our operations (edit/delete series).
      // If we needed a unique ID for each visual occurrence on calendar for some FC specific features,
      // we could generate one e.g. `${backendEvent.id}_${startTime}`. But for now, master ID is fine.
      id: backendEvent.id.toString(),
      title: backendEvent.title,
      start: startTime,
      end: endTime,
      allDay: false,
      extendedProps: {
        // Keep all original backend event data here
        description: backendEvent.description,
        colorTag: backendEvent.color_tag, // use the direct property
        is_occurrence: backendEvent.is_occurrence,
        series_start_time: backendEvent.series_start_time,
        // parent_event_id: backendEvent.parent_event_id, // also available
        recurrence_rule: backendEvent.recurrence_rule, // also available
        rawEvent: backendEvent
      },
      // You can change event color based on tag or if it's an occurrence
      backgroundColor: backendEvent.color_tag || (backendEvent.is_occurrence ? '#a0a0a0' : undefined), // Example: grey for occurrences
      borderColor: backendEvent.color_tag || (backendEvent.is_occurrence ? '#808080' : undefined),
    };
  });

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
        editable={true} // Allows drag-n-drop, resize - BEWARE: not handled for recurring events yet
        selectable={true}
        selectMirror={true}
        dayMaxEvents={true}
        datesSet={(dateInfo) => { // FullCalendar callback for view/date changes
          if (onViewChange) {
            onViewChange({ start: dateInfo.start, end: dateInfo.end });
          }
        }}
      />

      {modalOpen && selectedEvent && (
        <div style={modalOverlayStyle} onClick={closeModal}>
          <div style={modalContentStyle} onClick={e => e.stopPropagation()}>
            <h3>{selectedEvent.title}</h3>
            {selectedEvent.is_occurrence && selectedEvent.series_start_time && (
                 <p><small>(Part of a series that started on: {new Date(selectedEvent.series_start_time).toLocaleDateString()})</small></p>
            )}
            <p><strong>Starts:</strong> {new Date(selectedEvent.start).toLocaleString()}</p>
            <p><strong>Ends:</strong> {new Date(selectedEvent.end).toLocaleString()}</p>
            <p><strong>Description:</strong> {selectedEvent.description || 'N/A'}</p>
            {selectedEvent.colorTag && <p><strong>Tag:</strong> <span style={{color: selectedEvent.colorTag, fontWeight:'bold'}}>{selectedEvent.colorTag}</span></p>}

            <hr style={{margin: "10px 0"}}/>
            <button onClick={handleEditClick} style={{marginRight: '10px'}}>Edit Series</button>
            <button onClick={handleDeleteClick} style={{marginRight: '10px'}}>Delete Series</button>
            <button onClick={closeModal}>Close</button>
          </div>
        </div>
      )}
    </>
  );
};

export default EventCalendar;
