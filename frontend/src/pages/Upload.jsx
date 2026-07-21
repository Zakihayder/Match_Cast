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
import './Upload.css';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
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
  const [error, setError] = useState(null);
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
      setError(null);
    } else {
      setError('Please drop a video file (MP4, AVI, MOV)');
    }
  };

  const handleFileSelect = (e) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setUploadProgress(0);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      // Simulate progress for UX (real progress requires XMLHttpRequest)
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => Math.min(prev + Math.random() * 15, 90));
      }, 300);

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
        throw new Error(lastError?.message || 'Upload failed: backend unreachable');
      }

      clearInterval(progressInterval);

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await response.json();
      setUploadProgress(100);

      // Navigate to dashboard after short delay
      setTimeout(() => {
        navigate(`/match/${data.match_id}`);
      }, 800);
    } catch (err) {
      setError(
        err.message ||
        'Failed to upload. Ensure backend is running at http://127.0.0.1:8000 and retry.'
      );
      setUploading(false);
      setUploadProgress(0);
    }
  };

  const removeFile = () => {
    setFile(null);
    setError(null);
    setUploadProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
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
                        <span className="text-accent"><CheckCircle size={14} /> Uploaded!</span>
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

        {/* Error */}
        {error && (
          <motion.div
            className="upload-error"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
          >
            {error}
          </motion.div>
        )}

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
