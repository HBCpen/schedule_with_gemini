import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from './Dashboard';
import eventService from '../services/eventService';
import authService from '../services/authService';

// Mock the services
jest.mock('../services/eventService');
jest.mock('../services/authService');

// Mock child components that are not directly under test or complex
// For EventCalendar, we need to be able to simulate its onViewChange callback.
const mockSetViewChange = jest.fn();
const MockEventCalendar = jest.fn(({ onViewChange }) => {
    // Store the onViewChange callback so we can call it from tests
    mockSetViewChange(onViewChange);
    return <div data-testid="event-calendar">Event Calendar Mock</div>;
});
jest.mock('./Events/EventCalendar', () => MockEventCalendar);
jest.mock('./Events/EventList', () => ({ events }) => <div data-testid="event-list">{events.length} events list mock</div>);
// For EventForm, we want to simulate its onFormSubmit callback
const mockFormSubmit = jest.fn();
const MockEventForm = jest.fn(({ onFormSubmit }) => {
    // Allow tests to trigger form submission
    // This is a simplified mock; real form would have its own submit button
    global.triggerEventFormSubmit = onFormSubmit;
    return <div data-testid="event-form">Event Form Mock</div>;
});
jest.mock('./Events/EventForm', () => MockEventForm);


const initialMockEvents = [
    { id: '1', title: 'Event 1', description: 'First event', start_time: '2024-07-01T10:00:00Z', end_time: '2024-07-01T11:00:00Z', color_tag: 'work' },
    { id: '2', title: 'Event 2', description: 'Second event about project', start_time: '2024-07-02T14:00:00Z', end_time: '2024-07-02T15:00:00Z', color_tag: 'personal' },
    { id: '3', title: 'Another Project Meeting', description: 'Third event', start_time: '2024-07-03T16:00:00Z', end_time: '2024-07-03T17:00:00Z', color_tag: 'work,project' },
];

