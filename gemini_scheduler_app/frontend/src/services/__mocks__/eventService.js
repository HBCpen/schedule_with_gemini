// Mock implementation for eventService.js

const eventService = {
  getEvents: jest.fn(() => Promise.resolve({ data: [] })),
  getEventById: jest.fn(() => Promise.resolve({ data: {} })),
  createEvent: jest.fn(() => Promise.resolve({ data: {} })),
  updateEvent: jest.fn(() => Promise.resolve({ data: {} })),
  deleteEvent: jest.fn(() => Promise.resolve({ data: {} })),
  parseNaturalLanguageEvent: jest.fn(() => Promise.resolve({ data: {} })),
  searchEvents: jest.fn(() => Promise.resolve({ data: [] })),
};

export default eventService;
