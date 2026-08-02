import { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BarChart3, Users, Brain, Clock, Target, TrendingUp,
  Play, Pause, RotateCcw, Activity, Shield, Zap, AlertTriangle, Footprints,
  Film, Download, Volume2, FileText, Sparkles, Cloud, Upload, ExternalLink,
  HardDrive, CheckCircle
} from 'lucide-react';
import './Dashboard.css';

// Base backend URL config (matches Upload page behavior)
const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const API_BASE_URL = `${API_BASE}/api`;

const tabs = [
  { id: 'overview', label: 'Overview', icon: <BarChart3 size={16} /> },
  { id: 'timeline', label: 'Timeline', icon: <Clock size={16} /> },
  { id: 'highlights', label: 'Highlights', icon: <Film size={16} /> },
  { id: 'coach', label: 'AI Coach', icon: <Brain size={16} /> },
  { id: 'players', label: 'Players', icon: <Users size={16} /> },
  { id: 'storage', label: 'B2 Storage', icon: <Cloud size={16} /> },
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
              matchId={matchId}
            />
          )}
          {activeTab === 'highlights' && (
            <HighlightsTab matchId={matchId} />
          )}
          {activeTab === 'players' && (
            <PlayersTab 
              playerStats={analytics?.player_stats || {}}
            />
          )}
          {activeTab === 'storage' && (
            <StorageTab matchId={matchId} />
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

function CoachTab({ analytics, matchId }) {
  const [coachData, setCoachData] = useState(null);
  const [coachLoading, setCoachLoading] = useState(true);
  const [coachError, setCoachError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setCoachLoading(true);
    setCoachError(null);

    fetch(`${API_BASE_URL}/coach/${matchId}/coach`)
      .then((res) => {
        if (!res.ok) throw new Error(`Coach API error: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (!cancelled) {
          setCoachData(data);
          setCoachLoading(false);
        }
      })
      .catch((err) => {
        console.error('[CoachTab] Error:', err);
        if (!cancelled) {
          setCoachError(err.message);
          setCoachLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [matchId]);

  if (coachLoading) {
    return (
      <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="glass-card-static" style={{ padding: 48, textAlign: 'center' }}>
          <Brain size={28} className="text-accent pulse-animation" />
          <p className="text-secondary" style={{ marginTop: 12 }}>
            Analyzing match data for tactical insights...
          </p>
        </div>
      </motion.div>
    );
  }

  if (coachError) {
    return (
      <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
        <div className="glass-card-static" style={{ padding: 28, textAlign: 'center' }}>
          <AlertTriangle size={24} style={{ color: 'var(--team-b)' }} />
          <p className="text-secondary" style={{ marginTop: 8 }}>
            Could not load AI Coach: {coachError}
          </p>
        </div>
      </motion.div>
    );
  }

  const recs = coachData?.recommendations || [];
  const mode = coachData?.mode || 'heuristic';
  const scores = coachData?.performance_scores || { A: 7.2, B: 7.2 };

  const categoryColors = {
    tactical: { bg: 'rgba(99,102,241,0.15)', color: '#818cf8', border: 'rgba(99,102,241,0.3)' },
    attacking: { bg: 'rgba(0,255,120,0.1)', color: 'var(--accent)', border: 'rgba(0,255,120,0.25)' },
    defensive: { bg: 'rgba(255,107,107,0.12)', color: 'var(--team-b)', border: 'rgba(255,107,107,0.25)' },
    physical: { bg: 'rgba(251,191,36,0.12)', color: '#fbbf24', border: 'rgba(251,191,36,0.25)' },
    set_piece: { bg: 'rgba(103,232,249,0.12)', color: '#67e8f9', border: 'rgba(103,232,249,0.25)' },
  };

  const priorityDot = { high: '#ff6b6b', medium: '#fbbf24', low: '#4ade80' };

  const categoryIcon = (cat) => {
    if (cat === 'attacking') return <Target size={15} />;
    if (cat === 'defensive') return <Shield size={15} />;
    if (cat === 'physical') return <Zap size={15} />;
    return <TrendingUp size={15} />;
  };

  return (
    <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div className="coach-grid">
        <div className="glass-card-static" style={{ padding: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
            <h3 className="card-title" style={{ marginBottom: 0 }}>
              <Brain size={16} /> AI Coach Recommendations
            </h3>
            <span style={{
              fontSize: '0.7rem', padding: '3px 10px', borderRadius: 999,
              background: mode === 'llm' ? 'rgba(0,255,120,0.12)' : 'rgba(251,191,36,0.12)',
              color: mode === 'llm' ? 'var(--accent)' : '#fbbf24',
              border: `1px solid ${mode === 'llm' ? 'rgba(0,255,120,0.3)' : 'rgba(251,191,36,0.3)'}`,
              fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px',
            }}>
              {mode === 'llm' ? '⚡ LLM-Powered' : '📊 Data-Driven'}
            </span>
          </div>

          <div className="coach-content">
            {recs.map((rec, idx) => {
              const cat = rec.category || 'tactical';
              const pri = rec.priority || 'medium';
              const catStyle = categoryColors[cat] || categoryColors.tactical;
              return (
                <motion.div
                  className="coach-rec"
                  key={idx}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.08 }}
                  style={{ borderLeftColor: catStyle.color }}
                >
                  <div className="rec-header">
                    <span style={{ color: catStyle.color }}>{categoryIcon(cat)}</span>
                    <strong>{rec.title}</strong>
                    <span style={{
                      marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
                    }}>
                      <span style={{
                        fontSize: '0.65rem', padding: '2px 8px', borderRadius: 999,
                        background: catStyle.bg, color: catStyle.color, border: `1px solid ${catStyle.border}`,
                        fontWeight: 600, textTransform: 'capitalize',
                      }}>{cat}</span>
                      <span style={{
                        width: 7, height: 7, borderRadius: '50%',
                        background: priorityDot[pri] || priorityDot.medium,
                      }} title={`${pri} priority`} />
                    </span>
                  </div>
                  <p>{rec.body}</p>
                  <span className="rec-citation text-muted">📊 {rec.citation}</span>
                </motion.div>
              );
            })}
          </div>

          <p className="text-muted" style={{ fontSize: '0.76rem', marginTop: 20, fontStyle: 'italic' }}>
            {mode === 'llm'
              ? 'Recommendations generated by AI, grounded in real tracked match data.'
              : 'Recommendations generated from heuristic analysis of tracked match events and stats.'}
          </p>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <div className="glass-card-static coach-score-card">
            <h3 className="card-title"><Activity size={16} /> Team A Rating</h3>
            <div className="score-circle">
              <span className="score-big font-display">{scores.A}</span>
              <span className="score-label text-muted">/10</span>
            </div>
          </div>
          <div className="glass-card-static coach-score-card">
            <h3 className="card-title" style={{ color: 'var(--team-b)' }}>
              <Activity size={16} /> Team B Rating
            </h3>
            <div className="score-circle">
              <span className="score-big font-display" style={{ color: 'var(--team-b)' }}>{scores.B}</span>
              <span className="score-label text-muted">/10</span>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function HighlightsTab({ matchId }) {
  const [hlStatus, setHlStatus] = useState(null);
  const [commentary, setCommentary] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [polling, setPolling] = useState(false);

  // Check status on mount
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/highlights/${matchId}/status`)
      .then((r) => r.json())
      .then((data) => { if (!cancelled) setHlStatus(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [matchId]);

  // Load commentary if already generated
  useEffect(() => {
    if (hlStatus?.phase === 'complete') {
      fetch(`${API_BASE_URL}/highlights/${matchId}/commentary`)
        .then((r) => r.ok ? r.json() : null)
        .then((data) => { if (data) setCommentary(data.commentary); })
        .catch(() => {});
    }
  }, [hlStatus?.phase, matchId]);

  // Poll while generating
  useEffect(() => {
    if (!polling) return;
    const iv = setInterval(() => {
      fetch(`${API_BASE_URL}/highlights/${matchId}/status`)
        .then((r) => r.json())
        .then((data) => {
          setHlStatus(data);
          if (data.phase === 'complete' || data.phase === 'failed') {
            setPolling(false);
            setGenerating(false);
          }
        })
        .catch(() => {});
    }, 1500);
    return () => clearInterval(iv);
  }, [polling, matchId]);

  const handleGenerate = () => {
    setGenerating(true);
    setPolling(true);
    fetch(`${API_BASE_URL}/highlights/${matchId}/generate`, { method: 'POST' })
      .then((r) => r.json())
      .catch((err) => {
        setGenerating(false);
        setPolling(false);
        console.error('[Highlights]', err);
      });
  };

  const isComplete = hlStatus?.phase === 'complete';
  const isFailed = hlStatus?.phase === 'failed';
  const isRunning = generating || (hlStatus && !['complete', 'failed', 'not_started'].includes(hlStatus.phase));
  const progressPct = hlStatus ? Math.round((hlStatus.progress || 0) * 100) : 0;

  // Event type to icon (reuse from timeline)
  const commentaryIcon = (type) => {
    if (type === 'goal') return <Target size={14} style={{ color: 'var(--accent)' }} />;
    if (type === 'shot') return <Target size={14} style={{ color: 'var(--team-b)' }} />;
    if (type === 'sprint') return <Zap size={14} className="text-accent" />;
    if (type === 'dribble') return <Footprints size={14} style={{ color: '#f59e0b' }} />;
    if (type === 'possession_change') return <Shield size={14} style={{ color: 'var(--team-a)' }} />;
    return <Activity size={14} />;
  };

  const formatTime = (s) => {
    if (isNaN(s)) return '00:00';
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`;
  };

  return (
    <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* Generate / Status Card */}
        <div className="glass-card-static" style={{ padding: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 className="card-title" style={{ marginBottom: 0 }}>
              <Film size={16} /> Highlight Reel Generator
            </h3>
            {isComplete && (
              <span style={{
                fontSize: '0.7rem', padding: '3px 10px', borderRadius: 999,
                background: 'rgba(0,255,120,0.12)', color: 'var(--accent)',
                border: '1px solid rgba(0,255,120,0.3)', fontWeight: 600,
              }}>
                <Sparkles size={10} /> Generated
              </span>
            )}
          </div>

          {!isComplete && !isRunning && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <p className="text-secondary" style={{ marginBottom: 16, fontSize: '0.9rem' }}>
                Generate an AI-powered highlight reel from the most important match moments.
                Commentary will be created for each key event.
              </p>
              <button
                className="btn btn-primary"
                onClick={handleGenerate}
                disabled={generating}
                style={{ padding: '10px 28px', fontSize: '0.9rem', gap: 8, display: 'inline-flex', alignItems: 'center' }}
              >
                <Sparkles size={16} /> Generate Highlights
              </button>
              {isFailed && hlStatus?.error && (
                <p style={{ color: 'var(--team-b)', fontSize: '0.8rem', marginTop: 12 }}>
                  {hlStatus.error}
                </p>
              )}
            </div>
          )}

          {isRunning && (
            <div style={{ padding: '12px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <Film size={18} className="text-accent pulse-animation" />
                <span className="text-secondary" style={{ fontSize: '0.88rem' }}>
                  {hlStatus?.message || 'Starting generation...'}
                </span>
              </div>
              <div className="progress-container">
                <div className="progress-bar-bg">
                  <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
                </div>
                <span className="progress-pct font-display">{progressPct}%</span>
              </div>
            </div>
          )}

          {isComplete && (
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              {hlStatus?.reel_available && (
                <>
                  <a
                    href={`${API_BASE_URL}/highlights/${matchId}/reel`}
                    download
                    className="btn btn-primary"
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}
                  >
                    <Download size={16} /> Download Highlight Reel
                  </a>
                  <button
                    className="btn btn-ghost"
                    onClick={handleGenerate}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
                  >
                    <RotateCcw size={14} /> Regenerate
                  </button>
                </>
              )}
              {!hlStatus?.reel_available && (
                <p className="text-muted" style={{ fontSize: '0.82rem' }}>
                  <AlertTriangle size={12} /> Video reel not available (FFmpeg required).
                  Commentary was generated successfully below.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Video Player */}
        {isComplete && hlStatus?.reel_available && (
          <div className="glass-card-static" style={{ padding: 28 }}>
            <h3 className="card-title"><Play size={16} /> Highlight Reel</h3>
            <video
              controls
              style={{
                width: '100%', maxHeight: 420, borderRadius: 'var(--radius-md)',
                background: '#000', marginTop: 8,
              }}
              src={`${API_BASE_URL}/highlights/${matchId}/reel`}
            />
          </div>
        )}

        {/* Commentary */}
        {commentary && commentary.length > 0 && (
          <div className="glass-card-static" style={{ padding: 28 }}>
            <h3 className="card-title"><FileText size={16} /> Match Commentary</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
              {commentary.map((line, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.04 }}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 12,
                    padding: '12px 14px', borderRadius: 'var(--radius-md)',
                    background: 'rgba(255,255,255,0.02)',
                    borderLeft: `3px solid ${line.event_type === 'goal' ? 'var(--accent)' : 'var(--border-glass)'}`,
                  }}
                >
                  <span style={{ minWidth: 42, fontSize: '0.78rem', fontWeight: 600, color: 'var(--accent)' }}>
                    {formatTime(line.timestamp)}
                  </span>
                  <span style={{ color: 'var(--text-muted)' }}>
                    {commentaryIcon(line.event_type)}
                  </span>
                  <span style={{ fontSize: '0.86rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    {line.text}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        )}
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

function StorageTab({ matchId }) {
  const [storageStatus, setStorageStatus] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [assets, setAssets] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [polling, setPolling] = useState(false);

  // Check storage config + upload status on mount
  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE_URL}/storage/status`)
      .then((r) => r.json())
      .then((data) => { if (!cancelled) setStorageStatus(data); })
      .catch(() => {});
    fetch(`${API_BASE_URL}/storage/${matchId}/upload-status`)
      .then((r) => r.json())
      .then((data) => { if (!cancelled) setUploadStatus(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [matchId]);

  // Load assets if upload is complete
  useEffect(() => {
    if (uploadStatus?.phase === 'complete') {
      fetch(`${API_BASE_URL}/storage/${matchId}/assets`)
        .then((r) => r.ok ? r.json() : null)
        .then((data) => { if (data) setAssets(data.assets); })
        .catch(() => {});
    }
  }, [uploadStatus?.phase, matchId]);

  // Poll while uploading
  useEffect(() => {
    if (!polling) return;
    const iv = setInterval(() => {
      fetch(`${API_BASE_URL}/storage/${matchId}/upload-status`)
        .then((r) => r.json())
        .then((data) => {
          setUploadStatus(data);
          if (data.phase === 'complete' || data.phase === 'failed') {
            setPolling(false);
            setUploading(false);
          }
        })
        .catch(() => {});
    }, 2000);
    return () => clearInterval(iv);
  }, [polling, matchId]);

  const handleUpload = () => {
    setUploading(true);
    setPolling(true);
    fetch(`${API_BASE_URL}/storage/${matchId}/upload`, { method: 'POST' })
      .then((r) => r.json())
      .catch(() => { setUploading(false); setPolling(false); });
  };

  const formatSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1048576).toFixed(1)} MB`;
  };

  const isConfigured = storageStatus?.configured;
  const isComplete = uploadStatus?.phase === 'complete';
  const isFailed = uploadStatus?.phase === 'failed';
  const isRunning = uploading || (uploadStatus && !['complete', 'failed', 'not_started'].includes(uploadStatus.phase));
  const progressPct = uploadStatus ? Math.round((uploadStatus.progress || 0) * 100) : 0;

  const fileIcon = (name) => {
    if (name.endsWith('.mp4')) return <Film size={14} />;
    if (name.endsWith('.json')) return <FileText size={14} />;
    return <HardDrive size={14} />;
  };

  return (
    <motion.div className="tab-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

        {/* B2 Status Card */}
        <div className="glass-card-static" style={{ padding: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <h3 className="card-title" style={{ marginBottom: 0 }}>
              <Cloud size={16} /> Backblaze B2 Cloud Storage
            </h3>
            {isConfigured && (
              <span style={{
                fontSize: '0.7rem', padding: '3px 10px', borderRadius: 999,
                background: 'rgba(0,255,120,0.12)', color: 'var(--accent)',
                border: '1px solid rgba(0,255,120,0.3)', fontWeight: 600,
              }}>
                <CheckCircle size={10} /> Connected
              </span>
            )}
          </div>

          {!isConfigured && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <AlertTriangle size={24} style={{ color: '#fbbf24', marginBottom: 8 }} />
              <p className="text-secondary" style={{ fontSize: '0.88rem' }}>
                B2 credentials not configured. Add B2_APPLICATION_KEY_ID and B2_APPLICATION_KEY to your .env file.
              </p>
            </div>
          )}

          {isConfigured && !isComplete && !isRunning && (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <p className="text-secondary" style={{ marginBottom: 16, fontSize: '0.9rem' }}>
                Upload all match assets (video, tracking data, commentary, highlights, provenance manifest) to Backblaze B2 for permanent cloud storage.
              </p>
              <button
                className="btn btn-primary"
                onClick={handleUpload}
                disabled={uploading}
                style={{ padding: '10px 28px', fontSize: '0.9rem', gap: 8, display: 'inline-flex', alignItems: 'center' }}
              >
                <Upload size={16} /> Upload to B2
              </button>
            </div>
          )}

          {isRunning && (
            <div style={{ padding: '12px 0' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <Cloud size={18} className="text-accent pulse-animation" />
                <span className="text-secondary" style={{ fontSize: '0.88rem' }}>
                  {uploadStatus?.message || 'Starting upload...'}
                </span>
              </div>
              <div className="progress-container">
                <div className="progress-bar-bg">
                  <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
                </div>
                <span className="progress-pct font-display">{progressPct}%</span>
              </div>
            </div>
          )}

          {isComplete && (
            <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', alignItems: 'center' }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px',
                background: 'rgba(0,255,120,0.08)', borderRadius: 'var(--radius-md)',
                border: '1px solid rgba(0,255,120,0.2)',
              }}>
                <CheckCircle size={16} style={{ color: 'var(--accent)' }} />
                <span style={{ fontSize: '0.88rem' }}>
                  {uploadStatus.asset_count} assets uploaded ({formatSize(uploadStatus.total_size_bytes)})
                </span>
              </div>
              <button
                className="btn btn-ghost"
                onClick={handleUpload}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}
              >
                <RotateCcw size={14} /> Re-upload
              </button>
            </div>
          )}
        </div>

        {/* Assets List */}
        {assets && assets.length > 0 && (
          <div className="glass-card-static" style={{ padding: 28 }}>
            <h3 className="card-title"><HardDrive size={16} /> Stored Assets</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
              {assets.map((asset, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 12,
                    padding: '10px 14px', borderRadius: 'var(--radius-md)',
                    background: 'rgba(255,255,255,0.02)',
                  }}
                >
                  <span style={{ color: 'var(--accent)' }}>{fileIcon(asset.filename)}</span>
                  <span style={{ flex: 1, fontSize: '0.85rem' }}>{asset.filename}</span>
                  <span className="text-muted" style={{ fontSize: '0.78rem' }}>
                    {formatSize(asset.size_bytes)}
                  </span>
                  <span className="text-muted" style={{ fontSize: '0.72rem' }}>
                    {new Date(asset.last_modified).toLocaleDateString()}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
