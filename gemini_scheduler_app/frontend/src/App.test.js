import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from './App';
import authService from './services/authService'; // Import the original service

// Mock react-router-dom (Jest will automatically pick this up from src/__mocks__/react-router-dom.js)
jest.mock('react-router-dom');

// Mock authService
jest.mock('./services/authService');

// Mock child components that might be heavy or not relevant to App.js logic
jest.mock('./components/Auth/Login', () => () => <div data-testid="login-component">Login Mock</div>);
jest.mock('./components/Auth/Register', () => () => <div data-testid="register-component">Register Mock</div>);
jest.mock('./components/Layout/MainLayout', () => () => <div data-testid="main-layout-component">MainLayout Mock</div>);


describe('App Routing and Authentication', () => {
  beforeEach(() => {
    // Clear any previous mock implementations or reset calls
    authService.getCurrentUserToken.mockClear();
  });

  test('renders Login component when user is not authenticated and path is /login', () => {
    authService.getCurrentUserToken.mockReturnValue(null);
    // Mock window.location.pathname for this test
    Object.defineProperty(window, 'location', {
      value: {
        pathname: '/login'
      },
      writable: true
    });
    render(<App />);
    expect(screen.getByTestId('login-component')).toBeInTheDocument();
  });

  test('renders Register component when user is not authenticated and path is /register', () => {
    authService.getCurrentUserToken.mockReturnValue(null);
    Object.defineProperty(window, 'location', {
        value: {
          pathname: '/register'
        },
        writable: true
      });
    render(<App />);
    expect(screen.getByTestId('register-component')).toBeInTheDocument();
  });


  test('renders MainLayout component when user is authenticated', () => {
    authService.getCurrentUserToken.mockReturnValue('fake-token'); // User is logged in
     Object.defineProperty(window, 'location', { // Ensure a relevant path
        value: {
          pathname: '/'
        },
        writable: true
      });
    render(<App />);
    expect(screen.getByTestId('main-layout-component')).toBeInTheDocument();
  });

  test('redirects to / when user is authenticated but tries to access /login', () => {
    authService.getCurrentUserToken.mockReturnValue('fake-token');
    Object.defineProperty(window, 'location', {
      value: { pathname: '/login' },
      writable: true
    });
    render(<App />);
    // In this setup, App component logic should redirect.
    // Since Navigate is mocked, we check if it would have been rendered
    // OR, more accurately, check if MainLayout is rendered (as it's the target of redirection for logged-in users)
    expect(screen.getByTestId('main-layout-component')).toBeInTheDocument();
    expect(screen.queryByTestId('login-component')).not.toBeInTheDocument();
  });

   test('redirects to /login when user is not authenticated and tries to access a protected route like /', () => {
    authService.getCurrentUserToken.mockReturnValue(null);
    Object.defineProperty(window, 'location', {
      value: { pathname: '/' },
      writable: true
    });
    render(<App />);
    // App component logic should redirect to login.
    // Check if Login component is rendered
    expect(screen.getByTestId('login-component')).toBeInTheDocument();
    expect(screen.queryByTestId('main-layout-component')).not.toBeInTheDocument();
  });

});
