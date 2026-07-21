import { Link, useLocation } from 'react-router-dom';
import { Upload, BarChart3, Zap } from 'lucide-react';
import './Navbar.css';

export default function Navbar() {
  const location = useLocation();

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        {/* Logo */}
        <Link to="/" className="navbar-logo" id="nav-logo">
          <div className="logo-icon">
            <Zap size={20} />
          </div>
          <span className="logo-text font-display">
            MatchCast <span className="text-accent">AI</span>
          </span>
        </Link>

        {/* Nav Links */}
        <div className="navbar-links">
          <Link
            to="/upload"
            className={`nav-link ${location.pathname === '/upload' ? 'active' : ''}`}
            id="nav-upload"
          >
            <Upload size={16} />
            <span>Upload</span>
          </Link>
          <Link
            to="/"
            className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
            id="nav-dashboard"
          >
            <BarChart3 size={16} />
            <span>Matches</span>
          </Link>
        </div>

        {/* CTA */}
        <Link to="/upload" className="btn btn-primary btn-sm" id="nav-cta">
          <Upload size={14} />
          Upload Match
        </Link>
      </div>
    </nav>
  );
}
