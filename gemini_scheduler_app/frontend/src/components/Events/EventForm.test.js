import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import EventForm from './EventForm';
import eventService from '../../services/eventService';

jest.mock('../../services/eventService');

describe('EventForm Recurrence Functionality', () => {
    beforeEach(() => {
        eventService.createEvent.mockReset();
        eventService.updateEvent.mockReset();
    });

    const baseEventProps = {
        onFormSubmit: jest.fn(),
        onCancelEdit: jest.fn(),
    };

    test('renders basic recurrence fields', () => {
        render(<EventForm {...baseEventProps} />);
        expect(screen.getByText('Recurrence')).toBeInTheDocument();
        expect(screen.getByLabelText('Frequency:')).toBeInTheDocument();
    });

    test('shows interval input when a frequency is selected', () => {
        render(<EventForm {...baseEventProps} />);
        const frequencySelect = screen.getByLabelText('Frequency:');

        fireEvent.change(frequencySelect, { target: { value: 'DAILY' } });
        expect(screen.getByLabelText('Interval (Repeat every X):')).toBeInTheDocument();
        expect(screen.getByText('day(s)')).toBeInTheDocument(); // Checks for "day(s)" text next to interval

        fireEvent.change(frequencySelect, { target: { value: 'WEEKLY' } });
        expect(screen.getByText('week(s)')).toBeInTheDocument();
    });

    test('shows days of week checkboxes for WEEKLY frequency', () => {
        render(<EventForm {...baseEventProps} />);
        const frequencySelect = screen.getByLabelText('Frequency:');
        fireEvent.change(frequencySelect, { target: { value: 'WEEKLY' } });

        expect(screen.getByLabelText('Repeat on:')).toBeInTheDocument();
        ['MO', 'TU', 'WE', 'TH', 'FR', 'SA', 'SU'].forEach(day => {
            expect(screen.getByLabelText(day)).toBeInTheDocument();
        });
    });

    test('does not show days of week for DAILY frequency', () => {
        render(<EventForm {...baseEventProps} />);
        const frequencySelect = screen.getByLabelText('Frequency:');
        fireEvent.change(frequencySelect, { target: { value: 'DAILY' } });

        expect(screen.queryByLabelText('Repeat on:')).not.toBeInTheDocument();
    });

    test('updates state for recurrence fields', () => {
        render(<EventForm {...baseEventProps} />);
        const frequencySelect = screen.getByLabelText('Frequency:');
        fireEvent.change(frequencySelect, { target: { value: 'WEEKLY' } });

        const intervalInput = screen.getByLabelText('Interval (Repeat every X):');
        fireEvent.change(intervalInput, { target: { value: '2' } });
        expect(intervalInput.value).toBe('2');

        const mondayCheckbox = screen.getByLabelText('MO'); // Assuming label is just 'MO'
        fireEvent.click(mondayCheckbox); // Check MO
        expect(mondayCheckbox.checked).toBe(true);

        const untilDateInput = screen.getByLabelText('Ends (Until Date - Optional):');
        fireEvent.change(untilDateInput, { target: { value: '2024-12-31' } });
        expect(untilDateInput.value).toBe('2024-12-31');
    });

    // Test RRULE construction - This requires calling the instance method or checking form submission payload
    // For direct testing of buildRecurrenceRule, it would need to be exported or tested via its effect on submission.
    // Here, we'll test it by checking the payload on submit.
    test('constructs correct RRULE string on submit', async () => {
        eventService.createEvent.mockResolvedValue({ data: {} });
        render(<EventForm {...baseEventProps} />);

        // Fill in basic event details
        fireEvent.change(screen.getByLabelText('Title:'), { target: { value: 'Recurring Event' } });
        fireEvent.change(screen.getByLabelText('Start Time:'), { target: { value: '2024-07-01T10:00' } });
        fireEvent.change(screen.getByLabelText('End Time:'), { target: { value: '2024-07-01T11:00' } });

        // Set recurrence
        fireEvent.change(screen.getByLabelText('Frequency:'), { target: { value: 'WEEKLY' } });
        fireEvent.change(screen.getByLabelText('Interval (Repeat every X):'), { target: { value: '1' } });
        fireEvent.click(screen.getByLabelText('MO')); // Check MO
        fireEvent.click(screen.getByLabelText('FR')); // Check FR
        fireEvent.change(screen.getByLabelText('Ends (Until Date - Optional):'), { target: { value: '2024-07-31' } });

        fireEvent.click(screen.getByRole('button', { name: 'Create' }));

        await waitFor(() => {
            expect(eventService.createEvent).toHaveBeenCalledWith(expect.objectContaining({
                recurrence_rule: 'FREQ=WEEKLY;BYDAY=MO,FR;UNTIL=20240731T235959Z'
            }));
        });
    });

    test('constructs RRULE without BYDAY if no days selected for weekly', async () => {
        eventService.createEvent.mockResolvedValue({ data: {} });
        render(<EventForm {...baseEventProps} />);
        fireEvent.change(screen.getByLabelText('Title:'), { target: { value: 'Weekly Event No Days' } });
        fireEvent.change(screen.getByLabelText('Start Time:'), { target: { value: '2024-08-01T10:00' } });
        fireEvent.change(screen.getByLabelText('End Time:'), { target: { value: '2024-08-01T11:00' } });
        fireEvent.change(screen.getByLabelText('Frequency:'), { target: { value: 'WEEKLY' } });
        // No days selected
        fireEvent.click(screen.getByRole('button', { name: 'Create' }));

        await waitFor(() => {
            expect(eventService.createEvent).toHaveBeenCalledWith(expect.objectContaining({
                recurrence_rule: 'FREQ=WEEKLY' // Or 'FREQ=WEEKLY;INTERVAL=1' if interval is 1 by default
            }));
        });
    });


    test('sends null recurrence_rule if frequency is "Does not repeat"', async () => {
        eventService.createEvent.mockResolvedValue({ data: {} });
        render(<EventForm {...baseEventProps} />);
        fireEvent.change(screen.getByLabelText('Title:'), { target: { value: 'Non-Recurring' } });
        fireEvent.change(screen.getByLabelText('Start Time:'), { target: { value: '2024-07-01T10:00' } });
        fireEvent.change(screen.getByLabelText('End Time:'), { target: { value: '2024-07-01T11:00' } });

        fireEvent.change(screen.getByLabelText('Frequency:'), { target: { value: '' } }); // "Does not repeat"
        fireEvent.click(screen.getByRole('button', { name: 'Create' }));

        await waitFor(() => {
            expect(eventService.createEvent).toHaveBeenCalledWith(expect.objectContaining({
                recurrence_rule: null
            }));
        });
    });

    test('populates recurrence fields when editing an event with RRULE', () => {
        const eventToEdit = {
            id: '1',
            title: 'Existing Recurring Event',
            start_time: '2024-07-01T10:00:00Z',
            end_time: '2024-07-01T11:00:00Z',
            description: '',
            color_tag: '',
            recurrence_rule: 'FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH;UNTIL=20240831T235959Z'
        };
        render(<EventForm {...baseEventProps} eventToEdit={eventToEdit} />);

        expect(screen.getByLabelText('Frequency:').value).toBe('WEEKLY');
        expect(screen.getByLabelText('Interval (Repeat every X):').value).toBe('2');
        expect(screen.getByLabelText('TU').checked).toBe(true);
        expect(screen.getByLabelText('TH').checked).toBe(true);
        expect(screen.getByLabelText('MO').checked).toBe(false);
        expect(screen.getByLabelText('Ends (Until Date - Optional):').value).toBe('2024-08-31');
    });

    test('populates only frequency if RRULE is simple (e.g., FREQ=DAILY)', () => {
        const eventToEdit = {
            id: '2',
            title: 'Daily Recurring Event',
            start_time: '2024-07-01T09:00:00Z',
            end_time: '2024-07-01T10:00:00Z',
            recurrence_rule: 'FREQ=DAILY'
        };
        render(<EventForm {...baseEventProps} eventToEdit={eventToEdit} />);

        expect(screen.getByLabelText('Frequency:').value).toBe('DAILY');
        expect(screen.getByLabelText('Interval (Repeat every X):').value).toBe('1'); // Default interval
        expect(screen.queryByLabelText('Repeat on:')).not.toBeInTheDocument(); // No days of week for daily
        expect(screen.getByLabelText('Ends (Until Date - Optional):').value).toBe(''); // No UNTIL date
    });

});
