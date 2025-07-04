import React, { useState } from 'react';
import authService from '../../services/authService';

function Login({ onLoginSuccess }) { // Added onLoginSuccess prop
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState('');

    const handleLogin = async (e) => {
        e.preventDefault();
        setMessage('');
        try {
            await authService.login(email, password);
            setMessage('Login successful!');
            if (onLoginSuccess) { // Call the callback
                onLoginSuccess();
            } else {
                window.location.reload(); // Fallback
            }
        } catch (error) {
            const resMessage =
                (error.response && error.response.data && error.response.data.msg) ||
                error.message ||
                error.toString();
            setMessage(resMessage);
        }
    };

    return (
        <div>
            <h2>Login</h2>
            <form onSubmit={handleLogin}>
                <div>
                    <label htmlFor="email">Email</label>
                    <input type="email" id="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </div>
                <div>
                    <label htmlFor="password">Password</label>
                    <input type="password" id="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </div>
                <button type="submit">Login</button>
            </form>
            {message && <p>{message}</p>}
        </div>
    );
}
export default Login;
