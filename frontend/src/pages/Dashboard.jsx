import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3, Users, Brain, Clock, Target, TrendingUp,
  Play, Pause, RotateCcw, Activity, Shield, Zap, AlertTriangle, Footprints
} from 'lucide-react';
import './Dashboard.css';

// Base backend URL config (matches Upload page behavior)
const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const API_BASE_URL = `${API_BASE}/api`;

const tabs = [
  { id: 'overview', label: 'Overview', icon: <BarChart3 size={16} /> },
  { id: 'timeline', label: 'Timeline', icon: <Clock size={16} /> },
  { id: 'coach', label: 'AI Coach', icon: <Brain size={16} /> },
  { id: 'players', label: 'Players', icon: <Users size={16} /> },
];

// Map event type to icon
const eventIcon = (type) => {
  if (type === 'sprint')           return <Zap size={14} className="text-accent" />;
  if (type === 'possession_change') return <Shield size={14} style={{ color: 'var(--team-a)' }} />;
  if (type === 'shot')             return <Target size={14} style={{ color: 'var(--team-b)' }} />;
  if (type === 'goal')             return <Target size={14} style={{ color: 'var(--accent)' }} />;
  if (type === 'assist')           return <TrendingUp size={14} style={{ color: '#67e8f9' }} />;
  if (type === 'dribble')          return <Footprints size={14} style={{ color: '#f59e0b' }} />;
  return <Activity size={14} />;
};

const liveScoreAtTime = (events = [], timestamp = 0) => {
  let a = 0;
  let b = 0;
  for (const evt of events) {
    if (evt?.type !== 'goal') continue;
    if ((evt?.timestamp ?? 0) > timestamp) continue;
    if (evt?.team === 'A') a += 1;
    if (evt?.team === 'B') b += 1;
  }
  return { a, b };
};

