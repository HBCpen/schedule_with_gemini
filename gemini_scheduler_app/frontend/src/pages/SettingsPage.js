import React, { useState, useEffect } from 'react';
// import authService from '../services/authService'; // Will use mock for this task

// Mock authService for local component development
const mockAuthService = {
  getMe: async () => {
    console.log("mockAuthService.getMe called");
    await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay
    return {
      data: {
        name: 'Test User',
        email: 'user@example.com',
        timezone: 'UTC',
        default_reminder_value: 30,
        default_reminder_unit: 'minutes'
      }
    };
    // To simulate error:
    // throw { response: { data: { detail: "Mocked error: Failed to fetch user settings." }}};
  },
  updateMe: async (settings) => {
    console.log("mockAuthService.updateMe called with:", settings);
    await new Promise(resolve => setTimeout(resolve, 500)); // Simulate delay
    return { data: { message: 'Settings updated successfully (mocked)!' } };
    // To simulate error:
    // throw { response: { data: { detail: "Mocked error: Failed to update settings." }}};
  }
};

const SettingsPage = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [timezone, setTimezone] = useState('');
  const [defaultReminderValue, setDefaultReminderValue] = useState(30);
  const [defaultReminderUnit, setDefaultReminderUnit] = useState('minutes');

  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const fetchUserSettings = async () => {
    setIsLoading(true);
    setError('');
    setMessage('');
    try {
      const response = await mockAuthService.getMe(); // Using mock
      const userData = response.data;
      setName(userData.name || '');
      setEmail(userData.email || '');
      setTimezone(userData.timezone || 'UTC'); // Default to UTC if not set
      setDefaultReminderValue(userData.default_reminder_value || 30);
      setDefaultReminderUnit(userData.default_reminder_unit || 'minutes');
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to fetch user settings.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUserSettings();
  }, []);

  const handleInputChange = (e) => {
    const { name, value, type } = e.target;
    setMessage('');
    setError('');

    if (name === 'timezone') {
      setTimezone(value);
    } else if (name === 'defaultReminderValue') {
      setDefaultReminderValue(type === 'number' ? parseInt(value, 10) : value);
    } else if (name === 'defaultReminderUnit') {
      setDefaultReminderUnit(value);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    setMessage('');

    const settingsData = {
      timezone,
      default_reminder_value: parseInt(defaultReminderValue, 10),
      default_reminder_unit: defaultReminderUnit,
    };

    try {
      const response = await mockAuthService.updateMe(settingsData); // Using mock
      setMessage(response.data.message || 'Settings updated successfully!');
      // Optionally re-fetch settings or update state if backend returns the full updated object
      // fetchUserSettings();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to update settings.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h2>Settings Page</h2>

      {isLoading && <p>Loading...</p>}
      {message && <p style={{ color: 'green' }}>{message}</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      <form onSubmit={handleSubmit}>
        <h3>User Profile</h3>
        <div style={{ marginBottom: '10px' }}>
          <label>Name: </label>
          <span>{name || 'N/A'}</span>
        </div>
        <div style={{ marginBottom: '20px' }}>
          <label>Email: </label>
          <span>{email || 'N/A'}</span>
        </div>

        <h3>Preferences</h3>
        <div style={{ marginBottom: '10px' }}>
          <label htmlFor="timezone" style={{ marginRight: '10px' }}>Timezone:</label>
          <input
            type="text"
            id="timezone"
            name="timezone"
            value={timezone}
            onChange={handleInputChange}
            disabled={isLoading}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={{ marginRight: '10px' }}>Default Reminder Time:</label>
          <input
            type="number"
            id="defaultReminderValue"
            name="defaultReminderValue"
            value={defaultReminderValue}
            onChange={handleInputChange}
            disabled={isLoading}
            style={{ width: '60px', marginRight: '5px' }}
          />
          <select
            id="defaultReminderUnit"
            name="defaultReminderUnit"
            value={defaultReminderUnit}
            onChange={handleInputChange}
            disabled={isLoading}
          >
            <option value="minutes">minutes</option>
            <option value="hours">hours</option>
            <option value="days">days</option>
          </select>
          <span style={{ marginLeft: '5px' }}>before event</span>
        </div>

        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Saving...' : 'Save Settings'}
        </button>
      </form>
    </div>
  );
};

export default SettingsPage;
