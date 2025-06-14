import React, { useState, useEffect } from 'react'; // Import useState and useEffect
import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import timeGridPlugin from '@fullcalendar/timegrid';
import interactionPlugin from '@fullcalendar/interaction';
import eventService from '../../services/eventService'; // Import eventService

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
  const [relatedInfo, setRelatedInfo] = useState(null);
  const [relatedInfoLoading, setRelatedInfoLoading] = useState(false);
  const [relatedInfoError, setRelatedInfoError] = useState('');

  useEffect(() => {
    if (selectedEvent && selectedEvent.rawEvent && selectedEvent.rawEvent.id && modalOpen) {
        const fetchRelatedInfo = async (eventId) => {
            setRelatedInfoLoading(true);
            setRelatedInfo(null);
            setRelatedInfoError('');
            try {
                const response = await eventService.getEventRelatedInfo(eventId);
                // Ensure response and response.data exist before trying to access properties
                if (response && response.data && response.status === 200) {
                    setRelatedInfo(response.data);
                } else {
                    // Handle cases where response.data might be undefined or response status is not 200
                    const errorMessage = response && response.data ? (response.data.error || response.data.detail) : 'Failed to load related information.';
                    setRelatedInfoError(errorMessage || 'Failed to load related information.');
                }
            } catch (error) {
                console.error('Error fetching related info:', error);
                // Ensure error.response and error.response.data exist
                const errorMessage = error.response && error.response.data ? (error.response.data.error || error.response.data.detail) : 'An error occurred while fetching related information.';
                setRelatedInfoError(errorMessage || 'An error occurred while fetching related information.');
            } finally {
                setRelatedInfoLoading(false);
            }
        };
        fetchRelatedInfo(selectedEvent.rawEvent.id);
    } else {
        // Clear related info when modal is closed or no event selected
        setRelatedInfo(null);
        setRelatedInfoError('');
    }
  }, [selectedEvent, modalOpen]); // Re-run if selectedEvent or modalOpen changes

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
            <h4>Related Information</h4>
            {relatedInfoLoading && <p>Loading related info...</p>}
            {relatedInfoError && <p style={{color: 'red'}}>{relatedInfoError}</p>}
            {relatedInfo && !relatedInfoLoading && !relatedInfoError && (
                <div>
                    {/* Weather Section */}
                    {relatedInfo.weather && (
                        <div style={{marginBottom: '10px'}}>
                            <strong>Weather ({relatedInfo.weather.location} on {relatedInfo.weather.forecast_date}):</strong>
                            <p>{relatedInfo.weather.summary}</p>
                            <p>Condition: {relatedInfo.weather.condition}, Temp: {relatedInfo.weather.temperature_low}° - {relatedInfo.weather.temperature_high}°</p>
                            <p>Precipitation: {relatedInfo.weather.precipitation_chance}</p>
                        </div>
                    )}

                    {/* Traffic Section */}
                    {relatedInfo.traffic && (
                        <div style={{marginBottom: '10px'}}>
                            <strong>Traffic ({relatedInfo.traffic.location} around {relatedInfo.traffic.assessment_time}):</strong>
                            <p>{relatedInfo.traffic.summary}</p>
                            <p>Congestion: {relatedInfo.traffic.congestion_level}</p>
                            <p>Advisory: {relatedInfo.traffic.expected_travel_advisory}</p>
                        </div>
                    )}

                    {/* Suggestions Section (Restaurants, etc.) */}
                    {relatedInfo.suggestions && relatedInfo.suggestions.length > 0 && (
                        <div style={{marginBottom: '10px'}}>
                            <strong>Suggestions:</strong>
                            <ul>
                                {relatedInfo.suggestions.map((item, index) => (
                                    <li key={index}>
                                        {item.type}: <strong>{item.name}</strong> - {item.details}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Related Content Section (Articles/Documents) */}
                    {relatedInfo.related_content && relatedInfo.related_content.length > 0 && (
                        <div style={{marginBottom: '10px'}}>
                            <strong>Related Content:</strong>
                            <ul>
                                {relatedInfo.related_content.map((content, index) => (
                                    <li key={index}>
                                        <strong>{content.title}</strong> ({content.type})
                                        {content.source && <span> - Source: {content.source}</span>}
                                        {content.url && <div><a href={content.url} target="_blank" rel="noopener noreferrer">Link</a></div>}
                                        {content.summary && <p>{content.summary}</p>}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Message if no specific related info sections have content */}
                    {(!relatedInfo.weather && !relatedInfo.traffic && (!relatedInfo.suggestions || relatedInfo.suggestions.length === 0) && (!relatedInfo.related_content || relatedInfo.related_content.length === 0)) && (
                        <p>No specific related information available.</p>
                    )}
                </div>
            )}
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
