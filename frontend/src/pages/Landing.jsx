import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Upload,
  Play,
  Zap,
  BarChart3,
  Brain,
  Target,
  Users,
  TrendingUp,
  Video,
  ArrowRight,
} from 'lucide-react';
import './Landing.css';

const features = [
  {
    icon: <Target size={24} />,
    title: 'Player Detection & Tracking',
    desc: 'AI-powered detection of every player with persistent tracking across the entire match.',
  },
  {
    icon: <BarChart3 size={24} />,
    title: 'Formation Analysis',
    desc: 'Real-time formation-change detection with tactical shift alerts and radar replay.',
  },
  {
    icon: <Video size={24} />,
    title: 'Auto Highlight Reel',
    desc: 'AI-generated highlights with commentary, voiceover, and tactical graphics.',
  },
  {
    icon: <Brain size={24} />,
    title: 'AI Coach',
    desc: 'Data-grounded tactical recommendations citing real match statistics.',
  },
  {
    icon: <Users size={24} />,
    title: 'Player Performance',
    desc: 'Individual player summaries with distance, sprints, and event involvement.',
  },
  {
    icon: <TrendingUp size={24} />,
    title: 'Smart Timeline',
    desc: 'Clickable event timeline that jumps to key moments — goals, shots, formation shifts.',
  },
];

const fadeUp = {
  hidden: { opacity: 0, y: 30 },
  visible: (i) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.5, ease: 'easeOut' },
  }),
};

export default function Landing() {
  return (
    <div className="landing">
      {/* ===== Hero ===== */}
      <section className="hero" id="hero">
        <div className="hero-glow" />
        <motion.div
          className="hero-content"
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
        >
          <div className="hero-badge stat-badge">
            <Zap size={14} />
            AI-Powered Football Analysis
          </div>
          <h1 className="hero-title font-display">
            MatchCast <span className="text-accent glow-text">AI</span>
          </h1>
          <p className="hero-subtitle">
            Upload any football match video and receive AI-generated tactical
            insights, tracked positions, event detection, formation analysis,
            and automatic highlight generation.
          </p>
          <div className="hero-actions">
            <Link to="/upload" className="btn btn-primary btn-lg" id="hero-upload-btn">
              <Upload size={18} />
              Upload Match
            </Link>
            <a
              href="https://www.youtube.com/watch?v=-GqdlKqcFJo"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-outline btn-lg"
              id="hero-demo-btn"
              style={{ textDecoration: 'none' }}
            >
              <Play size={18} />
              Watch Demo
            </a>
          </div>
        </motion.div>

        {/* Hero visual — pitch lines */}
        <div className="hero-visual">
          <div className="pitch-lines">
            <div className="pitch-center-circle" />
            <div className="pitch-center-line" />
            <div className="pitch-dot dot-1" />
            <div className="pitch-dot dot-2" />
            <div className="pitch-dot dot-3" />
            <div className="pitch-dot dot-4" />
            <div className="pitch-dot dot-5" />
          </div>
        </div>
      </section>

      {/* ===== Features ===== */}
      <section className="features" id="features">
        <motion.div
          className="section-header"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <h2 className="section-title font-display">
            Everything You Need to <span className="text-accent">Analyze</span> a Match
          </h2>
          <p className="section-subtitle">
            From raw video to complete tactical intelligence — powered by computer vision and generative AI.
          </p>
        </motion.div>

        <div className="features-grid">
          {features.map((feature, i) => (
            <motion.div
              key={feature.title}
              className="feature-card glass-card"
              custom={i}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
            >
              <div className="feature-icon">{feature.icon}</div>
              <h3 className="feature-title">{feature.title}</h3>
              <p className="feature-desc">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* ===== How It Works ===== */}
      <section className="how-it-works" id="how-it-works">
        <motion.div
          className="section-header"
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
        >
          <h2 className="section-title font-display">
            How It <span className="text-accent">Works</span>
          </h2>
        </motion.div>

        <div className="steps-row">
          {[
            { num: '01', title: 'Upload', desc: 'Drop your match video into MatchCast AI.', icon: <Upload size={28} /> },
            { num: '02', title: 'Analyze', desc: 'AI detects players, tracks movement, and identifies key events.', icon: <Target size={28} /> },
            { num: '03', title: 'Review', desc: 'Explore the tactical dashboard with radar replay and AI insights.', icon: <BarChart3 size={28} /> },
          ].map((step, i) => (
            <motion.div
              key={step.num}
              className="step-card"
              custom={i}
              initial="hidden"
              whileInView="visible"
              viewport={{ once: true }}
              variants={fadeUp}
            >
              <div className="step-num">{step.num}</div>
              <div className="step-icon">{step.icon}</div>
              <h3>{step.title}</h3>
              <p>{step.desc}</p>
              {i < 2 && <ArrowRight className="step-arrow" size={20} />}
            </motion.div>
          ))}
        </div>
      </section>

      {/* ===== CTA ===== */}
      <section className="cta-section">
        <motion.div
          className="cta-card glass-card-static"
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <h2 className="font-display">Ready to Analyze Your Match?</h2>
          <p>Upload your football match video and let AI do the rest.</p>
          <Link to="/upload" className="btn btn-primary btn-lg" id="cta-upload-btn">
            <Upload size={18} />
            Get Started
            <ArrowRight size={16} />
          </Link>
        </motion.div>
      </section>

      {/* ===== Footer ===== */}
      <footer className="footer">
        <div className="footer-inner">
          <div className="footer-logo font-display">
            <Zap size={16} className="text-accent" />
            MatchCast <span className="text-accent">AI</span>
          </div>
          <p className="text-muted" style={{ fontSize: '0.8rem' }}>
            Built for the Backblaze Generative AI Media Hackathon
          </p>
        </div>
      </footer>
    </div>
  );
}
