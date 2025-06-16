import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from './Dashboard';
import eventService from '../services/eventService';
import authService from '../services/authService';

// Mock the services
jest.mock('../services/eventService', () => ({
    __esModule: true, // This is important for modules with default exports
    default: {
        createEvent: jest.fn(),
        getEvents: jest.fn(),
        getEventById: jest.fn(),
        updateEvent: jest.fn(),
        deleteEvent: jest.fn(),
        parseNaturalLanguageEvent: jest.fn(),
        getEventRelatedInfo: jest.fn(),
        searchEvents: jest.fn(),
        findFreeTime: jest.fn(),
        getEventSummary: jest.fn(),
    },
}));
jest.mock('../services/authService');

// Mock child components that are not directly under test or complex
// For EventCalendar, we need to be able to simulate its onViewChange callback.
const mockSetViewChange = jest.fn();
function MockEventCalendar({ onViewChange }) {
    // Store the onViewChange callback so we can call it from tests
    mockSetViewChange(onViewChange);
    return <div data-testid="event-calendar">Event Calendar Mock</div>;
}
jest.mock('./Events/EventCalendar', () => MockEventCalendar);

jest.mock('./Events/EventList', () => ({ events }) => <div data-testid="event-list">{events.length} events list mock</div>);

// For EventForm, we want to simulate its onFormSubmit callback
// const mockFormSubmit = jest.fn(); // Not directly used, onFormSubmit is passed to the mock
function MockEventForm({ onFormSubmit }) {
    // Allow tests to trigger form submission
    // This is a simplified mock; real form would have its own submit button
    global.triggerEventFormSubmit = onFormSubmit;
    return <div data-testid="event-form">Event Form Mock</div>;
}
jest.mock('./Events/EventForm', () => MockEventForm);


const initialMockEvents = [
    { id: '1', title: 'Event 1', description: 'First event', start_time: '2024-07-01T10:00:00Z', end_time: '2024-07-01T11:00:00Z', color_tag: 'work' },
    { id: '2', title: 'Event 2', description: 'Second event about project', start_time: '2024-07-02T14:00:00Z', end_time: '2024-07-02T15:00:00Z', color_tag: 'personal' },
    { id: '3', title: 'Another Project Meeting', description: 'Third event', start_time: '2024-07-03T16:00:00Z', end_time: '2024-07-03T17:00:00Z', color_tag: 'work,project' },
];

