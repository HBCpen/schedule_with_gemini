import axios from 'axios'; // Assuming eventService uses the global axios import
import AxiosMockAdapter from 'axios-mock-adapter';
import eventService from './eventService';
import authService from './authService'; // To mock getCurrentUserToken

// jest.mock('./authService'); // Alternative: auto-mock authService

describe('eventService Integration Tests', () => {
  let mock;
  const fakeToken = 'test-token';

  beforeEach(() => {
    mock = new AxiosMockAdapter(axios);
    // Mock getCurrentUserToken from the actual authService module
    jest.spyOn(authService, 'getCurrentUserToken').mockReturnValue(fakeToken);
  });

  afterEach(() => {
    mock.restore();
    jest.restoreAllMocks(); // Restores all spied/mocked functions
  });

  const commonEventData = {
    title: 'Test Event',
    start_time: '2024-01-01T10:00:00Z',
    end_time: '2024-01-01T11:00:00Z',
    description: 'Test description',
  };

  // Test for createEvent
  describe('createEvent', () => {
    it('should make a POST request to /api/events with correct data and headers on success', async () => {
      const responseData = { id: 1, ...commonEventData, color_tag: "blue" };
      mock.onPost('/api/events', commonEventData).reply(201, responseData);

      const result = await eventService.createEvent(commonEventData);

      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0].url).toBe('/api/events');
      expect(JSON.parse(mock.history.post[0].data)).toEqual(commonEventData);
      expect(mock.history.post[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(responseData);
    });

    it('should return an error on failure (e.g., validation error)', async () => {
      const errorResponse = { msg: 'Validation failed' };
      mock.onPost('/api/events', commonEventData).reply(400, errorResponse);

      try {
        await eventService.createEvent(commonEventData);
      } catch (error) {
        expect(error.response.status).toBe(400);
        expect(error.response.data).toEqual(errorResponse);
      }
    });
  });

  // Test for getEvents
  describe('getEvents', () => {
    it('should make a GET request to /api/events with params and headers', async () => {
      const params = { start_date: '2024-01-01', end_date: '2024-01-31' };
      const responseData = [{ id: 1, ...commonEventData }];
      mock.onGet('/api/events', { params }).reply(200, responseData);

      const result = await eventService.getEvents(params.start_date, params.end_date);

      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0].url).toBe('/api/events');
      expect(mock.history.get[0].params).toEqual(params);
      expect(mock.history.get[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(responseData);
    });
  });

  // Test for getEventById
  describe('getEventById', () => {
    const eventId = 'event123';
    it('should make a GET request to /api/events/:id with headers', async () => {
      const responseData = { id: eventId, ...commonEventData };
      mock.onGet(`/api/events/${eventId}`).reply(200, responseData);

      const result = await eventService.getEventById(eventId);

      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0].url).toBe(`/api/events/${eventId}`);
      expect(mock.history.get[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(responseData);
    });

    it('should return an error if event not found (404)', async () => {
      mock.onGet(`/api/events/${eventId}`).reply(404, { msg: 'Not Found' });
      try {
        await eventService.getEventById(eventId);
      } catch (error) {
        expect(error.response.status).toBe(404);
      }
    });
  });

  // Test for updateEvent
  describe('updateEvent', () => {
    const eventId = 'event456';
    const updatedData = { ...commonEventData, title: 'Updated Test Event' };
    it('should make a PUT request to /api/events/:id with data and headers', async () => {
      const responseData = { id: eventId, ...updatedData };
      mock.onPut(`/api/events/${eventId}`, updatedData).reply(200, responseData);

      const result = await eventService.updateEvent(eventId, updatedData);

      expect(mock.history.put.length).toBe(1);
      expect(mock.history.put[0].url).toBe(`/api/events/${eventId}`);
      expect(JSON.parse(mock.history.put[0].data)).toEqual(updatedData);
      expect(mock.history.put[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(responseData);
    });
  });

  // Test for deleteEvent
  describe('deleteEvent', () => {
    const eventId = 'event789';
    it('should make a DELETE request to /api/events/:id with headers', async () => {
      const responseData = { msg: 'Event deleted' };
      mock.onDelete(`/api/events/${eventId}`).reply(200, responseData);

      const result = await eventService.deleteEvent(eventId);

      expect(mock.history.delete.length).toBe(1);
      expect(mock.history.delete[0].url).toBe(`/api/events/${eventId}`);
      expect(mock.history.delete[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(responseData);
    });
  });

  // Test for parseNaturalLanguageEvent
  describe('parseNaturalLanguageEvent', () => {
    const text = 'Meeting tomorrow at 10am';
    const parsedData = { title: 'Meeting', start_time: '...' };
    it('should make a POST request to /api/events/parse-natural-language', async () => {
      mock.onPost('/api/events/parse-natural-language', { text }).reply(200, parsedData);

      const result = await eventService.parseNaturalLanguageEvent(text);

      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0].url).toBe('/api/events/parse-natural-language');
      expect(JSON.parse(mock.history.post[0].data)).toEqual({ text });
      expect(mock.history.post[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(parsedData);
    });
  });

  // Test for getEventRelatedInfo
  describe('getEventRelatedInfo', () => {
    const eventId = 'eventRelInfo123';
    const relatedInfo = { weather: 'Sunny', traffic: 'Light' };
    it('should make a GET request to /api/events/:eventId/related-info', async () => {
      mock.onGet(`/api/events/${eventId}/related-info`).reply(200, relatedInfo);

      const result = await eventService.getEventRelatedInfo(eventId);

      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0].url).toBe(`/api/events/${eventId}/related-info`);
      expect(mock.history.get[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(relatedInfo);
    });
  });

  // Test for searchEvents
  describe('searchEvents', () => {
    const params = { q: 'keyword', start_date: '2024-01-01', end_date: '2024-01-05', tags: 'work' };
    const searchResults = [{ id: 1, title: 'Found event by keyword' }];
    it('should make a GET request to /api/events/search with query params', async () => {
      mock.onGet('/api/events/search', { params }).reply(200, searchResults);

      const result = await eventService.searchEvents(params.q, params.start_date, params.end_date, params.tags);

      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0].url).toBe('/api/events/search');
      expect(mock.history.get[0].params).toEqual(params);
      expect(mock.history.get[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(searchResults);
    });
  });

  // Test for findFreeTime
  describe('findFreeTime', () => {
    const query = 'next week';
    const startDate = '2024-01-08';
    const endDate = '2024-01-14';
    const timeSlots = [{ start_time: '...', end_time: '...' }];
    it('should make a POST request to /api/events/find-free-time', async () => {
      mock.onPost('/api/events/find-free-time', { query, start_date: startDate, end_date: endDate }).reply(200, timeSlots);

      const result = await eventService.findFreeTime(query, startDate, endDate);

      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0].url).toBe('/api/events/find-free-time');
      expect(JSON.parse(mock.history.post[0].data)).toEqual({ query, start_date: startDate, end_date: endDate });
      expect(mock.history.post[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(timeSlots);
    });
  });

  // Test for getEventSummary
  describe('getEventSummary', () => {
    const date = '2024-01-01';
    const summary = { summary: 'You have 1 event.' };
    it('should make a GET request to /api/events/summary with date param', async () => {
      mock.onGet('/api/events/summary', { params: { date } }).reply(200, summary);

      const result = await eventService.getEventSummary(date);

      expect(mock.history.get.length).toBe(1);
      expect(mock.history.get[0].url).toBe('/api/events/summary');
      expect(mock.history.get[0].params).toEqual({ date });
      expect(mock.history.get[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
      expect(result.data).toEqual(summary);
    });
  });

  // Test for suggestSubtasks
  describe('suggestSubtasks', () => {
    const eventId = 'eventSubtask123';
    const subtasks = ["Subtask 1", "Subtask 2"];
    it('should make a POST request to /api/events/:eventId/suggest-subtasks', async () => {
        mock.onPost(`/api/events/${eventId}/suggest-subtasks`).reply(200, subtasks);

        const result = await eventService.suggestSubtasks(eventId);

        expect(mock.history.post.length).toBe(1);
        expect(mock.history.post[0].url).toBe(`/api/events/${eventId}/suggest-subtasks`);
        expect(mock.history.post[0].headers['Authorization']).toBe(`Bearer ${fakeToken}`);
        expect(result.data).toEqual(subtasks);
    });
  });

});
