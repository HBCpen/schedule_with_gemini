import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate, useNavigate } from 'react-router-dom';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import MainLayout from './components/Layout/MainLayout';
import DashboardPage from './pages/DashboardPage';
import CalendarPage from './pages/CalendarPage';
import SettingsPage from './pages/SettingsPage';
import authService from './services/authService';
import './App.css';

// AppContent component to use useNavigate hook
function AppContent() {
    const [currentUserToken, setCurrentUserToken] = useState(authService.getCurrentUserToken());
    const [loadingToken, setLoadingToken] = useState(true);
    const navigate = useNavigate(); // Hook for navigation

    useEffect(() => {
        const token = authService.getCurrentUserToken();
        if (token) {
            setCurrentUserToken(token);
        }
        setLoadingToken(false);
    }, []);

    const handleLogout = () => {
        authService.logout();
        setCurrentUserToken(null);
        navigate('/login'); // Navigate to login on logout
    };

    const handleLoginSuccess = (token) => { // Modified to accept token, though authService handles it
        setCurrentUserToken(authService.getCurrentUserToken()); // Ensure we get from service
        navigate('/dashboard'); // Navigate to dashboard on login
    };

    // This function is likely needed by the Register component
    const handleRegisterSuccess = () => {
        // Potentially navigate to login or dashboard, or show a message
        // For now, let's assume it navigates to login, or a confirmation page not yet built
        navigate('/login');
    };


    if (loadingToken) {
        return <p style={{ textAlign: 'center', marginTop: '50px' }}>Loading...</p>;
    }

    return (
        <>
            {currentUserToken ? (
                <MainLayout> {/* MainLayout will render Header, Sidebar, Footer */}
                    {/* Logout button can be moved into Header later */}
                    <button
                        onClick={handleLogout}
                        style={{
                            position: 'absolute',
                            top: '10px',
                            right: '20px',
                            zIndex: 1050, /* Ensure it's above other elements if necessary */
                            padding: '8px 15px',
                            backgroundColor: '#f44336', /* Red */
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer'
                        }}>
                        Logout
                    </button>
                    <Routes>
                        <Route path="/dashboard" element={<DashboardPage />} />
                        <Route path="/calendar" element={<CalendarPage />} />
                        <Route path="/settings" element={<SettingsPage />} />
                        <Route path="/" element={<Navigate to="/dashboard" />} /> {/* Default to dashboard */}
                        <Route path="/*" element={<Navigate to="/dashboard" />} /> {/* Catch-all to dashboard */}
                    </Routes>
                </MainLayout>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
                  <h1 style={{ marginBottom: '20px' }}>Gemini Scheduler</h1>
                  <Routes>
                      <Route path="/login" element={<Login onLoginSuccess={handleLoginSuccess} />} />
                      <Route path="/register" element={<Register onRegisterSuccess={handleRegisterSuccess} />} />
                      <Route path="/*" element={<Navigate to="/login" />} /> {/* Default to login */}
                  </Routes>
                </div>
            )}
        </>
    );
}

// Main App component wraps AppContent with Router
function App() {
    return (
        <Router>
            <div className="App">
                {/* The main App header is removed as MainLayout's Header will be used */}
                <AppContent />
            </div>
        </Router>
    );
}

export default App;
