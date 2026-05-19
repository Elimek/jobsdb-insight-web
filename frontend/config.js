// JobsDB Insight - Backend API URL
// Change this to your deployed backend address
const API_URL = (() => {
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8899';
  }
  // TODO: Replace with your Render/Railway backend URL
  return 'https://YOUR-BACKEND.onrender.com';
})();
