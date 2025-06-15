import React, { useState } from 'react';
import authService from '../../services/authService';

function Register({ onRegisterSuccess }) { // Added onRegisterSuccess prop
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [message, setMessage] = useState('');

    const handleRegister = async (e) => {
        e.preventDefault();
        setMessage('');
        try {
            const response = await authService.register(email, password);
            setMessage(response.data.msg || 'Registration successful!');
            if (onRegisterSuccess) { // Call the callback
                onRegisterSuccess();
            }
            // No fallback to window.location.reload() here, as navigation is preferred.
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
            <h2>Register</h2>
            <form onSubmit={handleRegister}>
                <div>
                    <label htmlFor="email">Email</label>
                    <input type="email" id="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </div>
                <div>
                    <label htmlFor="password">Password</label>
                    <input type="password" id="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </div>
                <button type="submit">Register</button>
            </form>
            {message && <p>{message}</p>}
        </div>
    );
}

export default Register;
