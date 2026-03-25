'use client';

import { useState, useEffect } from 'react';
import Button from '@leafygreen-ui/button';
import Badge from '@leafygreen-ui/badge';
import Icon from '@leafygreen-ui/icon';
import { H2, Body, Subtitle, InlineCode } from '@leafygreen-ui/typography';
import { palette } from '@leafygreen-ui/palette';
import { getImageUrl } from '../../lib/api/client';

/**
 * EventDetailModal component for displaying full event details.
 * Custom modal implementation (React 19 compatible).
 */
export default function EventDetailModal({ event, open, onClose, searchMeta = {} }) {
  const [expandedSection, setExpandedSection] = useState(false);

  // Handle escape key
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && open) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  if (!open || !event) return null;

  const imageUrl = getImageUrl(event.event_id);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose} aria-label="Close modal">
          ✕
        </button>
        
        <div className="modal-content">
          {/* Image section */}
          <div className="image-section">
            <img
              src={imageUrl}
              alt={event.text_description}
              className="event-image"
            />
          </div>

          {/* Details section */}
          <div className="details-section">
            <H2>{event.event_id}</H2>
            
            <Body className="description">{event.text_description}</Body>

            {/* Metadata badges */}
            <div className="metadata-badges">
              {event.weather && (
                <Badge variant="blue">
                  {getWeatherIcon(event.weather)} {event.weather}
                </Badge>
              )}
              {event.time_of_day && (
                <Badge variant="purple">
                  {getTimeIcon(event.time_of_day)} {event.time_of_day}
                </Badge>
              )}
              {event.season && (
                <Badge variant="yellow">
                  🍂 {event.season}
                </Badge>
              )}
              {event.rarity_score > 0.7 && (
                <Badge variant="red">
                  ⚠️ Rare Event ({(event.rarity_score * 100).toFixed(0)}%)
                </Badge>
              )}
            </div>

            {/* Expandable MongoDB Capabilities Section */}
            <div className="expandable-section">
              <button 
                className="expand-header"
                onClick={() => setExpandedSection(!expandedSection)}
              >
                <span className="expand-title">
                  <Icon glyph="Database" fill={palette.green.dark1} />
                  MongoDB Search Details
                </span>
                <span className="expand-icon">{expandedSection ? '▼' : '▶'}</span>
              </button>
              
              {expandedSection && (
                <div className="capabilities-content">
                  {/* Search Scores */}
                  {event.scores && (
                    <div className="score-section">
                      <Subtitle>Search Relevance</Subtitle>
                      <div className="score-grid">
                        {event.scores.reranker_score > 0 ? (
                          <ScoreBar 
                            label="Relevance Score" 
                            score={event.scores.reranker_score}
                            color={palette.green.base}
                            highlight
                          />
                        ) : (
                          <div className="ranking-badge">
                            <Badge variant="green">Ranked by $rankFusion</Badge>
                            <Body size="small" style={{ color: palette.gray.dark1, marginTop: '8px' }}>
                              Combined $vectorSearch + $search using Reciprocal Rank Fusion
                            </Body>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Quantization Details */}
                  <div className="quantization-section">
                    <Subtitle>Vector Quantization</Subtitle>
                    <div className="quantization-stats">
                      <div className="stat">
                        <Body weight="medium">Dimensions</Body>
                        <InlineCode>{event.embedding_dimensions || 1024}</InlineCode>
                      </div>
                      <div className="stat">
                        <Body weight="medium">Original Size</Body>
                        <InlineCode>{event.original_bytes || 4096} bytes</InlineCode>
                      </div>
                      <div className="stat">
                        <Body weight="medium">Quantized Size</Body>
                        <InlineCode>{event.quantized_bytes || 1024} bytes</InlineCode>
                      </div>
                      <div className="stat highlight">
                        <Body weight="medium">Savings</Body>
                        <Badge variant="green">75% vector payload reduction</Badge>
                      </div>
                    </div>
                  </div>

                  {/* MongoDB Features Used */}
                  <div className="features-section">
                    <Subtitle>MongoDB Features Demonstrated</Subtitle>
                    <div className="feature-list">
                      <FeatureItem 
                        icon="Relationship" 
                        feature="$rankFusion" 
                        description="Combines $vectorSearch + $search with Reciprocal Rank Fusion"
                      />
                      <FeatureItem 
                        icon="Database" 
                        feature="$vectorSearch" 
                        description="Cosine similarity on quantized embeddings (int8)"
                      />
                      <FeatureItem 
                        icon="MagnifyingGlass" 
                        feature="$search (Atlas Search)" 
                        description="Full-text search with fuzzy matching"
                      />
                      <FeatureItem 
                        icon="Filter" 
                        feature="Pre-filtering" 
                        description="Metadata filters applied inside $vectorSearch"
                      />
                      <FeatureItem 
                        icon="Sparkle" 
                        feature="Voyage AI Reranking" 
                        description="Re-score results for relevance"
                      />
                    </div>
                  </div>

                  {/* Executed Queries Section */}
                  {searchMeta?.executed_queries && Object.keys(searchMeta.executed_queries).length > 0 && (
                    <div className="queries-section">
                      <Subtitle>Executed Queries</Subtitle>
                      <Body size="small" style={{ color: palette.gray.dark1, marginBottom: '8px' }}>
                        Aggregation pipelines executed for this search:
                      </Body>
                      <pre className="query-code">
                        {JSON.stringify(searchMeta.executed_queries, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="modal-actions">
            <Button variant="default" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.6);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          padding: 20px;
        }
        .modal-container {
          background: ${palette.white};
          border-radius: 12px;
          max-width: 800px;
          width: 100%;
          max-height: 90vh;
          overflow-y: auto;
          position: relative;
          box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }
        .modal-close {
          position: absolute;
          top: 12px;
          right: 12px;
          width: 32px;
          height: 32px;
          border: none;
          background: ${palette.gray.light2};
          border-radius: 50%;
          cursor: pointer;
          font-size: 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 10;
          transition: background 0.2s;
        }
        .modal-close:hover {
          background: ${palette.gray.light1};
        }
        .modal-content {
          padding: 24px;
          display: flex;
          flex-direction: column;
          gap: 20px;
        }
        .image-section {
          width: 100%;
          max-height: 400px;
          overflow: hidden;
          border-radius: 8px;
          background: ${palette.black};
        }
        .event-image {
          width: 100%;
          height: auto;
          max-height: 400px;
          object-fit: contain;
        }
        .details-section {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .description {
          color: ${palette.gray.dark2};
          line-height: 1.6;
        }
        .metadata-badges {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
        }
        
        /* Expandable Section */
        .expandable-section {
          border: 1px solid ${palette.gray.light2};
          border-radius: 8px;
          overflow: hidden;
        }
        .expand-header {
          width: 100%;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: ${palette.gray.light3};
          border: none;
          cursor: pointer;
          font-size: 14px;
          font-weight: 500;
        }
        .expand-header:hover {
          background: ${palette.gray.light2};
        }
        .expand-title {
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .expand-icon {
          color: ${palette.gray.dark1};
          font-size: 12px;
        }
        
        .capabilities-content {
          display: flex;
          flex-direction: column;
          gap: 20px;
          padding: 16px;
          border-top: 1px solid ${palette.gray.light2};
        }
        .score-section, .quantization-section, .features-section {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .score-grid {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .ranking-badge {
          padding: 12px;
          background: ${palette.green.light3};
          border-radius: 8px;
        }
        .quantization-stats {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 12px;
        }
        .stat {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .stat.highlight {
          background: ${palette.green.light3};
          padding: 8px;
          border-radius: 4px;
        }
        .feature-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .queries-section {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid ${palette.gray.light2};
        }
        .query-code {
          background: ${palette.gray.dark3};
          color: ${palette.green.light2};
          padding: 12px;
          border-radius: 4px;
          font-size: 11px;
          overflow-x: auto;
          max-height: 300px;
          overflow-y: auto;
          font-family: 'Monaco', 'Menlo', monospace;
        }
        .modal-actions {
          display: flex;
          justify-content: flex-end;
          padding-top: 16px;
          border-top: 1px solid ${palette.gray.light2};
        }
      `}</style>
    </div>
  );
}

/**
 * Score bar visualization component with explanation.
 */
function ScoreBar({ label, score, color, highlight = false }) {
  // Reranker scores are 0-1, display as percentage
  const percentage = Math.round((score || 0) * 100);
  
  const explanations = {
    'Relevance Score': `${percentage}% match - scored by Voyage AI rerank-2 cross-encoder.`
  };
  
  return (
    <div className={`score-bar ${highlight ? 'highlight' : ''}`}>
      <div className="score-label">
        <Body size="small">{label}</Body>
        <Body size="small" weight="medium">{percentage}%</Body>
      </div>
      <div className="bar-bg">
        <div 
          className="bar-fill" 
          style={{ width: `${percentage}%`, backgroundColor: color }} 
        />
      </div>
      <Body size="small" className="score-hint">{explanations[label] || ''}</Body>
      <style jsx>{`
        .score-bar {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .score-bar.highlight {
          background: ${palette.yellow.light3};
          padding: 8px;
          border-radius: 4px;
          margin-top: 8px;
        }
        .score-label {
          display: flex;
          justify-content: space-between;
        }
        .bar-bg {
          height: 8px;
          background: ${palette.gray.light2};
          border-radius: 4px;
          overflow: hidden;
        }
        .bar-fill {
          height: 100%;
          border-radius: 4px;
          transition: width 0.3s ease;
        }
        .score-hint {
          color: ${palette.gray.dark1};
          font-style: italic;
          font-size: 11px;
        }
      `}</style>
    </div>
  );
}

/**
 * Feature item component.
 */
function FeatureItem({ icon, feature, description }) {
  return (
    <div className="feature-item">
      <Icon glyph={icon} fill={palette.green.dark1} />
      <div className="feature-text">
        <Body weight="medium">{feature}</Body>
        <Body size="small" style={{ color: palette.gray.dark1 }}>{description}</Body>
      </div>
      <style jsx>{`
        .feature-item {
          display: flex;
          gap: 12px;
          align-items: flex-start;
          padding: 8px;
          background: ${palette.gray.light3};
          border-radius: 4px;
        }
        .feature-text {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
      `}</style>
    </div>
  );
}

function getWeatherIcon(weather) {
  switch (weather) {
    case 'foggy': return '🌫️';
    case 'overcast': return '☁️';
    case 'rainy': return '🌧️';
    case 'cloudy': return '☁️';
    case 'clear': return '☀️';
    default: return '🌤️';
  }
}

function getTimeIcon(time) {
  switch (time) {
    case 'night': return '🌙';
    case 'dawn': return '🌅';
    case 'dusk': return '🌆';
    case 'day': return '☀️';
    default: return '🕐';
  }
}
