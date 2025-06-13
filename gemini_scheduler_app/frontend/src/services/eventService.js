import axios from 'axios';
import authService from './authService'; // To get the token

const API_URL = '/api/events'; // Base URL for event-related actions

const getAuthHeaders = () => {
    const token = authService.getCurrentUserToken();
    if (token) {
        return { Authorization: `Bearer ${token}` };
    }
    return {};
};

const createEvent = (eventData) => {
    return axios.post(API_URL, eventData, { headers: getAuthHeaders() });
};

// Modified to accept query parameters for date range
const getEvents = (params = {}) => {
    return axios.get(API_URL, {
        headers: getAuthHeaders(),
        params: params
    });
};

const getEventById = (id) => {
    return axios.get(`${API_URL}/${id}`, { headers: getAuthHeaders() });
};

const updateEvent = (id, eventData) => {
    return axios.put(`${API_URL}/${id}`, eventData, { headers: getAuthHeaders() });
};

const deleteEvent = (id) => {
    return axios.delete(`${API_URL}/${id}`, { headers: getAuthHeaders() });
};

// New function for parsing natural language text
const parseNaturalLanguageEvent = (text) => {
    // The actual API endpoint for NLP parsing is /api/events/parse-natural-language
    return axios.post(`${API_URL}/parse-natural-language`, { text }, { headers: getAuthHeaders() });
};

const eventService = {
    createEvent,
    getEvents,
    getEventById,
    updateEvent,
    deleteEvent,
    parseNaturalLanguageEvent, // Added new function to export

    // New function for searching events
    searchEvents: (params) => {
        return axios.get(`${API_URL}/search`, {
            headers: getAuthHeaders(),
            params: params // e.g., { q: 'keyword', start_date: '2024-01-01', ... }
        });
    }
};
export default eventService;