describe('Dashboard Functionality', () => {

    beforeEach(() => {
        // Reset mocks before each test
        // eventService.getEvents.mockReset(); // Will be set per test or with mockResolvedValueOnce
        jest.clearAllMocks(); // Clears all mocks, including call counts

        authService.getCurrentUserToken.mockReturnValue('fake-token'); // Assume user is logged in

        // Default mock for getEvents (called on initial load in most tests)
        eventService.getEvents.mockResolvedValue({ data: [...initialMockEvents] });
        // Default mock for getEventSummary (called on initial load)
        eventService.getEventSummary.mockResolvedValue({ data: { summary: "Default summary for today." } });


        // Reset the onViewChange callback store for EventCalendar mock
        mockSetViewChange.mockClear();
        // Clear any previous global trigger
        if (global.triggerEventFormSubmit) delete global.triggerEventFormSubmit;
    });

    // --- Search Functionality Tests ---
    // (Keep existing search tests here, ensure they use initialMockEvents for consistency if needed)
    // Example: Adjust one search test to reflect this structure
    test('renders search input fields and buttons', async () => {
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled());
        // ... (rest of the assertions from existing search test)
        expect(screen.getByPlaceholderText('Keywords (title, description)')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Tags (comma-separated)')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Clear Search' })).toBeInTheDocument();
    });

    // --- Event Summary Tests ---
    test('fetches and displays event summary on mount', async () => {
        const mockSummary = "Today's key activities include important meetings.";
        eventService.getEventSummary.mockResolvedValueOnce({ data: { summary: mockSummary } });
        render(<Dashboard />);

        // Wait for summary to be loaded and displayed
        await waitFor(() => {
            expect(screen.getByText(mockSummary)).toBeInTheDocument();
        });
        expect(eventService.getEventSummary).toHaveBeenCalledWith(new Date().toISOString().split('T')[0]);
        expect(screen.queryByText('Loading summary...')).not.toBeInTheDocument();
        expect(screen.queryByText(/Error:/)).not.toBeInTheDocument();
    });

    test('displays loading message while fetching summary', async () => {
        eventService.getEventSummary.mockImplementationOnce(() =>
            new Promise(resolve => setTimeout(() => resolve({ data: { summary: "Late summary" } }), 100))
        );
        render(<Dashboard />);

        // Check for loading message immediately
        expect(screen.getByText('Loading summary...')).toBeInTheDocument();

        // Wait for the summary to eventually load to ensure the loading message disappears
        await waitFor(() => {
            expect(screen.getByText("Late summary")).toBeInTheDocument();
        }, { timeout: 500 }); // Increased timeout for safety with mock delay
         expect(screen.queryByText('Loading summary...')).not.toBeInTheDocument();
    });

    test('displays error message if fetching summary fails', async () => {
        const errorMessage = "Failed to retrieve summary.";
        eventService.getEventSummary.mockRejectedValueOnce({ response: { data: { msg: errorMessage } } });
        render(<Dashboard />);

        await waitFor(() => {
            expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
        });
        expect(screen.queryByText('Loading summary...')).not.toBeInTheDocument();
        expect(screen.queryByText("Default summary for today.")).not.toBeInTheDocument(); // Ensure no old summary is shown
    });

    test('displays "No summary available" message when summary is empty and no error/loading', async () => {
        eventService.getEventSummary.mockResolvedValueOnce({ data: { summary: "" } }); // Empty summary
        render(<Dashboard />);

        await waitFor(() => {
            expect(screen.getByText("No summary available for today.")).toBeInTheDocument();
        });
        expect(screen.queryByText('Loading summary...')).not.toBeInTheDocument();
        expect(screen.queryByText(/Error:/)).not.toBeInTheDocument();
    });


    // --- Search Functionality Tests (Existing) ---
    test('allows typing into keyword and tags fields', async () => {
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled());

        const keywordInput = screen.getByPlaceholderText('Keywords (title, description)');
        fireEvent.change(keywordInput, { target: { value: 'test keyword' } });
        expect(keywordInput.value).toBe('test keyword');

        const tagsInput = screen.getByPlaceholderText('Tags (comma-separated)');
        fireEvent.change(tagsInput, { target: { value: 'work,test' } });
        expect(tagsInput.value).toBe('work,test');
    });

    test('calls eventService.searchEvents with correct params on search click', async () => {
        eventService.searchEvents.mockResolvedValue({ data: [] });
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled());

        fireEvent.change(screen.getByPlaceholderText('Keywords (title, description)'), { target: { value: 'project' } });
        fireEvent.change(screen.getByPlaceholderText('Tags (comma-separated)'), { target: { value: 'work' } });

        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => {
            expect(eventService.searchEvents).toHaveBeenCalledWith({
                q: 'project',
                tags: 'work'
            });
        });
    });

    test.skip('updates events state with search results', async () => {
        // Specific mocks for this test
        const searchResults = [initialMockEvents[2]]; // Contains 1 event
        eventService.searchEvents.mockResolvedValue({ data: searchResults });
        // Mock the getEvents call that happens due to isSearching changing after search
        eventService.getEvents.mockResolvedValueOnce({ data: [...initialMockEvents] }) // Initial load
                                .mockResolvedValueOnce({ data: [] }); // Post-search fetchEvents call

        render(<Dashboard />);
        await waitFor(() => expect(screen.getByTestId('event-list').textContent).toContain('3 events list mock'));

        fireEvent.change(screen.getByPlaceholderText('Keywords (title, description)'), { target: { value: 'Another' } });

        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Search' }));
        });

        await waitFor(() => {
            expect(screen.getByTestId('event-list').textContent).toContain('1 events list mock');
        });
        // Ensure searchEvents was called
        expect(eventService.searchEvents).toHaveBeenCalledWith({ q: 'Another' });
    });

    test.skip('clears search fields and reverts to original events on clear search click', async () => {
        // Mock sequence for eventService.getEvents:
        // 1. Initial load (from beforeEach or explicitly here)
        eventService.getEvents.mockResolvedValueOnce({ data: [...initialMockEvents] });

        render(<Dashboard />);
        await waitFor(() => expect(screen.getByTestId('event-list').textContent).toContain('3 events list mock'));

        const keywordInput = screen.getByPlaceholderText('Keywords (title, description)');

        // 2. Perform a search
        const searchResultOneEvent = [initialMockEvents[0]];
        eventService.searchEvents.mockResolvedValue({ data: searchResultOneEvent });
        // Mock the fetchEvents call triggered by setIsSearching(true) after search
        eventService.getEvents.mockResolvedValueOnce({ data: [] }); // This call should not affect originalEvents

        await act(async () => {
            fireEvent.change(keywordInput, { target: { value: 'Event 1' } });
            fireEvent.click(screen.getByRole('button', { name: 'Search' }));
        });
        await waitFor(() => expect(screen.getByTestId('event-list').textContent).toContain('1 events list mock'));

        // 3. Clear the search
        // Mock the fetchEvents call triggered by setIsSearching(false) after clearing - this should restore original
        eventService.getEvents.mockResolvedValueOnce({ data: [...initialMockEvents] });

        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Clear Search' }));
        });

        await waitFor(() => {
            expect(keywordInput.value).toBe('');
            expect(screen.getByTestId('event-list').textContent).toContain('3 events list mock');
        });
    });

    test('displays error message if search API call fails', async () => {
        eventService.searchEvents.mockRejectedValueOnce({ response: { data: { msg: 'Search failed' } } });
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled());

        fireEvent.change(screen.getByPlaceholderText('Keywords (title, description)'), { target: { value: 'test' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => {
            expect(screen.getByText('Search failed')).toBeInTheDocument();
        });
    });

    test('displays error if search is clicked with no criteria', async () => {
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled());

        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => {
            expect(screen.getByText('Please enter at least one search criteria.')).toBeInTheDocument();
        });
        expect(eventService.searchEvents).not.toHaveBeenCalled();
    });


    // --- Recurrence Functionality Tests ---

    test('fetches events with date range when calendar view changes', async () => {
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalledTimes(1)); // Initial call

        // Simulate calendar view change by calling the captured onViewChange callback
        const calendarViewChangeCallback = mockSetViewChange.mock.calls[0][0];
        const newStartDate = new Date('2024-08-01T00:00:00.000Z');
        const newEndDate = new Date('2024-08-31T00:00:00.000Z');

        // Clear mock calls from initial load to focus on this interaction
        eventService.getEvents.mockClear();
        eventService.getEvents.mockResolvedValue({ data: [] }); // New response for this call

        await act(async () => {
            calendarViewChangeCallback({ start: newStartDate, end: newEndDate });
        });

        await waitFor(() => {
            expect(eventService.getEvents).toHaveBeenCalledWith({
                start_date: '2024-08-01',
                end_date: '2024-08-31'
            });
        });
    });

    test('refetches events for current view after EventForm submission', async () => {
        render(<Dashboard />);
        // Wait for initial fetch (e.g., July 2024 default)
        const defaultStartDate = new Date(new Date().getFullYear(), new Date().getMonth(), 1);
        const defaultEndDate = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0);

        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalledWith(expect.objectContaining({
            start_date: defaultStartDate.toISOString().split('T')[0],
            end_date: defaultEndDate.toISOString().split('T')[0]
        })));

        eventService.getEvents.mockClear(); // Clear calls from initial load
        eventService.getEvents.mockResolvedValue({data: []}); // Mock for the refetch

        // First, make the form visible
        fireEvent.click(screen.getByRole('button', { name: 'Create New Event Manually' }));

        // Simulate EventForm submission
        expect(global.triggerEventFormSubmit).toBeDefined(); // Now EventForm mock should have been rendered and set this
        await act(async () => {
            global.triggerEventFormSubmit(); // Simulate the form being submitted
        });

        await waitFor(() => {
            // Expect getEvents to be called again with the same (default) date range
            expect(eventService.getEvents).toHaveBeenCalledWith(expect.objectContaining({
                 start_date: defaultStartDate.toISOString().split('T')[0],
                 end_date: defaultEndDate.toISOString().split('T')[0]
            }));
        });
    });

    test('passes events with occurrence data to EventCalendar and EventList', async () => {
        const eventsWithOccurrences = [
            ...initialMockEvents,
            {
                id: '4', title: 'Recurring Event', start_time: '2024-07-05T10:00:00Z', end_time: '2024-07-05T11:00:00Z',
                recurrence_rule: 'FREQ=DAILY;COUNT=2',
                // This is an expanded occurrence from backend
                is_occurrence: true,
                occurrence_start_time: '2024-07-06T10:00:00Z',
                occurrence_end_time: '2024-07-06T11:00:00Z',
                parent_event_id: '4' // Master ID
            }
        ];
        eventService.getEvents.mockResolvedValue({ data: eventsWithOccurrences });

        render(<Dashboard />);
        // Wait for the events to be loaded and displayed based on the mock
        await waitFor(() => {
            expect(screen.getByTestId('event-list').textContent).toContain(`${eventsWithOccurrences.length} events list mock`);
        });
        // More specific tests would involve inspecting props passed to the actual (unmocked) EventList/Calendar
        // or having the mocks render more specific data.
    });

});

// Ensure App tests are separate or correctly managed if in same file
// describe('App Component', () => { ... }); // Moved to its own section or file ideally
// For this task, keeping the App tests from previous step is fine.
// --- App Component Tests (from previous step, ensure they are not duplicated if running separately) ---
// Describe block for App component tests removed from here as it belongs in App.test.js
