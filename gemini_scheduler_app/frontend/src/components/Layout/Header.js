import React from 'react';
// import './Header.css'; // Optional: if you use a separate CSS file

const Header = () => {
  return (
    <header className="app-header" style={{ padding: '10px 20px', backgroundColor: '#f0f0f0', borderBottom: '1px solid #ccc' }}>
      <h1>Gemini Scheduler</h1>
    </header>
  );
};

export default Header;
