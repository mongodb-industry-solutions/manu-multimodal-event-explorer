'use client';

import { useState, useEffect } from 'react';
import Card from '@leafygreen-ui/card';
import Badge from '@leafygreen-ui/badge';
import Icon from '@leafygreen-ui/icon';
import { H3, Body, Subtitle, InlineCode } from '@leafygreen-ui/typography';
import { palette } from '@leafygreen-ui/palette';

/**
 * SearchPipeline component for visualizing the $rankFusion hybrid search pipeline.
 * Shows: Pre-filter → $rankFusion (Vector + Text) → Reranker
 * 
 * @param {Object} props
 * @param {Object} props.searchMeta - Search response metadata
 */
export default function SearchPipeline({ searchMeta = {} }) {
  if (!searchMeta?.pipeline_steps || searchMeta.pipeline_steps.length === 0) {
    return null;
  }

  const { timing, pipeline_steps, filters_applied } = searchMeta;

  // Format time to single decimal
  const formatTime = (ms) => {
    if (ms === undefined || ms === null) return '0';
    return Number(ms).toFixed(1);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return palette.green.base;
      case 'running': return palette.blue.base;
      case 'failed': return palette.red.base;
      case 'skipped': return palette.gray.base;
      default: return palette.gray.light1;
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return '✓';
      case 'running': return '⟳';
      case 'failed': return '✗';
      case 'skipped': return '−';
      default: return '○';
    }
  };

  const getBadgeVariant = (status) => {
    switch (status) {
      case 'completed': return 'green';
      case 'running': return 'blue';
      case 'failed': return 'red';
      case 'skipped': return 'lightgray';
      default: return 'lightgray';
    }
  };

  return (
    <Card className="pipeline-card">
      <div className="pipeline-header">
        <H3>Search Pipeline</H3>
        {timing && (
          <Badge variant="darkgray">
            {formatTime(timing.total_ms)}ms
          </Badge>
        )}
      </div>

      {/* Pre-filters summary */}
      {filters_applied && Object.keys(filters_applied).length > 0 && (
        <div className="prefilters-section">
          <Body size="small" className="section-label">
            <strong>Lexical Pre-filters Applied:</strong>
          </Body>
          <div className="filter-badges">
            {Object.entries(filters_applied).map(([key, value]) => (
              <Badge key={key} variant="blue">
                {key}: {value}
              </Badge>
            ))}
          </div>
          <Body size="small" className="filter-note">
            Pre-filtering narrows candidates before vector search for faster queries.
          </Body>
        </div>
      )}

      {/* Pipeline steps visualization */}
      <div className="pipeline-steps">
        {pipeline_steps.map((step, index) => (
          <div key={step.name} className="pipeline-step">
            <div className="step-connector">
              {index > 0 && <div className="connector-line" />}
              <div 
                className="step-indicator"
                style={{ backgroundColor: getStatusColor(step.status) }}
              >
                {getStatusIcon(step.status)}
              </div>
              {index < pipeline_steps.length - 1 && <div className="connector-line" />}
            </div>
            
            <div className="step-content">
              <div className="step-header">
                <Subtitle className="step-name">{step.name}</Subtitle>
                <Badge variant={getBadgeVariant(step.status)}>
                  {step.status}
                </Badge>
                {step.time_ms > 0 && (
                  <span className="step-time">{formatTime(step.time_ms)}ms</span>
                )}
              </div>
              
              <div className="step-details">
                {step.result_count > 0 && (
                  <span className="result-count">
                    {step.result_count} results
                  </span>
                )}
                {step.details && (
                  <Body size="small" className="step-description">
                    {step.details}
                  </Body>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Timing breakdown */}
      {timing && (
        <div className="timing-breakdown">
          <Body size="small" className="section-label">
            <strong>Timing Breakdown:</strong>
          </Body>
          <div className="timing-bars">
            {timing.embedding_ms > 0 && (
              <div className="timing-item">
                <span className="timing-label">Query Embedding</span>
                <div className="timing-bar-wrapper">
                  <div 
                    className="timing-bar embedding"
                    style={{ width: `${(timing.embedding_ms / timing.total_ms) * 100}%` }}
                  />
                </div>
                <span className="timing-value">{formatTime(timing.embedding_ms)}ms</span>
              </div>
            )}
            {timing.vector_search_ms > 0 && (
              <div className="timing-item">
                <span className="timing-label">$rankFusion</span>
                <div className="timing-bar-wrapper">
                  <div 
                    className="timing-bar vector"
                    style={{ width: `${(timing.vector_search_ms / timing.total_ms) * 100}%` }}
                  />
                </div>
                <span className="timing-value">{formatTime(timing.vector_search_ms)}ms</span>
              </div>
            )}
            {timing.reranker_ms > 0 && (
              <div className="timing-item">
                <span className="timing-label">Reranker</span>
                <div className="timing-bar-wrapper">
                  <div 
                    className="timing-bar reranker"
                    style={{ width: `${(timing.reranker_ms / timing.total_ms) * 100}%` }}
                  />
                </div>
                <span className="timing-value">{formatTime(timing.reranker_ms)}ms</span>
              </div>
            )}
          </div>
        </div>
      )}

      <style jsx>{`
        :global(.pipeline-card) {
          margin-bottom: 16px;
          background: linear-gradient(135deg, ${palette.blue.light3} 0%, ${palette.white} 100%);
          border: 1px solid ${palette.blue.light2};
        }
        .pipeline-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid ${palette.blue.light2};
        }
        .prefilters-section {
          background: ${palette.blue.light3};
          border-radius: 8px;
          padding: 12px;
          margin-bottom: 16px;
        }
        .section-label {
          color: ${palette.gray.dark2};
          margin-bottom: 8px;
        }
        .filter-badges {
          display: flex;
          gap: 8px;
          flex-wrap: wrap;
          margin-bottom: 8px;
        }
        .filter-note {
          color: ${palette.gray.dark1};
          font-style: italic;
        }
        .pipeline-steps {
          display: flex;
          flex-direction: column;
          gap: 4px;
          margin-bottom: 16px;
        }
        .pipeline-step {
          display: flex;
          gap: 12px;
        }
        .step-connector {
          display: flex;
          flex-direction: column;
          align-items: center;
          width: 24px;
        }
        .connector-line {
          width: 2px;
          flex: 1;
          background: ${palette.gray.light1};
          min-height: 8px;
        }
        .step-indicator {
          width: 24px;
          height: 24px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          color: white;
          font-size: 12px;
          font-weight: bold;
          flex-shrink: 0;
        }
        .step-content {
          flex: 1;
          padding-bottom: 12px;
        }
        .step-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 4px;
        }
        :global(.step-name) {
          margin: 0;
        }
        .step-time {
          color: ${palette.gray.dark1};
          font-size: 12px;
          margin-left: auto;
        }
        .step-details {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .result-count {
          color: ${palette.green.dark1};
          font-size: 12px;
          font-weight: 500;
        }
        :global(.step-description) {
          color: ${palette.gray.dark1};
        }
        .timing-breakdown {
          background: ${palette.white};
          border-radius: 8px;
          padding: 12px;
          border: 1px solid ${palette.gray.light1};
        }
        .timing-bars {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .timing-item {
          display: grid;
          grid-template-columns: 100px 1fr 60px;
          align-items: center;
          gap: 8px;
        }
        .timing-label {
          font-size: 12px;
          color: ${palette.gray.dark2};
        }
        .timing-bar-wrapper {
          height: 12px;
          background: ${palette.gray.light2};
          border-radius: 6px;
          overflow: hidden;
        }
        .timing-bar {
          height: 100%;
          border-radius: 6px;
          transition: width 0.3s ease;
        }
        .timing-bar.embedding {
          background: ${palette.purple.base};
        }
        .timing-bar.vector {
          background: ${palette.green.base};
        }
        .timing-bar.text {
          background: ${palette.blue.base};
        }
        .timing-bar.reranker {
          background: ${palette.yellow.dark2};
        }
        .timing-value {
          font-size: 12px;
          color: ${palette.gray.dark1};
          text-align: right;
        }
      `}</style>
    </Card>
  );
}
