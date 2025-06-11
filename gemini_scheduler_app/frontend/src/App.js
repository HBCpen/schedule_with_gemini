import React, { useState, useEffect } from 'react';
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';
import Dashboard from './components/Dashboard'; // Import Dashboard
import authService from './services/authService';
import './App.css';

function App() {
    const [currentUserToken, setCurrentUserToken] = useState(null);
    const [loadingToken, setLoadingToken] = useState(true);


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
    };

    const handleLoginSuccess = () => {
         const token = authService.getCurrentUserToken();
         setCurrentUserToken(token);
    }

    if (loadingToken) {
        return <p>Loading...</p>; // Or a spinner
    }

    return (
        <div className="App">
            <header className="App-header">
                <h1>Gemini Scheduler</h1>
                 {currentUserToken ? (
                    <>
                        <button onClick={handleLogout} style={{float: 'right'}}>Logout</button>
                        <Dashboard />
                    </>
                ) : (
                    <div>
                        <Login onLoginSuccess={handleLoginSuccess} />
                        <hr />
                        <Register />
                    </div>
                )}
            </header>
        </div>
    );
}
export default App;
