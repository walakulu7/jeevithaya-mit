// API Helper Functions for communicating with Django backend

const API_BASE_URL = '/api';

// Generic API request function
async function apiRequest(endpoint, method = 'GET', data = null) {
  const options = {
    method: method,
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'same-origin',
  };

  if (data && method !== 'GET') {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    
    // Handle 204 No Content responses
    if (response.status === 204) {
      return null;
    }

    const json = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(json.error || `HTTP error! status: ${response.status}`);
    }

    return json;
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// Authentication API
const authAPI = {
  login: (email, password, role) => apiRequest('/auth/login/', 'POST', { email, password, role }),
  logout: () => apiRequest('/auth/logout/', 'POST'),
  me: () => apiRequest('/auth/me/', 'GET'),
};

// Donor API
const donorAPI = {
  getAll: () => apiRequest('/donors/', 'GET'),
  getById: (id) => apiRequest(`/donors/${id}/`, 'GET'),
  create: (data) => apiRequest('/donors/', 'POST', data),
  update: (id, data) => apiRequest(`/donors/${id}/`, 'PUT', data),
  delete: (id) => apiRequest(`/donors/${id}/`, 'DELETE'),
};

// Patient API
const patientAPI = {
  getAll: () => apiRequest('/patients/', 'GET'),
  getById: (id) => apiRequest(`/patients/${id}/`, 'GET'),
  create: (data) => apiRequest('/patients/', 'POST', data),
  update: (id, data) => apiRequest(`/patients/${id}/`, 'PUT', data),
  delete: (id) => apiRequest(`/patients/${id}/`, 'DELETE'),
};

// Request API
const requestAPI = {
  getAll: () => apiRequest('/requests/', 'GET'),
  getById: (id) => apiRequest(`/requests/${id}/`, 'GET'),
  create: (data) => apiRequest('/requests/', 'POST', data),
  update: (id, data) => apiRequest(`/requests/${id}/`, 'PUT', data),
  delete: (id) => apiRequest(`/requests/${id}/`, 'DELETE'),
};

// Donation API
const donationAPI = {
  getAll: () => apiRequest('/donations/', 'GET'),
  getById: (id) => apiRequest(`/donations/${id}/`, 'GET'),
  create: (data) => apiRequest('/donations/', 'POST', data),
  update: (id, data) => apiRequest(`/donations/${id}/`, 'PUT', data),
  delete: (id) => apiRequest(`/donations/${id}/`, 'DELETE'),
};

// Inventory API
const inventoryAPI = {
  getAll: () => apiRequest('/inventory/', 'GET'),
  getById: (id) => apiRequest(`/inventory/${id}/`, 'GET'),
  create: (data) => apiRequest('/inventory/', 'POST', data),
  update: (id, data) => apiRequest(`/inventory/${id}/`, 'PUT', data),
  delete: (id) => apiRequest(`/inventory/${id}/`, 'DELETE'),
};

// Verification API
const verificationAPI = {
  getAll: () => apiRequest('/verifications/', 'GET'),
  getById: (id) => apiRequest(`/verifications/${id}/`, 'GET'),
  create: (data) => apiRequest('/verifications/', 'POST', data),
  update: (id, data) => apiRequest(`/verifications/${id}/`, 'PUT', data),
  delete: (id) => apiRequest(`/verifications/${id}/`, 'DELETE'),
};

// Disposal API
const disposalAPI = {
  getAll: () => apiRequest('/disposals/', 'GET'),
  getById: (id) => apiRequest(`/disposals/${id}/`, 'GET'),
  create: (data) => apiRequest('/disposals/', 'POST', data),
  update: (id, data) => apiRequest(`/disposals/${id}/`, 'PUT', data),
  delete: (id) => apiRequest(`/disposals/${id}/`, 'DELETE'),
};

// User API
const userAPI = {
  getAll: () => apiRequest('/users/', 'GET'),
  getById: (id) => apiRequest(`/users/${id}/`, 'GET'),
  create: (data) => apiRequest('/users/', 'POST', data),
  update: (id, data) => apiRequest(`/users/${id}/`, 'PUT', data),
  delete: (id) => apiRequest(`/users/${id}/`, 'DELETE'),
};

// Dashboard Stats API
const dashboardAPI = {
  getStats: () => apiRequest('/dashboard/stats/', 'GET'),
};

// Make all functions globally accessible
window.apiRequest = apiRequest;
window.authAPI = authAPI;
window.donorAPI = donorAPI;
window.patientAPI = patientAPI;
window.requestAPI = requestAPI;
window.donationAPI = donationAPI;
window.inventoryAPI = inventoryAPI;
window.verificationAPI = verificationAPI;
window.disposalAPI = disposalAPI;
window.userAPI = userAPI;
window.dashboardAPI = dashboardAPI;
