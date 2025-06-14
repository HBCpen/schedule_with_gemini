import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import EventCalendar from './EventCalendar';
import eventService from '../../services/eventService';

// Mock the eventService
jest.mock('../../services/eventService');

// Mock FullCalendar components to simplify testing
jest.mock('@fullcalendar/react', () => {
  // A simple mock: renders a placeholder and calls eventClick if an event is clicked (simulated)
  return function FullCalendarMock({ events, eventClick }) {
    return (
      <div data-testid="fullcalendar-mock">
        {events.map(event => (
          <div key={event.id || event.title} data-testid={`event-${event.rawEvent?.id || event.id}`} onClick={() => eventClick ? eventClick({ event: { ...event, extendedProps: { rawEvent: event.rawEvent } } }) : null}>
            {event.title}
          </div>
        ))}
      </div>
    );
  };
});
jest.mock('@fullcalendar/daygrid', () => ({})); // Mock plugin
jest.mock('@fullcalendar/timegrid', () => ({})); // Mock plugin
jest.mock('@fullcalendar/interaction', () => ({})); // Mock plugin


const mockEvents = [
  {
    id: '1', // This ID is used by FullCalendar, rawEvent.id is the backend ID
    title: 'Test Event 1',
    start: new Date().toISOString(),
    end: new Date(new Date().getTime() + 3600 * 1000).toISOString(),
    description: 'Description for event 1',
    color_tag: 'work',
    rawEvent: { // This is the structure the component expects for backend data
      id: 'event123', // Backend ID
      title: 'Test Event 1',
      start_time: new Date().toISOString(),
      end_time: new Date(new Date().getTime() + 3600 * 1000).toISOString(),
      description: 'Description for event 1',
      color_tag: 'work',
      location: 'Test Location 1', // Add location for related info
    }
  },
  {
    id: '2',
    title: 'Test Event 2 for Error',
    start: new Date(new Date().getTime() + 2 * 3600 * 1000).toISOString(),
    end: new Date(new Date().getTime() + 3 * 3600 * 1000).toISOString(),
    description: 'Description for event 2',
    color_tag: 'personal',
    rawEvent: {
      id: 'event456',
      title: 'Test Event 2 for Error',
      start_time: new Date(new Date().getTime() + 2 * 3600 * 1000).toISOString(),
      end_time: new Date(new Date().getTime() + 3 * 3600 * 1000).toISOString(),
      description: 'Description for event 2',
      color_tag: 'personal',
      location: 'Test Location 2',
    }
  }
];

const mockOnEventEdit = jest.fn();
const mockOnEventDelete = jest.fn();
const mockOnViewChange = jest.fn();

describe('EventCalendar Related Information', () => {
  beforeEach(() => {
    // Reset mocks before each test
    jest.clearAllMocks();
    eventService.getEventRelatedInfo.mockResolvedValue({ data: {}, status: 200 }); // Default mock
  });

  test('displays loading state initially for related information', async () => {
    eventService.getEventRelatedInfo.mockImplementation(() => {
      return new Promise(() => {}); // Promise that never resolves to keep loading state
    });

    render(
      <EventCalendar
        events={mockEvents}
        onEventEdit={mockOnEventEdit}
        onEventDelete={mockOnEventDelete}
        onViewChange={mockOnViewChange}
      />
    );

    // Simulate clicking the first event to open the modal
    // Using the mock, we find the element by its test ID derived from rawEvent.id
    fireEvent.click(screen.getByTestId('event-event123'));

    expect(await screen.findByText('Related Information')).toBeInTheDocument(); // Modal section title
    expect(await screen.findByText('Loading related info...')).toBeInTheDocument();
  });

  test('displays related information on successful fetch', async () => {
    const mockRelatedInfoData = {
      weather: { location: 'Test City', forecast_date: '2023-01-01', summary: 'Very Sunny', condition: 'Clear Sky', temperature_low: '10', temperature_high: '20', precipitation_chance: '0%' },
      traffic: { location: 'Test City', assessment_time: '10:00', summary: 'Light traffic conditions', congestion_level: 'Low', expected_travel_advisory: 'None' },
      suggestions: [{ type: 'Restaurant', name: 'Test Cafe Mocha', details: 'Great coffee' }],
      related_content: [{ type: 'article', title: 'Relevant Test Article', source: 'Test Source', url: 'http://example.com/article' }]
    };
    eventService.getEventRelatedInfo.mockResolvedValue({ data: mockRelatedInfoData, status: 200 });

    render(
      <EventCalendar
        events={mockEvents}
        onEventEdit={mockOnEventEdit}
        onEventDelete={mockOnEventDelete}
        onViewChange={mockOnViewChange}
      />
    );

    fireEvent.click(screen.getByTestId('event-event123'));

    await waitFor(() => {
      expect(screen.getByText('Very Sunny')).toBeInTheDocument(); // Weather summary
      expect(screen.getByText('Light traffic conditions')).toBeInTheDocument(); // Traffic summary
      expect(screen.getByText('Test Cafe Mocha')).toBeInTheDocument(); // Suggestion name
      expect(screen.getByText('Relevant Test Article')).toBeInTheDocument(); // Related content title
      expect(screen.getByText('Link').closest('a')).toHaveAttribute('href', 'http://example.com/article');
    });
  });

  test('displays error message on fetch failure for related information', async () => {
    eventService.getEventRelatedInfo.mockRejectedValue({
      response: { data: { error: 'Failed to fetch related details' } }
    });

    render(
      <EventCalendar
        events={mockEvents}
        onEventEdit={mockOnEventEdit}
        onEventDelete={mockOnEventDelete}
        onViewChange={mockOnViewChange}
      />
    );

    // Use the second event for this test to ensure clean state if needed, though mock is per test
    fireEvent.click(screen.getByTestId('event-event456'));

    await waitFor(() => {
      expect(screen.getByText('Failed to fetch related details')).toBeInTheDocument();
    });
  });

  test('displays "No specific related information available" when data is empty/null', async () => {
    const mockEmptyRelatedInfo = {
      weather: null,
      traffic: null,
      suggestions: [],
      related_content: []
    };
    eventService.getEventRelatedInfo.mockResolvedValue({ data: mockEmptyRelatedInfo, status: 200 });

    render(
      <EventCalendar
        events={mockEvents}
        onEventEdit={mockOnEventEdit}
        onEventDelete={mockOnEventDelete}
        onViewChange={mockOnViewChange}
      />
    );

    fireEvent.click(screen.getByTestId('event-event123'));

    await waitFor(() => {
      expect(screen.getByText('No specific related information available.')).toBeInTheDocument();
    });
  });

  test('getEventRelatedInfo is called with correct event ID', async () => {
    eventService.getEventRelatedInfo.mockResolvedValue({ data: {}, status: 200 }); // Basic success response

    render(
      <EventCalendar
        events={mockEvents} // mockEvents[0].rawEvent.id is 'event123'
        onEventEdit={mockOnEventEdit}
        onEventDelete={mockOnEventDelete}
        onViewChange={mockOnViewChange}
      />
    );

    fireEvent.click(screen.getByTestId('event-event123'));

    await waitFor(() => {
      expect(eventService.getEventRelatedInfo).toHaveBeenCalledWith('event123');
    });
  });
});
