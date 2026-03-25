/**
 * API client for the Multimodal Event Explorer backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Make a fetch request with error handling.
 */
async function fetchAPI(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API Error (${endpoint}):`, error);
    throw error;
  }
}

/**
 * Search for events using hybrid search.
 * 
 * @param {Object} params - Search parameters
 * @param {string} params.query - Natural language search query
 * @param {string} [params.domain='adas'] - Domain to search
 * @param {string} [params.season] - Filter by season
 * @param {string} [params.timeOfDay] - Filter by time of day
 * @param {string} [params.weather] - Filter by weather
 * @param {number} [params.limit=20] - Maximum results
 * @param {boolean} [params.useVectorSearch=true] - Enable vector search
 * @param {boolean} [params.useTextSearch=true] - Enable text search
 * @param {boolean} [params.useReranker=true] - Enable Voyage AI reranker
 * @returns {Promise<Object>} Search response with results and metadata
 */
export async function search({
  query,
  domain = 'adas',
  season,
  timeOfDay,
  weather,
  limit = 20,
  useVectorSearch = true,
  useTextSearch = true,
  useReranker = true,
}) {
  const params = new URLSearchParams({
    query,
    domain,
    limit: limit.toString(),
    use_vector_search: useVectorSearch.toString(),
    use_text_search: useTextSearch.toString(),
    use_reranker: useReranker.toString(),
  });
  
  if (season) params.append('season', season);
  if (timeOfDay) params.append('time_of_day', timeOfDay);
  if (weather) params.append('weather', weather);
  
  return fetchAPI(`/api/search?${params.toString()}`);
}

/**
 * Get a single event by ID.
 * 
 * @param {string} eventId - Event identifier
 * @param {string} [domain='adas'] - Domain to search in
 * @returns {Promise<Object>} Event details
 */
export async function getEvent(eventId, domain = 'adas') {
  return fetchAPI(`/api/events/${eventId}?domain=${domain}`);
}

/**
 * List events with optional filtering.
 * 
 * @param {Object} params - Filter parameters
 * @returns {Promise<Object>} Events list with pagination
 */
export async function listEvents({
  domain = 'adas',
  season,
  timeOfDay,
  weather,
  limit = 20,
  offset = 0,
} = {}) {
  const params = new URLSearchParams({
    domain,
    limit: limit.toString(),
    offset: offset.toString(),
  });
  
  if (season) params.append('season', season);
  if (timeOfDay) params.append('time_of_day', timeOfDay);
  if (weather) params.append('weather', weather);
  
  return fetchAPI(`/api/events?${params.toString()}`);
}

/**
 * Get available filter options for a domain.
 * 
 * @param {string} [domain='adas'] - Domain to get filters for
 * @returns {Promise<Object>} Filter options
 */
export async function getFilterOptions(domain = 'adas') {
  return fetchAPI(`/api/events/filters/options?domain=${domain}`);
}

/**
 * Get all available domains.
 * 
 * @returns {Promise<Array>} List of domain configurations
 */
export async function getDomains() {
  return fetchAPI('/api/domains');
}

/**
 * Get only enabled domains.
 * 
 * @returns {Promise<Array>} List of enabled domain configurations
 */
export async function getEnabledDomains() {
  return fetchAPI('/api/domains/enabled');
}

/**
 * Get sample queries for a domain.
 * 
 * @param {string} domainId - Domain identifier
 * @returns {Promise<Array>} List of sample queries
 */
export async function getSampleQueries(domainId) {
  return fetchAPI(`/api/domains/${domainId}/sample-queries`);
}

/**
 * Get statistics for a domain (for quantization showcase).
 * 
 * @param {string} [domain='adas'] - Domain to get stats for
 * @returns {Promise<Object>} Statistics including quantization info
 */
export async function getStats(domain = 'adas') {
  return fetchAPI(`/api/stats?domain=${domain}`);
}

/**
 * Get summary statistics across all domains.
 * 
 * @returns {Promise<Object>} Summary statistics
 */
export async function getStatsSummary() {
  return fetchAPI('/api/stats/summary');
}

/**
 * Get image URL for an event.
 * 
 * @param {string} eventId - Event identifier
 * @returns {string} Image URL
 */
export function getImageUrl(eventId) {
  return `${API_BASE_URL}/api/images/${eventId}`;
}

export default {
  search,
  getEvent,
  listEvents,
  getFilterOptions,
  getDomains,
  getEnabledDomains,
  getSampleQueries,
  getStats,
  getStatsSummary,
  getImageUrl,
};
