"use client";

import { useState, useEffect, useCallback } from 'react';
import { H1, Body } from '@leafygreen-ui/typography';
import Button from '@leafygreen-ui/button';
import { palette } from '@leafygreen-ui/palette';

import SearchBar from '@/components/SearchBar';
import ResultsGrid from '@/components/ResultsGrid';
import EventDetailModal from '@/components/EventDetailModal';
import DomainSwitcher from '@/components/DomainSwitcher';
import QuantizationStats from '@/components/QuantizationStats';
import SearchPipeline from '@/components/SearchPipeline';
import InfoWizard from '@/components/infoWizard/InfoWizard';
import ChatPanel from '@/components/ChatPanel/ChatPanel';

import { 
  search, 
  getDomains, 
  getSampleQueries, 
  getFilterOptions 
} from '@/lib/api/client';

export default function Home() {
  // State
  const [domains, setDomains] = useState([]);
  const [activeDomain, setActiveDomain] = useState('adas');
  const [sampleQueries, setSampleQueries] = useState([]);
  const [filterOptions, setFilterOptions] = useState({});
  const [searchResults, setSearchResults] = useState([]);
  const [searchMeta, setSearchMeta] = useState({});
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  // Trigger object passed to SearchBar when the AI agent runs a search
  const [agentSearchTrigger, setAgentSearchTrigger] = useState(null);

  // Load initial data
  useEffect(() => {
    async function loadInitialData() {
      try {
        const [domainsData, queries, filters] = await Promise.all([
          getDomains(),
          getSampleQueries(activeDomain),
          getFilterOptions(activeDomain),
        ]);
        setDomains(domainsData);
        setSampleQueries(queries);
        setFilterOptions(filters);
      } catch (err) {
        console.error('Failed to load initial data:', err);
        // Set defaults for demo
        setDomains([
          { id: 'adas', name: 'ADAS / Autonomous Driving', enabled: true },
          { id: 'factory', name: 'Industrial Scenarios', enabled: false },
        ]);
        setSampleQueries([
          'night driving conditions',
          'overcast dusk on rural roads',
          'clear summer daytime driving',
          'autumn dawn driving conditions',
          'spring night rural road',
        ]);
        setFilterOptions({
          season: ['spring', 'summer', 'fall', 'winter'],
          time_of_day: ['dawn', 'day', 'dusk', 'night'],
          weather: ['clear', 'overcast'],
        });
      }
    }
    loadInitialData();
  }, [activeDomain]);

  // Handle search
  const handleSearch = useCallback(async (params) => {
    setIsLoading(true);
    setError(null);
    setHasSearched(true);
    
    try {
      const response = await search({
        ...params,
        domain: activeDomain,
      });
      
      setSearchResults(response.results || []);
      setSearchMeta({
        query: response.query,
        total_count: response.total_count,
        query_time_ms: response.query_time_ms,
        vector_index_type: response.vector_index_type,
        filters_applied: response.filters_applied,
        search_config: response.search_config,
        executed_queries: response.executed_queries,
        timing: response.timing,
        pipeline_steps: response.pipeline_steps,
      });
    } catch (err) {
      console.error('Search failed:', err);
      setError(err.message || 'Search failed. Please try again.');
      setSearchResults([]);
    } finally {
      setIsLoading(false);
    }
  }, [activeDomain]);

  // Handle domain change
  const handleDomainChange = useCallback((domainId) => {
    setActiveDomain(domainId);
    setSearchResults([]);
    setSearchMeta({});
    setHasSearched(false);
  }, []);

  // Handle event click
  const handleEventClick = useCallback((event) => {
    setSelectedEvent(event);
  }, []);

  // Close modal
  const handleCloseModal = useCallback(() => {
    setSelectedEvent(null);
  }, []);

  // Called by ChatPanel when the agent fires a search_events tool call
  const handleAgentSearch = useCallback((params) => {
    // Open the chat panel automatically so the user can see both
    setChatOpen(true);
    // Update the trigger — SearchBar watches this and fires the search
    setAgentSearchTrigger({ query: params.query, timestamp: Date.now() });
  }, []);

  return (
    <main className="app-container">
      {/* Header */}
      <header className="app-header">
        <div className="header-content">
          <div className="title-row">
            <H1>Multimodal Event Explorer</H1>
            <InfoWizard />
          </div>
          <Body className="subtitle">
            MongoDB-powered multimodal search for autonomous driving and industrial scenarios
          </Body>
        </div>
        <div className="header-right">
          <DomainSwitcher
            domains={domains}
            activeDomain={activeDomain}
            onDomainChange={handleDomainChange}
          />
          <Button
            variant={chatOpen ? 'primary' : 'default'}
            size="small"
            onClick={() => setChatOpen(true)}
          >
            MongoDB AI Agent
          </Button>
        </div>
      </header>

      {/* Main content */}
      <div className="main-content">
        {/* Left column - Search and Results */}
        <div className="search-column">
          <SearchBar
            onSearch={handleSearch}
            sampleQueries={sampleQueries}
            filterOptions={filterOptions}
            isLoading={isLoading}
            triggerSearch={agentSearchTrigger}
          />

          {error && (
            <div className="error-message">
              <Body>{error}</Body>
            </div>
          )}

          {hasSearched && (
            <ResultsGrid
              results={searchResults}
              onEventClick={handleEventClick}
              isLoading={isLoading}
              searchMeta={searchMeta}
            />
          )}

          {!hasSearched && !isLoading && (
            <div className="welcome-message">
              <H1>Search Autonomous Driving Events</H1>
              <Body>
                Use natural language to find specific driving scenarios.
                Try searches like "night driving" or "overcast dusk conditions".
                This demo has the following capabilities:
              </Body>
              <div className="capabilities-list">
                <div className="capability">
                  <span>Vector Search with Voyage AI embeddings</span>
                </div>
                <div className="capability">
                  <span>Full-text search on descriptions</span>
                </div>
                <div className="capability">
                  <span>Hybrid retrieval with reranking</span>
                </div>
                <div className="capability">
                  <span>Storage savings with quantization</span>
                </div>
              </div>
                <div className="disclaimer-text">
                  <span> <a href="https://huggingface.co/datasets/jongwonryu/MIST-autonomous-driving-dataset">MIST Autonomous Driving Dataset</a> </span>
                </div>
            </div>
          )}
        </div>

        {/* Right column - Stats Panel */}
        <div className="stats-column">
          {/* Search Pipeline Visualization - shows after search */}
          {hasSearched && searchMeta?.pipeline_steps && (
            <SearchPipeline searchMeta={searchMeta} />
          )}
          
          <QuantizationStats 
            domain={activeDomain} 
            searchMeta={searchMeta}
          />
        </div>
      </div>

      {/* Event Detail Modal */}
      <EventDetailModal
        event={selectedEvent}
        open={!!selectedEvent}
        onClose={handleCloseModal}
        searchMeta={searchMeta}
      />

      <ChatPanel open={chatOpen} onClose={() => setChatOpen(false)} onAgentSearch={handleAgentSearch} />

      <style jsx>{`
        .app-container {
          min-height: 100vh;
          background: ${palette.gray.light3};
          padding: 24px;
        }
        .app-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 24px;
          padding: 20px 24px;
          background: ${palette.white};
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
          position: sticky;
          top: 0;
          z-index: 200;
        }
        .header-right {
          display: flex;
          flex-direction: column;
          align-items: flex-end;
          gap: 12px;
        }

        .header-content {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .title-row {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .subtitle {
          color: ${palette.gray.dark1};
        }
        .main-content {
          display: grid;
          grid-template-columns: 1fr 320px;
          gap: 24px;
        }
        .search-column {
          display: flex;
          flex-direction: column;
          gap: 24px;
        }
        .stats-column {
          position: sticky;
          top: 24px;
          align-self: start;
        }
        .error-message {
          padding: 16px;
          background: ${palette.red.light3};
          border: 1px solid ${palette.red.light2};
          border-radius: 8px;
          color: ${palette.red.dark2};
        }
        .welcome-message {
          display: flex;
          flex-direction: column;
          align-items: center;
          text-align: center;
          padding: 64px 32px;
          background: ${palette.white};
          border-radius: 12px;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
        }
        .welcome-icon {
          font-size: 64px;
          margin-bottom: 16px;
        }
        .welcome-message :global(h1) {
          margin-bottom: 8px;
        }
        .welcome-message :global(p) {
          color: ${palette.gray.dark1};
          max-width: 500px;
          margin-bottom: 24px;
        }
        .disclaimer-text   {
          color: ${palette.blue.light1};
          max-width: 1000px;
          margin-bottom: 24px;
          margin-top: 100px;
          font-size: 12px;
          text-align: right;
        }
        .capabilities-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
          margin-top: 16px;
        }
        .capability {
          display: flex;
          align-items: center;
          gap: 12px;
          padding: 12px 20px;
          background: ${palette.green.light3};
          border-radius: 8px;
          font-size: 14px;
          color: ${palette.green.dark2};
        }
        .cap-icon {
          font-size: 20px;
        }
        
        @media (max-width: 1024px) {
          .main-content {
            grid-template-columns: 1fr;
          }
          .stats-column {
            position: static;
            order: -1;
          }
        }

      `}</style>
    </main>
  );
}
