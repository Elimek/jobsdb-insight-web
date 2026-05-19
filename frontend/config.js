// Backend API URL for JobsDB Insight
// Change this to your deployed backend URL
const API_URL = (() => {
  // Auto-detect: if running locally, use localhost
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8899';
  }
  // For GitHub Pages deployment, point to your Render/Railway backend
  return 'https://YOUR-BACKEND.onrender.com';
})();
