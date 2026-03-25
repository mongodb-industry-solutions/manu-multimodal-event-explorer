'use client';

import { useState } from 'react';
import Card from '@leafygreen-ui/card';
import Badge from '@leafygreen-ui/badge';
import { Body, Subtitle } from '@leafygreen-ui/typography';
import { palette } from '@leafygreen-ui/palette';
import { getImageUrl } from '../../lib/api/client';

/**
 * ResultsGrid component for displaying search results.
 * 
 * @param {Object} props
 * @param {Array} props.results - Search results to display
 * @param {Function} props.onEventClick - Callback when an event is clicked
 * @param {boolean} props.isLoading - Whether results are loading
 * @param {Object} props.searchMeta - Search metadata (query time, etc.)
 */
export default function ResultsGrid({
  results = [],
  onEventClick,
  isLoading = false,
  searchMeta = {},
}) {
  if (isLoading) {
    return (
      <div className="results-grid">
        {[...Array(8)].map((_, i) => (
          <div key={i} className="skeleton-card">
            <div className="skeleton-image" />
            <div className="skeleton-text" />
            <div className="skeleton-text short" />
          </div>
        ))}
        <style jsx>{`
          .results-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            padding: 16px 0;
          }
          .skeleton-card {
            background: ${palette.white};
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
          }
          .skeleton-image {
            width: 100%;
            height: 180px;
            background: linear-gradient(90deg, ${palette.gray.light3} 25%, ${palette.gray.light2} 50%, ${palette.gray.light3} 75%);
            background-size: 200% 100%;
            animation: shimmer 1.5s infinite;
            border-radius: 4px;
          }
          .skeleton-text {
            height: 16px;
            margin-top: 12px;
            background: ${palette.gray.light3};
            border-radius: 4px;
          }
          .skeleton-text.short {
            width: 60%;
          }
          @keyframes shimmer {
            0% { background-position: 200% 0; }
            100% { background-position: -200% 0; }
          }
        `}</style>
      </div>
    );
  }

  if (!results.length) {
    return (
      <div className="no-results">
        <Subtitle>No results found</Subtitle>
        <Body>Try adjusting your search query or filters</Body>
        <style jsx>{`
          .no-results {
            text-align: center;
            padding: 48px;
            color: ${palette.gray.dark1};
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="results-container">
      {/* Results header */}
      {searchMeta.query && (
        <div className="results-header">
          <div className="results-summary">
            Found <strong>{searchMeta.total_count || results.length}</strong> results 
            {searchMeta.query_time_ms && (
              <span className="query-time"> in {searchMeta.query_time_ms.toFixed(1)}ms</span>
            )}
            {searchMeta.vector_index_type === 'quantized_scalar' && (
              <Badge variant="green" className="quantized-badge">
                 Quantized
              </Badge>
            )}
          </div>
          {searchMeta.filters_applied && Object.keys(searchMeta.filters_applied).length > 0 && (
            <div className="active-filters">
              {Object.entries(searchMeta.filters_applied).map(([key, value]) => (
                <Badge key={key} variant="lightgray">
                  {key}: {value}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Results grid */}
      <div className="results-grid">
        {results.map((result) => (
          <ResultCard
            key={result.event_id}
            result={result}
            onClick={() => onEventClick?.(result)}
          />
        ))}
      </div>

      <style jsx>{`
        .results-container {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .results-header {
          display: flex;
          align-items: center;
          gap: 12px;
          flex-wrap: wrap;
          padding: 12px 16px;
          background: ${palette.gray.light3};
          border-radius: 8px;
        }
        .query-time {
          color: ${palette.gray.dark1};
        }
        .active-filters {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        .results-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: 16px;
        }
        :global(.quantized-badge) {
          margin-left: 8px;
        }
      `}</style>
    </div>
  );
}

/**
 * Individual result card component.
 */
function ResultCard({ result, onClick }) {
  const [imageError, setImageError] = useState(false);
  
  const imageUrl = getImageUrl(result.event_id);
  
  const getWeatherIcon = (weather) => {
    switch (weather) {
      case 'foggy': return '🌫️';
      case 'overcast': return '☁️';
      case 'rainy': return '🌧️';
      case 'cloudy': return '☁️';
      case 'clear': return '☀️';
      default: return '🌤️';
    }
  };

  const getTimeIcon = (time) => {
    switch (time) {
      case 'night': return '🌙';
      case 'dawn': return '🌅';
      case 'dusk': return '🌆';
      case 'day': return '☀️';
      default: return '🕐';
    }
  };

  return (
    <Card 
      className="result-card" 
      onClick={onClick}
      style={{ cursor: 'pointer' }}
    >
      <div className="card-image">
        {!imageError ? (
          <img
            src={imageUrl}
            alt={result.text_description}
            onError={() => setImageError(true)}
            loading="lazy"
          />
        ) : (
          <div className="image-placeholder">
            <span>🖼️</span>
          </div>
        )}
        
      </div>
      
      <div className="card-content">
        <div className="metadata-row">
          <span title="Weather">{getWeatherIcon(result.weather)} {result.weather || 'unknown'}</span>
          <span title="Time">{getTimeIcon(result.time_of_day)} {result.time_of_day || 'unknown'}</span>
          {result.season && (
            <span title="Season">🍂 {result.season}</span>
          )}
        </div>
        
        <Body className="description">
          {result.text_description}
        </Body>
        
        {result.rarity_score > 0.7 && (
          <Badge variant="yellow">Rare Event</Badge>
        )}
      </div>

      <style jsx>{`
        .result-card {
          overflow: hidden;
          transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .result-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        .card-image {
          position: relative;
          width: 100%;
          height: 180px;
          overflow: hidden;
          background: ${palette.gray.light3};
        }
        .card-image img {
          width: 100%;
          height: 100%;
          object-fit: cover;
        }
        .image-placeholder {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 48px;
          color: ${palette.gray.base};
        }
        .score-badge {
          position: absolute;
          top: 8px;
          right: 8px;
          background: ${palette.green.dark1};
          color: white;
          padding: 4px 8px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 600;
        }
        .card-content {
          padding: 12px;
        }
        .metadata-row {
          display: flex;
          gap: 12px;
          margin-bottom: 8px;
          font-size: 13px;
          color: ${palette.gray.dark1};
        }
        .description {
          font-size: 14px;
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </Card>
  );
}