export default function Dashboard() {
  const { matchId } = useParams();
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [matchInfo, setMatchInfo] = useState(null);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [tracking, setTracking] = useState(null);
  
  // Radar replay states
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentFrameIdx, setCurrentFrameIdx] = useState(0);
  const [playSpeed, setPlaySpeed] = useState(1);
  const playbackIntervalRef = useRef(null);
  const trackingRef = useRef(null); // always-current ref for use inside interval

  // Fetch initial match metadata and poll if processing
  useEffect(() => {
    let isMounted = true;
    let pollInterval = null;

    const fetchMatchState = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/matches/${matchId}`);
        if (!response.ok) throw new Error('Match not found');
        const matchData = await response.json();
        
        if (!isMounted) return;
        setMatchInfo(matchData);

        if (matchData.status === 'completed') {
          setLoading(false);
          fetchAnalyticsAndTracking();
        } else if (matchData.status === 'processing' || matchData.status === 'uploaded') {
          setLoading(false);
          // Start polling processing status
          startPolling();
        } else if (matchData.status === 'failed') {
          setLoading(false);
        }
      } catch (err) {
        console.error('Error fetching match status:', err);
        if (isMounted) setLoading(false);
      }
    };

    const startPolling = () => {
      if (pollInterval) clearInterval(pollInterval);
      
      const pollStatus = async () => {
        try {
          const response = await fetch(`${API_BASE_URL}/processing/${matchId}/status`);
          if (!response.ok) return;
          const statusData = await response.json();
          
          if (!isMounted) return;
          setProcessingStatus(statusData);

          // If pipeline is not running yet, trigger it automatically for the user
          if (statusData.phase === 'uploaded') {
            await fetch(`${API_BASE_URL}/processing/${matchId}/start`, { method: 'POST' });
          }

          if (statusData.phase === 'complete') {
            clearInterval(pollInterval);
            // Refresh match metadata
            const matchResp = await fetch(`${API_BASE_URL}/matches/${matchId}`);
            const updatedMatch = await matchResp.json();
            setMatchInfo(updatedMatch);
            fetchAnalyticsAndTracking();
          } else if (statusData.phase === 'failed') {
            clearInterval(pollInterval);
            const matchResp = await fetch(`${API_BASE_URL}/matches/${matchId}`);
            const updatedMatch = await matchResp.json();
            setMatchInfo(updatedMatch);
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      };

      // Poll every 2 seconds
      pollStatus();
      pollInterval = setInterval(pollStatus, 2000);
    };

    const fetchAnalyticsAndTracking = async () => {
      try {
        const [analysisResp, trackingResp] = await Promise.all([
          fetch(`${API_BASE_URL}/analysis/${matchId}/analytics`),
          fetch(`${API_BASE_URL}/analysis/${matchId}/tracking`)
        ]);

        if (analysisResp.ok && trackingResp.ok) {
          const analysisData = await analysisResp.json();
          const trackingData = await trackingResp.json();
          
          if (isMounted) {
            setAnalytics(analysisData);
            setTracking(trackingData);
            trackingRef.current = trackingData;  // keep ref in sync
          }
        }
      } catch (err) {
        console.error('Error loading analytics/tracking data:', err);
      }
    };

    fetchMatchState();

    return () => {
      isMounted = false;
      if (pollInterval) clearInterval(pollInterval);
    };
  }, [matchId]);

  // Radar playback controls
  useEffect(() => {
    if (isPlaying && tracking && tracking.frames && tracking.frames.length > 0) {
      const frameDurationMs = 1000 / (tracking.fps || 25);
      
      playbackIntervalRef.current = setInterval(() => {
        setCurrentFrameIdx((prev) => {
          if (prev >= tracking.frames.length - 1) {
            setIsPlaying(false);
            clearInterval(playbackIntervalRef.current);
            return 0;
          }
          return prev + 1;
        });
      }, frameDurationMs / playSpeed);
    } else {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current);
      }
    }

    return () => {
      if (playbackIntervalRef.current) {
        clearInterval(playbackIntervalRef.current);
      }
    };
  }, [isPlaying, tracking, playSpeed]);

  // jumpToTimestamp: navigates radar to the frame closest to `timestamp` seconds
  // and switches to the Overview tab so the user sees the radar move
  const jumpToTimestamp = (timestamp) => {
    const td = trackingRef.current || tracking;
    if (!td || !td.frames || td.frames.length === 0) return;

    // Binary-search for the closest frame by timestamp
    const frames = td.frames;
    let lo = 0, hi = frames.length - 1, best = 0;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (frames[mid].timestamp < timestamp) { lo = mid + 1; best = mid; }
      else if (frames[mid].timestamp > timestamp) { hi = mid - 1; }
      else { best = mid; break; }
    }
    setCurrentFrameIdx(best);
    setIsPlaying(false);
    setActiveTab('overview');   // switch to radar view so user sees the result
  };

  // Helper to format timestamp seconds into MM:SS
  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="loading-spinner"></div>
        <p className="text-secondary">Loading match details...</p>
      </div>
    );
  }

  // Render processing state if video is still being processed
  if (matchInfo && (matchInfo.status === 'uploaded' || matchInfo.status === 'processing')) {
    const progressPct = processingStatus ? Math.round(processingStatus.progress * 100) : 0;
    return (
      <div className="dashboard-processing">
        <motion.div 
          className="glass-card-static processing-card"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <Activity size={32} className="text-accent pulse-animation" />
          <h2 className="font-display">Analyzing Pitch Perception</h2>
          <p className="text-secondary" style={{ margin: '8px 0 20px 0', textAlign: 'center' }}>
            {processingStatus?.message || "Preparing YOLOv8 model for object tracking..."}
          </p>

          <div className="progress-container">
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
            </div>
            <span className="progress-pct font-display">{progressPct}%</span>
          </div>

          <div className="processing-steps">
            <div className={`step-item ${progressPct >= 0 ? 'active' : ''}`}>1. Load Model</div>
            <div className={`step-item ${progressPct > 10 ? 'active' : ''}`}>2. Run Object Detection</div>
            <div className={`step-item ${progressPct > 40 ? 'active' : ''}`}>3. Track Player IDs</div>
            <div className={`step-item ${progressPct > 80 ? 'active' : ''}`}>4. Project Pitch Homography</div>
          </div>
        </motion.div>
      </div>
    );
  }

  if (matchInfo && matchInfo.status === 'failed') {
    return (
      <div className="dashboard-failed">
        <div className="glass-card-static error-card">
          <AlertTriangle size={40} style={{ color: 'var(--team-b)' }} />
          <h2 className="font-display">Analysis Failed</h2>
          <p className="text-secondary" style={{ marginTop: 12 }}>
            The perception pipeline encountered an error during frame processing.
          </p>
          <button className="btn btn-primary" onClick={() => window.location.reload()} style={{ marginTop: 20 }}>
            Retry Analysis
          </button>
        </div>
      </div>
    );
  }

  const currentFrame = tracking?.frames[currentFrameIdx] || { players: [], ball: null, timestamp: 0 };
  const events = analytics?.events || [];
  const liveScore = liveScoreAtTime(events, currentFrame.timestamp || 0);
  const finalScoreA = Number.isFinite(analytics?.score_a) ? analytics.score_a : liveScore.a;
  const finalScoreB = Number.isFinite(analytics?.score_b) ? analytics.score_b : liveScore.b;
  const qualityFlags = analytics?.quality_flags || [];

  const qualityText = (flag) => {
    if (flag.startsWith('possible_duplicate_goal')) return 'Possible duplicate goal detected';
    if (flag.startsWith('possible_missed_goal:team=A')) return 'Possible missed goal for Team A';
    if (flag.startsWith('possible_missed_goal:team=B')) return 'Possible missed goal for Team B';
    if (flag.startsWith('goal_without_scorer')) return 'Goal detected without scorer identity';
    if (flag.startsWith('goal_without_assist_candidate')) return 'Goal detected without assist candidate';
    return flag;
  };

  return (
    <div className="dashboard">
      <div className="dashboard-container">
        {/* Match Header */}
        <motion.div
          className="match-header glass-card-static"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="match-header-top">
            <div className="stat-badge"><Activity size={12} /> Analysis Complete</div>
            <span className="text-muted" style={{ fontSize: '0.8rem' }}>Match ID: {matchId}</span>
          </div>
          <div className="score-display">
            <div className="team-side">
              <div className="team-badge team-a">A</div>
              <span className="team-name">Team A</span>
            </div>
            <div className="score-center">
              <span className="score-num">{liveScore.a}</span>
              <span className="score-sep">-</span>
              <span className="score-num">{liveScore.b}</span>
            </div>
            <div className="team-side">
              <span className="team-name">Team B</span>
              <div className="team-badge team-b">B</div>
            </div>
          </div>
          <div className="score-meta-row">
            <span className="text-muted" style={{ fontSize: '0.78rem' }}>
              Final detected score: {finalScoreA}-{finalScoreB}
            </span>
            {qualityFlags.length > 0 && (
              <div className="quality-flags-wrap">
                {qualityFlags.slice(0, 3).map((flag, idx) => (
                  <span className="quality-flag-badge" key={`${flag}-${idx}`} title={flag}>
                    <AlertTriangle size={12} /> {qualityText(flag)}
                  </span>
                ))}
              </div>
            )}
          </div>
        </motion.div>

        {/* Tabs */}
        <div className="dashboard-tabs">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
              id={`tab-${tab.id}`}
            >
              {tab.icon}
              <span>{tab.label}</span>
            </button>
          ))}
        </div>

        {/* Tab Content */}
        <div className="dashboard-content">
          {activeTab === 'overview' && (
            <OverviewTab 
              analytics={analytics} 
              currentFrame={currentFrame} 
              currentFrameIdx={currentFrameIdx}
              totalFrames={tracking?.frames?.length || 0}
              isPlaying={isPlaying}
              setIsPlaying={setIsPlaying}
              setCurrentFrameIdx={setCurrentFrameIdx}
              playSpeed={playSpeed}
              setPlaySpeed={setPlaySpeed}
              formatTime={formatTime}
            />
          )}
          {activeTab === 'timeline' && (
            <TimelineTab 
              events={analytics?.events || []} 
              jumpToTimestamp={jumpToTimestamp}
              formatTime={formatTime}
            />
          )}
          {activeTab === 'coach' && (
            <CoachTab 
              analytics={analytics}
            />
          )}
          {activeTab === 'players' && (
            <PlayersTab 
              playerStats={analytics?.player_stats || {}}
            />
          )}
        </div>
      </div>
    </div>
  );
}

function OverviewTab({ 
  analytics, currentFrame, currentFrameIdx, totalFrames, 
  isPlaying, setIsPlaying, setCurrentFrameIdx, playSpeed, setPlaySpeed, formatTime 
}) {
  const possessionPct = analytics?.possession_a || 50;

  const stats = [
    { label: 'Possession', valueA: `${possessionPct}%`, valueB: `${100 - possessionPct}%`, pctA: possessionPct },
    { label: 'Sprints Logged', valueA: Object.values(analytics?.player_stats || {}).filter(p => p.team === 'A').reduce((acc, curr) => acc + curr.sprint_count, 0), valueB: Object.values(analytics?.player_stats || {}).filter(p => p.team === 'B').reduce((acc, curr) => acc + curr.sprint_count, 0), pctA: 50 },
    { label: 'Shots Logged', valueA: analytics?.events?.filter(e => e.type === 'shot' && e.team === 'A').length || 0, valueB: analytics?.events?.filter(e => e.type === 'shot' && e.team === 'B').length || 0, pctA: 50 },
    { label: 'Formations Tracked', valueA: analytics?.formations?.A?.[0]?.formation || '4-3-3', valueB: analytics?.formations?.B?.[0]?.formation || '4-4-2', pctA: 50 }
  ];

  return (
    <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="overview-grid">
        {/* Stats Card */}
        <div className="glass-card-static overview-card">
          <h3 className="card-title"><BarChart3 size={16} /> Pitch Statistics</h3>
          <div className="stats-list">
            {stats.map((stat) => (
              <div className="stat-row" key={stat.label}>
                <span className="stat-val-a">{stat.valueA}</span>
                <div className="stat-bar-container">
                  <span className="stat-label">{stat.label}</span>
                  <div className="stat-bar-bg">
                    <div className="stat-bar-a" style={{ width: `${stat.pctA}%` }} />
                  </div>
                </div>
                <span className="stat-val-b">{stat.valueB}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Radar view playback */}
        <div className="glass-card-static overview-card radar-preview">
          <h3 className="card-title"><Target size={16} /> Top-Down Radar Replay</h3>
          <div className="radar-placeholder">
            <LivePitchSVG currentFrame={currentFrame} />
            
            {/* Playback Controls */}
            <div className="playback-controls" style={{ width: '100%', marginTop: 16 }}>
              <div className="slider-container" style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <span className="time-display">{formatTime(currentFrame.timestamp)}</span>
                <input 
                  type="range" 
                  min="0" 
                  max={Math.max(0, totalFrames - 1)} 
                  value={currentFrameIdx} 
                  onChange={(e) => {
                    setCurrentFrameIdx(Number(e.target.value));
                    setIsPlaying(false);
                  }}
                  className="playback-slider"
                  style={{ flex: 1 }}
                />
              </div>
              
              <div className="control-buttons" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 16 }}>
                <button 
                  className="btn btn-ghost btn-icon" 
                  onClick={() => {
                    setCurrentFrameIdx(0);
                    setIsPlaying(false);
                  }}
                >
                  <RotateCcw size={16} />
                </button>
                <button 
                  className="btn btn-primary btn-icon" 
                  style={{ padding: 12, borderRadius: '50%' }}
                  onClick={() => setIsPlaying(!isPlaying)}
                >
                  {isPlaying ? <Pause size={18} /> : <Play size={18} />}
                </button>
                
                <select 
                  value={playSpeed} 
                  onChange={(e) => setPlaySpeed(Number(e.target.value))}
                  className="speed-selector"
                  style={{ background: 'var(--bg-glass)', border: '1px solid var(--border-glass)', color: '#fff', padding: '4px 8px', borderRadius: 4 }}
                >
                  <option value={0.5}>0.5x</option>
                  <option value={1}>1.0x</option>
                  <option value={2}>2.0x</option>
                  <option value={4}>4.0x</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Events */}
        <div className="glass-card-static overview-card events-preview">
          <h3 className="card-title"><Clock size={16} /> Recent Events</h3>
          <div className="events-mini-list">
            {analytics?.events?.slice(0, 4).map((evt, i) => (
              <div className="event-mini" key={i}>
                <span className="event-time">{formatTime(evt.timestamp)}</span>
                <span className="event-icon">{eventIcon(evt.type)}</span>
                <span className="event-desc">{evt.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function LivePitchSVG({ currentFrame }) {
  return (
    <svg viewBox="0 0 105 68" className="pitch-svg" xmlns="http://www.w3.org/2000/svg" style={{ border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)' }}>
      {/* Pitch outline */}
      <rect x="0.5" y="0.5" width="104" height="67" fill="none" stroke="var(--accent)" strokeWidth="0.5" opacity="0.4" rx="1" />
      {/* Center line */}
      <line x1="52.5" y1="0.5" x2="52.5" y2="67.5" stroke="var(--accent)" strokeWidth="0.3" opacity="0.3" />
      {/* Center circle */}
      <circle cx="52.5" cy="34" r="9.15" fill="none" stroke="var(--accent)" strokeWidth="0.3" opacity="0.3" />
      {/* Penalty areas */}
      <rect x="0.5" y="13.84" width="16.5" height="40.32" fill="none" stroke="var(--accent)" strokeWidth="0.3" opacity="0.3" />
      <rect x="88.5" y="13.84" width="16.5" height="40.32" fill="none" stroke="var(--accent)" strokeWidth="0.3" opacity="0.3" />
      {/* Goal areas */}
      <rect x="0.5" y="24.84" width="5.5" height="18.32" fill="none" stroke="var(--accent)" strokeWidth="0.3" opacity="0.3" />
      <rect x="99.5" y="24.84" width="5.5" height="18.32" fill="none" stroke="var(--accent)" strokeWidth="0.3" opacity="0.3" />
      
      {/* Render player dots */}
      {currentFrame.players?.map((player) => {
        let fill = 'var(--team-a)';
        if (player.team === 'B') fill = 'var(--team-b)';
        if (player.team === 'R') fill = '#ffeb3b'; // yellow for referee
        
        return (
          <g key={player.id}>
            <circle 
              cx={player.pitch_x} 
              cy={player.pitch_y} 
              r="1.8" 
              fill={fill} 
              opacity="0.9" 
            />
            {/* Small label with player tracking ID */}
            {player.id !== -1 && (
              <text 
                x={player.pitch_x} 
                y={player.pitch_y - 2.5} 
                fill="#ffffff" 
                fontSize="2" 
                textAnchor="middle"
                fontWeight="bold"
              >
                {player.id}
              </text>
            )}
          </g>
        );
      })}

      {/* Render ball */}
      {currentFrame.ball && (
        <circle 
          cx={currentFrame.ball.pitch_x} 
          cy={currentFrame.ball.pitch_y} 
          r="1.2" 
          fill="#ffffff" 
          stroke="#000000"
          strokeWidth="0.3"
          opacity="1" 
        />
      )}
    </svg>
  );
}

function TimelineTab({ events, jumpToTimestamp, formatTime }) {
  if (!events || events.length === 0) {
    return (
      <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="glass-card-static" style={{ padding: 28, textAlign: 'center' }}>
          <p className="text-secondary">No match events logged yet.</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="glass-card-static" style={{ padding: 28 }}>
        <h3 className="card-title"><Clock size={16} /> Match Timeline</h3>
        <p className="text-muted" style={{ fontSize: '0.8rem', marginBottom: 16 }}>
          Click any event or "Jump to" to navigate the radar view to that moment.
        </p>
        <div className="timeline-list">
          {events.map((evt, i) => (
            <div 
              className={`timeline-item type-${evt.type}`} 
              key={evt.event_id || i}
            >
              <div className="timeline-dot" />
              <div className="timeline-time">{formatTime(evt.timestamp)}</div>
              <div className="timeline-body">
                <span className="timeline-icon">{eventIcon(evt.type)}</span>
                <span>{evt.message}</span>
              </div>
              <button
                className="btn btn-ghost"
                style={{ marginLeft: 'auto', fontSize: '0.78rem', whiteSpace: 'nowrap' }}
                onClick={(e) => {
                  e.stopPropagation();
                  jumpToTimestamp(evt.timestamp);
                }}
              >
                <Play size={12} /> Jump to
              </button>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function CoachTab({ analytics }) {
  const possessionPct = analytics?.possession_a || 50;
  const events = analytics?.events || [];
  const shotsA = events.filter((e) => e.type === 'shot' && e.team === 'A').length;
  const shotsB = events.filter((e) => e.type === 'shot' && e.team === 'B').length;
  const shiftsA = events.filter((e) => e.type === 'formation_shift' && e.team === 'A').length;
  const shiftsB = events.filter((e) => e.type === 'formation_shift' && e.team === 'B').length;
  const sprintsA = Object.values(analytics?.player_stats || {})
    .filter((p) => p.team === 'A')
    .reduce((acc, curr) => acc + (curr.sprint_count || 0), 0);
  const sprintsB = Object.values(analytics?.player_stats || {})
    .filter((p) => p.team === 'B')
    .reduce((acc, curr) => acc + (curr.sprint_count || 0), 0);

  const recs = [];
  if (shotsA !== shotsB) {
    const leading = shotsA > shotsB ? 'A' : 'B';
    const trailing = leading === 'A' ? 'B' : 'A';
    recs.push({
      title: 'Final-Third Chance Creation',
      body: `Team ${trailing} is trailing in logged shots. Focus on earlier ball progression into the final third to close chance volume.`,
      cite: `Based on: shots logged Team A ${shotsA} vs Team B ${shotsB}.`,
      icon: <Target size={16} className="text-accent" />,
    });
  }

  if (Math.abs(possessionPct - 50) >= 8) {
    const trailing = possessionPct > 50 ? 'B' : 'A';
    recs.push({
      title: 'Possession Control',
      body: `Team ${trailing} should prioritize safer midfield circulation after regains to reduce immediate turnovers.`,
      cite: `Based on: possession split Team A ${possessionPct}% vs Team B ${100 - possessionPct}%.`,
      icon: <Shield size={16} className="text-accent" />,
    });
  }

  if (shiftsA + shiftsB > 0) {
    recs.push({
      title: 'Shape Stability',
      body: 'Frequent formation shifts suggest unstable spacing. Reinforce line compactness during transitions.',
      cite: `Based on: formation shifts Team A ${shiftsA}, Team B ${shiftsB}.`,
      icon: <TrendingUp size={16} className="text-accent" />,
    });
  }

  if (recs.length === 0) {
    recs.push({
      title: 'Transition Intensity',
      body: 'Use sprint bursts selectively around pressing triggers instead of sustained chasing to keep structure intact.',
      cite: `Based on: sprint events Team A ${sprintsA}, Team B ${sprintsB}; possession Team A ${possessionPct}% vs Team B ${100 - possessionPct}%.`,
      icon: <Zap size={16} className="text-accent" />,
    });
  }

  const performanceScore = Math.max(6.5, Math.min(9.4, 7.2 + ((possessionPct - 50) / 30) + ((shotsA - shotsB) / 12))).toFixed(1);
  
  return (
    <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="coach-grid">
        <div className="glass-card-static" style={{ padding: 28 }}>
          <h3 className="card-title"><Brain size={16} /> AI Coach Recommendations</h3>
          <div className="coach-content">
            {recs.map((rec, idx) => (
              <div className="coach-rec" key={idx}>
                <div className="rec-header">
                  {rec.icon}
                  <strong>{rec.title}</strong>
                </div>
                <p>{rec.body}</p>
                <span className="rec-citation text-muted">📊 {rec.cite}</span>
              </div>
            ))}
          </div>
          <p className="text-muted" style={{ fontSize: '0.78rem', marginTop: 20, fontStyle: 'italic' }}>
            Recommendations above are generated from tracked events and team stats for this match.
          </p>
        </div>

        <div className="glass-card-static coach-score-card">
          <h3 className="card-title"><Activity size={16} /> Performance Score</h3>
          <div className="score-circle">
            <span className="score-big font-display">{performanceScore}</span>
            <span className="score-label text-muted">/10</span>
          </div>
          <p className="text-secondary" style={{ textAlign: 'center', fontSize: '0.85rem' }}>Overall Team Rating</p>
        </div>
      </div>
    </motion.div>
  );
}

function PlayersTab({ playerStats }) {
  const players = Object.entries(playerStats);
  
  if (players.length === 0) {
    return (
      <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="glass-card-static" style={{ padding: 28, textAlign: 'center' }}>
          <p className="text-secondary">No player tracking data available for statistics.</p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="glass-card-static" style={{ padding: 28 }}>
        <h3 className="card-title"><Users size={16} /> Player Performance</h3>
        <p className="text-secondary" style={{ fontSize: '0.9rem', marginBottom: 20 }}>
          Individual tracking metrics generated automatically by the perception pipeline.
        </p>
        <div className="player-placeholder-grid">
          {players.map(([id, stats]) => (
            <div className="player-card glass-card" key={id}>
              <div className="player-num">#{id}</div>
              <div className="player-stats-mini">
                <span style={{ fontWeight: 'bold', color: stats.team === 'A' ? 'var(--team-a)' : 'var(--team-b)' }}>
                  Team {stats.team}
                </span>
                <span>Distance: {stats.distance_meters}m</span>
                <span>Sprints: {stats.sprint_count}</span>
                <span>Avg Speed: {stats.average_speed_mps} m/s</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
