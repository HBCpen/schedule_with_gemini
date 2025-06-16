import React from 'react';

const mockNavigateFn = jest.fn(); // Renamed to avoid conflict if useNavigate itself is imported directly
const mockUseNavigate = jest.fn(() => mockNavigateFn);

const BrowserRouter = ({ children }) => <div>{children}</div>;
const Routes = ({ children }) => <div>{children}</div>;
const Route = ({ element }) => element;
const Link = ({ to, children }) => <a href={to}>{children}</a>;
const Navigate = (props) => <div data-testid="navigate-mock" {...props}>Navigate to {props.to}</div>;

export {
  BrowserRouter,
  Routes,
  Route,
  Link,
  Navigate,
  mockUseNavigate as useNavigate, // Correctly export mockUseNavigate as useNavigate
};
