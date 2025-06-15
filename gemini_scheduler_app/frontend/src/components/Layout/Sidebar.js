import React from 'react';
import { Link } from 'react-router-dom'; // Import Link
// import './Sidebar.css'; // Optional

const Sidebar = () => {
  return (
    <aside className="app-sidebar" style={{ padding: '20px', width: '200px', backgroundColor: '#e9e9e9', height: 'calc(100vh - 120px)' /* Adjust if necessary */ }}>
      <nav>
        <ul>
          <li style={{ marginBottom: '10px' }}><Link to="/dashboard">Dashboard</Link></li>
          <li style={{ marginBottom: '10px' }}><Link to="/calendar">Calendar</Link></li>
          <li style={{ marginBottom: '10px' }}><Link to="/settings">Settings</Link></li>
        </ul>
      </nav>
    </aside>
  );
};

export default Sidebar;
