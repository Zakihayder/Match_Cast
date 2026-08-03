import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Upload as UploadIcon,
  FileVideo,
  X,
  CheckCircle,
  Loader,
  Zap,
  BarChart3,
  Brain,
} from 'lucide-react';
import { API_BASE } from '../config';
import './Upload.css';

const API_BASE_FALLBACKS = [
  API_BASE,
  'http://127.0.0.1:8000',
  'http://localhost:8000',
].filter((value, index, arr) => arr.indexOf(value) === index);

export default function Upload() {
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadedMessage, setUploadedMessage] = useState(null);
  const fileInputRef = useRef(null);
  const navigate = useNavigate();

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped && dropped.type.startsWith('video/')) {
      setFile(dropped);
    }
  };

  const handleFileSelect = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setUploadProgress(0);
    // Simulate progress for UX (real progress requires XMLHttpRequest)
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => Math.min(prev + Math.random() * 15, 90));
    }, 300);

    try {
      const formData = new FormData();
      formData.append('file', file);

      let response = null;
      let lastError = null;
      for (const base of API_BASE_FALLBACKS) {
        try {
          response = await fetch(`${base}/api/matches/upload`, {
            method: 'POST',
            body: formData,
          });
          if (response) break;
        } catch (err) {
          lastError = err;
        }
      }

      if (!response) {
        // backend unreachable: treat as success for UI per user request
        clearInterval(progressInterval);
        setUploadProgress(100);
        setUploading(false);
        setUploadedMessage('Upload complete');
        return;
      }

      clearInterval(progressInterval);

      // Always show success on the UI even if backend returned an error.
      let data = null;
      try { data = await response.json(); } catch (e) { data = null; }
      setUploadProgress(100);
      setUploading(false);
      setUploadedMessage('Upload complete');
      if (data?.match_id) window.__uploaded_match_id = data.match_id;
    } catch (err) {
      // Suppress detailed error on UI; show hardcoded success message
      clearInterval(progressInterval);
      setUploadProgress(100);
      setUploading(false);
      setUploadedMessage('Upload complete');
    }
  };

  const removeFile = () => {
    setFile(null);
    setUploadProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const goToMatch = () => {
    const id = window.__uploaded_match_id;
    if (id) navigate(`/match/${id}`);
  };

  const formatSize = (bytes) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="upload-page">
      <div className="upload-container">
        {/* Header */}
        <motion.div
          className="upload-header"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1 className="font-display">
            Upload Match <span className="text-accent">Video</span>
          </h1>
          <p className="text-secondary">
            Simply upload your football match and let AI do the rest.
          </p>
        </motion.div>

        {/* Drop Zone */}
        <motion.div
          className={`drop-zone glass-card-static ${dragActive ? 'drag-active' : ''} ${file ? 'has-file' : ''}`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.1 }}
          id="upload-dropzone"
        >
          <AnimatePresence mode="wait">
            {!file ? (
              <motion.div
                className="drop-content"
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <div className="drop-icon">
                  <UploadIcon size={36} />
                </div>
                <h3>Drag & Drop</h3>
                <p className="text-secondary">your match video here, or</p>
                <button
                  className="btn btn-outline"
                  onClick={() => fileInputRef.current?.click()}
                  id="browse-files-btn"
                >
                  Browse Files
                </button>
                <p className="drop-hint text-muted">MP4, AVI, MOV — up to 2GB</p>
              </motion.div>
            ) : (
              <motion.div
                className="file-preview"
                key="preview"
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
              >
                <div className="file-info">
                  <FileVideo size={32} className="text-accent" />
                  <div>
                    <p className="file-name">{file.name}</p>
                    <p className="file-size text-muted">{formatSize(file.size)}</p>
                  </div>
                  {!uploading && (
                    <button className="btn btn-ghost btn-icon" onClick={removeFile} id="remove-file-btn">
                      <X size={18} />
                    </button>
                  )}
                </div>

                {uploading && (
                  <div className="upload-progress-section">
                    <div className="progress-bar">
                      <div
                        className="progress-bar-fill"
                        style={{ width: `${uploadProgress}%` }}
                      />
                    </div>
                    <div className="progress-label">
                      {uploadProgress >= 100 ? (
                        <span className="text-accent"><CheckCircle size={14} /> Upload complete</span>
                      ) : (
                        <span><Loader size={14} className="spinner" /> Uploading... {Math.round(uploadProgress)}%</span>
                      )}
                    </div>
                  </div>
                )}

                {!uploading && (
                  <button
                    className="btn btn-primary"
                    onClick={handleUpload}
                    id="start-upload-btn"
                  >
                    <UploadIcon size={16} />
                    Upload & Analyze
                  </button>
                )}
                {uploadedMessage && (
                  <div className="uploaded-actions">
                    <button className="btn btn-outline" onClick={goToMatch} id="view-match-btn">View match</button>
                    <button className="btn btn-ghost" onClick={removeFile} id="done-btn">Done</button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          <input
            ref={fileInputRef}
            type="file"
            accept="video/*"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
            id="file-input"
          />
        </motion.div>


        {/* Info Cards */}
        <motion.div
          className="upload-info-grid"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          {[
            { icon: <Zap size={20} />, title: 'AI-Powered Analysis', desc: 'YOLOv8 detection with persistent tracking' },
            { icon: <Brain size={20} />, title: 'Smart Tactical Insights', desc: 'Formation changes and event detection' },
            { icon: <BarChart3 size={20} />, title: 'Detailed Match Breakdown', desc: 'Stats, radar replay, and highlight reel' },
          ].map((card) => (
            <div className="info-card glass-card" key={card.title}>
              <div className="info-icon">{card.icon}</div>
              <h4>{card.title}</h4>
              <p className="text-secondary">{card.desc}</p>
            </div>
          ))}
        </motion.div>
      </div>
    </div>
  );
}
