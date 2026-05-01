/**
 * Global Configuration for Naganaverse Mobile App
 */

const IS_PRODUCTION = false; // Toggle this to switch environments

export const CONFIG = {
  // Use localhost for local dev, or your production server URL for final deployment
  BASE_URL: IS_PRODUCTION 
    ? "https://your-production-api.com" 
    : "http://localhost:8000",
  
  VERSION: "1.0.0-dev",
  ENVIRONMENT: IS_PRODUCTION ? "production" : "development",
};
