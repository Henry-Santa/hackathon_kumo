// Configuration for API endpoints
export const config = {
  // API base URL - defaults to localhost for development
  apiBaseUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  
  // Helper function to build full API URLs
  apiUrl: (endpoint: string) => {
    const base = config.apiBaseUrl;
    // Remove leading slash if present
    const cleanEndpoint = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
    return `${base}/${cleanEndpoint}`;
  }
};
