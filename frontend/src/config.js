/**
 * MatchCast AI — Frontend Configuration
 *
 * Centralizes the API base URL so every page reads from one place.
 * In production (Vercel), set the VITE_API_URL env variable to your
 * Railway backend URL (e.g. https://matchcast-ai-backend.up.railway.app).
 */

export const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
export const API_BASE_URL = `${API_BASE}/api`;
