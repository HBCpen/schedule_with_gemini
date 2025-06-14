import React from 'react';

const SuggestedTimeSlots = ({ slots, onSlotSelect }) => {
    if (!slots) {
        return null; // Or some fallback UI if slots is undefined for some reason
    }

    return (
        <div style={{ marginTop: '20px', padding: '15px', border: '1px solid #eee', borderRadius: '5px' }}>
            <h4>Suggested Time Slots</h4>
            {slots.length === 0 ? (
                <p>No suggestions available. Enter a query above and click 'Find Time' to see suggestions.</p>
            ) : (
                <ul style={{ listStyleType: 'none', padding: 0 }}>
                    {slots.map((slot, index) => (
                        <li key={index} style={{ marginBottom: '15px', padding: '10px', border: '1px solid #ddd', borderRadius: '4px' }}>
                            <p>
                                <strong>From:</strong> {new Date(slot.start_time).toLocaleString()} <br />
                                <strong>To:</strong> {new Date(slot.end_time).toLocaleString()}
                            </p>
                            {slot.reason && <p style={{ fontSize: '0.9em', color: '#555' }}><strong>Reason:</strong> {slot.reason}</p>}
                            {slot.description && <p style={{ fontSize: '0.9em', color: '#555' }}><strong>Description:</strong> {slot.description}</p>}
                            {/* If there are other details, they can be displayed similarly */}
                            {slot.details && typeof slot.details === 'object' && (
                                <div style={{ marginTop: '5px' }}>
                                    <strong>Details:</strong>
                                    <ul style={{ fontSize: '0.85em', color: '#666' }}>
                                        {Object.entries(slot.details).map(([key, value]) => (
                                            <li key={key}><em>{key}:</em> {String(value)}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            <button
                                onClick={() => onSlotSelect(slot)}
                                style={{ marginTop: '10px', padding: '5px 10px', cursor: 'pointer' }}
                            >
                                Select this slot
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </div>
    );
};

export default SuggestedTimeSlots;
