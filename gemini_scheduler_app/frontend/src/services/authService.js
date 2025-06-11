import axios from 'axios';

const API_URL = '/api/auth'; // Assuming frontend is served by a proxy to backend on /api

const register = (email, password) => {
    return axios.post(`${API_URL}/register`, { email, password });
};

const login = async (email, password) => {
    const response = await axios.post(`${API_URL}/login`, { email, password });
    if (response.data.access_token) {
        localStorage.setItem('user_token', response.data.access_token);
    }
    return response.data;
};

const logout = () => {
    localStorage.removeItem('user_token');
    // Potentially call a backend logout endpoint if it handles server-side session invalidation/blocklisting
    // For now, client-side token removal is the primary JWT logout mechanism.
    // return axios.post(`${API_URL}/logout`); // If backend has a meaningful logout
};

const getCurrentUserToken = () => {
    return localStorage.getItem('user_token');
};

// Optional: Add a service to get current user details if needed frequently
// const getMe = () => {
//     const token = getCurrentUserToken();
//     return axios.get(`${API_URL}/me`, { headers: { Authorization: `Bearer ${token}` } });
// };

const authService = {
    register,
    login,
    logout,
    getCurrentUserToken,
    // getMe,
};

export default authService;
