import React from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import Footer from './Footer';
// Optional: import './MainLayout.css';

const MainLayout = ({ children }) => { // Ensure children prop is destructured
  return (
    <div className="main-layout">
      <Header />
      <div className="layout-body" style={{ display: 'flex' }}>
        <Sidebar />
        <main className="content-area" style={{ flexGrow: 1, padding: '20px', minHeight: 'calc(100vh - 140px)' /* Adjust based on header/footer height */ }}>
          {children}
        </main>
      </div>
      <Footer />
    </div>
  );
};

export default MainLayout;