describe('Dashboard Functionality', () => {

    beforeEach(() => {
        // Reset mocks before each test
        eventService.getEvents.mockReset();
        eventService.searchEvents.mockReset();
        eventService.createEvent.mockReset(); // For potential form submissions
        eventService.updateEvent.mockReset(); // For potential form submissions
        eventService.getEventSummary.mockReset(); // Reset summary mock
        authService.getCurrentUserToken.mockReturnValue('fake-token'); // Assume user is logged in

        // Default mock for getEvents (called on initial load)
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

    test('updates events state with search results', async () => {
        const searchResults = [initialMockEvents[2]];
        eventService.searchEvents.mockResolvedValue({ data: searchResults });

        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled());

        fireEvent.change(screen.getByPlaceholderText('Keywords (title, description)'), { target: { value: 'Another' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => {
            expect(screen.getByTestId('event-list').textContent).toContain('1 events list mock');
        });
    });

    test('clears search fields and reverts to original events on clear search click', async () => {
        eventService.searchEvents.mockResolvedValue({ data: [initialMockEvents[0]] });
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalledTimes(1));

        expect(screen.getByTestId('event-list').textContent).toContain('3 events list mock');

        const keywordInput = screen.getByPlaceholderText('Keywords (title, description)');
        fireEvent.change(keywordInput, { target: { value: 'Event 1' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => expect(eventService.searchEvents).toHaveBeenCalled());
        expect(screen.getByTestId('event-list').textContent).toContain('1 events list mock');

        fireEvent.click(screen.getByRole('button', { name: 'Clear Search' }));

        await waitFor(() => {
            expect(keywordInput.value).toBe('');
        });
        expect(screen.getByTestId('event-list').textContent).toContain('3 events list mock');
        expect(eventService.getEvents).toHaveBeenCalledTimes(1);
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

        calendarViewChangeCallback({ start: newStartDate, end: newEndDate });

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

        // Simulate EventForm submission
        // The mock EventForm captures its onFormSubmit prop in `global.triggerEventFormSubmit`
        expect(global.triggerEventFormSubmit).toBeDefined();
        global.triggerEventFormSubmit(); // Simulate the form being submitted

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
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled());

        // EventList mock displays the number of events
        expect(screen.getByTestId('event-list').textContent).toContain(`${eventsWithOccurrences.length} events list mock`);
        // More specific tests would involve inspecting props passed to the actual (unmocked) EventList/Calendar
        // or having the mocks render more specific data.
    });

});

// Ensure App tests are separate or correctly managed if in same file
// describe('App Component', () => { ... }); // Moved to its own section or file ideally
// For this task, keeping the App tests from previous step is fine.
// --- App Component Tests (from previous step, ensure they are not duplicated if running separately) ---
describe('App Component', () => {
    test('renders Dashboard when user is logged in', () => {
        authService.getCurrentUserToken.mockReturnValue('fake-token');
        render(<App />);
        expect(screen.getByText('My Schedule')).toBeInTheDocument();
    });

    test('renders Login when user is not logged in', () => {
        authService.getCurrentUserToken.mockReturnValue(null);
        render(<App />);
        expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    });
});
        { id: '2', title: 'Event 2', description: 'Second event about project', start_time: '2024-07-02T14:00:00Z', end_time: '2024-07-02T15:00:00Z', color_tag: 'personal' },
        { id: '3', title: 'Another Project Meeting', description: 'Third event', start_time: '2024-07-03T16:00:00Z', end_time: '2024-07-03T17:00:00Z', color_tag: 'work,project' },
    ];

    beforeEach(() => {
        // Reset mocks before each test
        eventService.getEvents.mockReset();
        eventService.searchEvents.mockReset();
        authService.getCurrentUserToken.mockReturnValue('fake-token'); // Assume user is logged in

        // Default mock for getEvents (called on initial load)
        eventService.getEvents.mockResolvedValue({ data: mockEvents });
    });

    test('renders search input fields and buttons', async () => {
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled()); // Wait for initial load

        expect(screen.getByPlaceholderText('Keywords (title, description)')).toBeInTheDocument();
        // For date inputs, it's harder to get by placeholder if not set. Check for their existence.
        // Assuming date inputs don't have specific labels that are easy to query without being too fragile.
        const dateInputs = screen.getAllByRole('textbox'); // This is a bit generic, refine if possible or add test-ids
        // A better way might be to find by associated label text if available or add test-ids.
        // For now, we'll assume their presence. A more robust query would be:
        // expect(screen.getByLabelText('Start Date Label Text if any')).toBeInTheDocument();

        expect(screen.getByPlaceholderText('Tags (comma-separated)')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Search' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Clear Search' })).toBeInTheDocument();
    });

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
        eventService.searchEvents.mockResolvedValue({ data: [] }); // Mock search response
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled());

        fireEvent.change(screen.getByPlaceholderText('Keywords (title, description)'), { target: { value: 'project' } });
        // For date inputs, React Testing Library handles date input changes directly on the input element
        // Assuming the date inputs are the first two of their kind if not specifically labeled for query
        const dateInputs = screen.getAllByRole('textbox'); // Re-evaluating this selector, might need test-ids for dates.
                                                          // Let's assume for now they are not being set in this test.
        // For a more robust way to find date inputs, use specific labels or test-ids.
        // For this test, we'll focus on keyword and tags.
        // Example for date: fireEvent.change(screen.getByLabelText('Start Date:'), { target: { value: '2024-07-01' } });


        fireEvent.change(screen.getByPlaceholderText('Tags (comma-separated)'), { target: { value: 'work' } });

        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => {
            expect(eventService.searchEvents).toHaveBeenCalledWith({
                q: 'project',
                tags: 'work'
                // start_date: '2024-07-01', // if date was set
                // end_date: '2024-07-03',   // if date was set
            });
        });
    });

    test('updates events state with search results', async () => {
        const searchResults = [mockEvents[2]]; // "Another Project Meeting"
        eventService.searchEvents.mockResolvedValue({ data: searchResults });

        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalled()); // Initial load

        fireEvent.change(screen.getByPlaceholderText('Keywords (title, description)'), { target: { value: 'Another' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => {
            // The EventList mock displays the number of events.
            // Check if the list reflects the search result.
            // This depends on EventList mock correctly using the events prop.
            // For this test, we'll assume the Dashboard's 'events' state is updated.
            // A more direct test would be to check the props passed to EventList mock,
            // or to have EventList mock render titles to check specific content.
            expect(screen.getByTestId('event-list').textContent).toContain('1 events list mock');
        });
         // To be more specific, you would ideally check the content of the list
         // For example, if EventList mock rendered titles:
         // expect(screen.getByText('Another Project Meeting')).toBeInTheDocument();
    });

    test('clears search fields and reverts to original events on clear search click', async () => {
        eventService.searchEvents.mockResolvedValue({ data: [mockEvents[0]] }); // Search returns 1 event
        render(<Dashboard />);
        await waitFor(() => expect(eventService.getEvents).toHaveBeenCalledTimes(1)); // Initial load with 3 events (mockEvents)

        // Check initial state (mockEvents has 3 items)
        expect(screen.getByTestId('event-list').textContent).toContain('3 events list mock');


        const keywordInput = screen.getByPlaceholderText('Keywords (title, description)');
        fireEvent.change(keywordInput, { target: { value: 'Event 1' } });
        fireEvent.click(screen.getByRole('button', { name: 'Search' }));

        await waitFor(() => expect(eventService.searchEvents).toHaveBeenCalled());
        // After search, list shows 1 event
        expect(screen.getByTestId('event-list').textContent).toContain('1 events list mock');


        fireEvent.click(screen.getByRole('button', { name: 'Clear Search' }));

        await waitFor(() => {
            expect(keywordInput.value).toBe('');
            // Tags and dates should also be cleared if they were set
        });
        // After clearing, list should revert to original 3 events
        expect(screen.getByTestId('event-list').textContent).toContain('3 events list mock');
        // Ensure getEvents is not called again on clear if we revert from originalEvents state
        expect(eventService.getEvents).toHaveBeenCalledTimes(1);
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
});

// Minimal test for App component to ensure Dashboard is rendered when logged in
describe('App Component', () => {
    test('renders Dashboard when user is logged in', () => {
        authService.getCurrentUserToken.mockReturnValue('fake-token'); // User is logged in
        render(<App />);
        expect(screen.getByText('My Schedule')).toBeInTheDocument(); // "My Schedule" is a heading in Dashboard
    });

    test('renders Login when user is not logged in', () => {
        authService.getCurrentUserToken.mockReturnValue(null); // User is not logged in
        render(<App />);
        // Assuming Login component has a distinct element, e.g., a button or heading
        expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    });
});
