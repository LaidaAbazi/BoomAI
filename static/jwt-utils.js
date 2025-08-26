// JWT Token Management Utilities

// Token storage keys
const ACCESS_TOKEN_KEY = 'accessToken';
const REFRESH_TOKEN_KEY = 'refreshToken';

// Get tokens from localStorage
function getAccessToken() {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
}

function getRefreshToken() {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
}

// Store tokens in localStorage
function setTokens(accessToken, refreshToken) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

// Clear tokens from localStorage
function clearTokens() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
}

// Check if user is authenticated
function isAuthenticated() {
    return !!getAccessToken();
}

// Make authenticated API calls with automatic token refresh
async function authenticatedFetch(url, options = {}) {
    // Add Authorization header if token exists
    const accessToken = getAccessToken();
    if (accessToken) {
        options.headers = {
            ...options.headers,
            'Authorization': `Bearer ${accessToken}`
        };
    }
    
    try {
        const response = await fetch(url, options);
        
        // If token expired, try to refresh
        if (response.status === 401 && getRefreshToken()) {
            const refreshResponse = await fetch('/api/refresh', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getRefreshToken()}`
                }
            });
            
            if (refreshResponse.ok) {
                const { access_token } = await refreshResponse.json();
                setTokens(access_token, getRefreshToken());
                
                // Retry original request with new token
                options.headers = {
                    ...options.headers,
                    'Authorization': `Bearer ${access_token}`
                };
                return await fetch(url, options);
            } else {
                // Refresh failed, redirect to login
                logout();
                return response;
            }
        }
        
        return response;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

// Logout function
function logout() {
    clearTokens();
    window.location.href = '/login';
}

// Check authentication status and redirect if needed
async function checkAuth() {
    if (!isAuthenticated()) {
        window.location.href = '/login';
        return false;
    }
    
    try {
        const response = await authenticatedFetch('/api/user');
        if (response.status === 401) {
            logout();
            return false;
        }
        return true;
    } catch (error) {
        console.error('Auth check failed:', error);
        logout();
        return false;
    }
}

// Export functions for use in other scripts
window.JWTUtils = {
    getAccessToken,
    getRefreshToken,
    setTokens,
    clearTokens,
    isAuthenticated,
    authenticatedFetch,
    logout,
    checkAuth
}; 