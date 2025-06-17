import axios from 'axios'; // Import the direct axios instance
import AxiosMockAdapter from 'axios-mock-adapter';
import authService from './authService';

describe('authService Integration Tests', () => {
  let mock;

  beforeEach(() => {
    mock = new AxiosMockAdapter(axios); // Use the direct axios instance
    localStorage.clear(); // Clear localStorage before each test
  });

  afterEach(() => {
    mock.restore(); // Restore original axios instance
    localStorage.clear(); // Clear localStorage after each test
  });

  describe('register', () => {
    it('should make a POST request to /api/auth/register and return data on success', async () => {
      const email = 'test@example.com';
      const password = 'password123';
      const responseData = { msg: 'User registered successfully' };

      mock.onPost('/api/auth/register', { email, password }).reply(201, responseData);

      const result = await authService.register(email, password);

      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0].url).toBe('/api/auth/register');
      expect(JSON.parse(mock.history.post[0].data)).toEqual({ email, password });
      expect(result).toEqual(responseData);
    });

    it('should return an error message on registration failure (e.g., email exists)', async () => {
      const email = 'test@example.com';
      const password = 'password123';
      const errorResponse = { msg: 'Email already exists' };

      mock.onPost('/api/auth/register', { email, password }).reply(400, errorResponse);

      try {
        await authService.register(email, password);
      } catch (error) {
        expect(mock.history.post.length).toBe(1);
        expect(mock.history.post[0].url).toBe('/api/auth/register');
        // Axios error object structure: error.response.data contains the error payload
        expect(error.response.data).toEqual(errorResponse);
      }
    });
  });

  describe('login', () => {
    it('should make a POST request to /api/auth/login, store token, and return data on success', async () => {
      const email = 'test@example.com';
      const password = 'password123';
      const responseData = { access_token: 'fake_access_token', user: { id: 1, email } };

      mock.onPost('/api/auth/login', { email, password }).reply(200, responseData);

      const result = await authService.login(email, password);

      expect(mock.history.post.length).toBe(1);
      expect(mock.history.post[0].url).toBe('/api/auth/login');
      expect(JSON.parse(mock.history.post[0].data)).toEqual({ email, password });
      expect(localStorage.getItem('user_token')).toBe(responseData.access_token);
      expect(result).toEqual(responseData);
    });

    it('should not store token and return error on login failure (e.g., wrong credentials)', async () => {
      const email = 'test@example.com';
      const password = 'wrongpassword';
      const errorResponse = { msg: 'Invalid credentials' };

      mock.onPost('/api/auth/login', { email, password }).reply(401, errorResponse);

      localStorage.setItem('user_token', 'initial_token_value'); // Pre-set a token

      try {
        await authService.login(email, password);
      } catch (error) {
        expect(mock.history.post.length).toBe(1);
        expect(mock.history.post[0].url).toBe('/api/auth/login');
        expect(localStorage.getItem('user_token')).toBe('initial_token_value'); // Token should not change
        expect(error.response.data).toEqual(errorResponse);
      }
    });
  });

  describe('logout', () => {
    it('should remove user_token from localStorage', () => {
      localStorage.setItem('user_token', 'fake_token_to_remove');

      authService.logout();

      expect(localStorage.getItem('user_token')).toBeNull();
    });
  });

  describe('getCurrentUserToken', () => {
    it('should return the token when it is set in localStorage', () => {
      const fakeToken = 'my_fake_user_token';
      localStorage.setItem('user_token', fakeToken);

      expect(authService.getCurrentUserToken()).toBe(fakeToken);
    });

    it('should return null when no token is set in localStorage', () => {
      localStorage.removeItem('user_token'); // Ensure it's removed
      expect(authService.getCurrentUserToken()).toBeNull();
    });
  });
});
