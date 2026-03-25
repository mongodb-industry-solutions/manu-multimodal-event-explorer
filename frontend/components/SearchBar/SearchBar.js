'use client';

import { useState, useCallback, useEffect } from 'react';
import Button from '@leafygreen-ui/button';
import Icon from '@leafygreen-ui/icon';
import { Body } from '@leafygreen-ui/typography';
import { palette } from '@leafygreen-ui/palette';

/**
 * SearchBar component for natural language search with filters.
 *
 * @param {Object} props
 * @param {Function} props.onSearch - Callback when search is triggered
 * @param {Array} props.sampleQueries - Sample queries to show as suggestions
 * @param {Object} props.filterOptions - Available filter values
 * @param {boolean} props.isLoading - Whether a search is in progress
 * @param {Object|null} props.triggerSearch - { query, timestamp } — set from outside to trigger a search
 */
export default function SearchBar({
  onSearch,
  sampleQueries = [],
  filterOptions = {},
  isLoading = false,
  triggerSearch = null,
}) {
  const [query, setQuery] = useState('');
  const [season, setSeason] = useState('');
  const [timeOfDay, setTimeOfDay] = useState('');
  const [weather, setWeather] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  // Respond to an externally-triggered search (e.g. from the AI agent)
  useEffect(() => {
    if (!triggerSearch?.query) return;
    setQuery(triggerSearch.query);
    setSeason('');
    setTimeOfDay('');
    setWeather('');
    onSearch({ query: triggerSearch.query });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerSearch?.timestamp]);

  const handleSearch = useCallback(() => {
    if (!query.trim()) return;
    
    onSearch({
      query: query.trim(),
      season: season || undefined,
      timeOfDay: timeOfDay || undefined,
      weather: weather || undefined,
    });
  }, [query, season, timeOfDay, weather, onSearch]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleSampleClick = (sampleQuery) => {
    setQuery(sampleQuery);
    onSearch({
      query: sampleQuery,
      season: season || undefined,
      timeOfDay: timeOfDay || undefined,
      weather: weather || undefined,
    });
  };

  const clearFilters = () => {
    setSeason('');
    setTimeOfDay('');
    setWeather('');
  };

  const hasActiveFilters = season || timeOfDay || weather;

  return (
    <div className="search-bar">
      {/* Main search input */}
      <div className="search-input-row">
        <div className="search-input-wrapper">
          <label htmlFor="search-input" className="visually-hidden">Search query</label>
          <input
            id="search-input"
            type="text"
            className="search-input"
            placeholder="Search events... e.g., 'night driving conditions'"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
        </div>
        
        <Button
          variant="primary"
          onClick={handleSearch}
          disabled={!query.trim() || isLoading}
          leftGlyph={<Icon glyph="MagnifyingGlass" />}
        >
          {isLoading ? 'Searching...' : 'Search'}
        </Button>
        
        <Button
          variant="default"
          onClick={() => setShowFilters(!showFilters)}
          leftGlyph={<Icon glyph="Filter" />}
          style={{ 
            backgroundColor: hasActiveFilters ? palette.green.light3 : undefined 
          }}
        >
          Filters {hasActiveFilters && '•'}
        </Button>
      </div>

      {/* Filters row */}
      {showFilters && (
        <div className="filters-row">
          <div className="filter-group">
            <label className="filter-label">Season</label>
            <select
              className="filter-select"
              value={season}
              onChange={(e) => setSeason(e.target.value)}
            >
              <option value="">Any season</option>
              {(filterOptions.season || ['spring', 'summer', 'fall', 'winter']).map((s) => s && (
                <option key={s} value={s}>
                  {s.charAt(0).toUpperCase() + s.slice(1)}
                </option>
              ))}
            </select>
          </div>
          
          <div className="filter-group">
            <label className="filter-label">Time of Day</label>
            <select
              className="filter-select"
              value={timeOfDay}
              onChange={(e) => setTimeOfDay(e.target.value)}
            >
              <option value="">Any time</option>
              {(filterOptions.time_of_day || ['dawn', 'day', 'dusk', 'night']).map((t) => t && (
                <option key={t} value={t}>
                  {t.charAt(0).toUpperCase() + t.slice(1)}
                </option>
              ))}
            </select>
          </div>
          
          <div className="filter-group">
            <label className="filter-label">Weather</label>
            <select
              className="filter-select"
              value={weather}
              onChange={(e) => setWeather(e.target.value)}
            >
              <option value="">Any weather</option>
              {(filterOptions.weather || ['clear', 'overcast']).map((w) => w && (
                <option key={w} value={w}>
                  {w.charAt(0).toUpperCase() + w.slice(1)}
                </option>
              ))}
            </select>
          </div>
          
          {hasActiveFilters && (
            <Button variant="default" size="small" onClick={clearFilters}>
              Clear filters
            </Button>
          )}
        </div>
      )}

      {/* Sample queries */}
      {sampleQueries.length > 0 && !query && (
        <div className="sample-queries">
          <Body size="small" style={{ color: palette.gray.dark1, marginBottom: '8px' }}>
            Try these searches:
          </Body>
          <div className="sample-query-chips">
            {sampleQueries.slice(0, 5).map((sample, index) => (
              <button
                key={index}
                className="sample-chip"
                onClick={() => handleSampleClick(sample)}
                disabled={isLoading}
              >
                {sample}
              </button>
            ))}
          </div>
        </div>
      )}

      <style jsx>{`
        .search-bar {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 16px;
          background: ${palette.white};
          border-radius: 8px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
        
        .search-input-row {
          display: flex;
          gap: 8px;
          align-items: flex-end;
        }
        
        .search-input-wrapper {
          flex: 1;
        }
        
        .visually-hidden {
          position: absolute;
          width: 1px;
          height: 1px;
          padding: 0;
          margin: -1px;
          overflow: hidden;
          clip: rect(0, 0, 0, 0);
          white-space: nowrap;
          border: 0;
        }
        
        .search-input {
          width: 100%;
          padding: 10px 12px;
          border: 1px solid ${palette.gray.light2};
          border-radius: 6px;
          font-size: 16px;
          color: ${palette.gray.dark3};
          background: ${palette.white};
          transition: border-color 0.15s, box-shadow 0.15s;
        }
        
        .search-input:focus {
          outline: none;
          border-color: ${palette.green.base};
          box-shadow: 0 0 0 3px ${palette.green.light3};
        }
        
        .search-input:disabled {
          background: ${palette.gray.light3};
          cursor: not-allowed;
        }
        
        .search-input::placeholder {
          color: ${palette.gray.base};
        }
        
        .filters-row {
          display: flex;
          gap: 12px;
          align-items: flex-end;
          flex-wrap: wrap;
          padding: 12px;
          background: ${palette.gray.light3};
          border-radius: 4px;
        }
        
        .filter-group {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        
        .filter-label {
          font-size: 12px;
          font-weight: 500;
          color: ${palette.gray.dark1};
        }
        
        .filter-select {
          padding: 8px 12px;
          border: 1px solid ${palette.gray.light2};
          border-radius: 4px;
          background: ${palette.white};
          font-size: 14px;
          color: ${palette.gray.dark3};
          cursor: pointer;
          min-width: 140px;
        }
        
        .filter-select:focus {
          outline: none;
          border-color: ${palette.green.base};
          box-shadow: 0 0 0 2px ${palette.green.light3};
        }
        
        .sample-queries {
          padding-top: 8px;
          border-top: 1px solid ${palette.gray.light2};
        }
        
        .sample-query-chips {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
        }
        
        .sample-chip {
          padding: 6px 12px;
          background: ${palette.gray.light3};
          border: 1px solid ${palette.gray.light2};
          border-radius: 16px;
          font-size: 13px;
          color: ${palette.gray.dark2};
          cursor: pointer;
          transition: all 0.15s ease;
        }
        
        .sample-chip:hover:not(:disabled) {
          background: ${palette.green.light3};
          border-color: ${palette.green.light2};
          color: ${palette.green.dark2};
        }
        
        .sample-chip:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
