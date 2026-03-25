'use client';

import { useState, useEffect } from 'react';
import Card from '@leafygreen-ui/card';
import Badge from '@leafygreen-ui/badge';
import { H3, Body, Subtitle } from '@leafygreen-ui/typography';
import { palette } from '@leafygreen-ui/palette';
import { getStats } from '../../lib/api/client';

/**
 * QuantizationStats - Technically accurate explanation of Atlas Vector Search quantization.
 */
export default function QuantizationStats({ domain = 'adas', searchMeta = {} }) {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchStats() {
      try {
        const data = await getStats(domain);
        setStats(data);
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, [domain]);

  if (loading) {
    return (
      <Card className="stats-panel loading">
        <div className="loading-placeholder">Loading stats...</div>
        <style jsx>{`
          .loading-placeholder {
            padding: 24px;
            text-align: center;
            color: ${palette.gray.dark1};
          }
        `}</style>
      </Card>
    );
  }

  const collection = stats?.collection || {};
  const docCount = collection.document_count || 0;
  const embeddingStorage = collection.embedding_storage || {};
  const searchIndexes = collection.search_indexes || [];
  const queryTimeMs = searchMeta?.query_time_ms || null;

  const dimensions = embeddingStorage.dimensions || 1024;
  const vectorBytesInDocs = docCount * dimensions * 4; // float32 in documents

  const formatBytes = (bytes) => {
    if (!bytes || bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const vectorIndex = searchIndexes.find(idx => idx.type === 'vectorSearch');
  const isQuantized = vectorIndex && vectorIndex.status === 'READY';

  return (
    <Card className="stats-panel">
      <div className="stats-header">
        <H3>Scalar Quantization</H3>
        <Badge variant={isQuantized ? "green" : "yellow"}>
          {isQuantized ? "Enabled" : "Pending"}
        </Badge>
      </div>

      <div className="stats-content">
        {/* What Quantization Does */}
        <div className="explanation-section">
          <div className="section-title">How It Works</div>
          
          <div className="storage-diagram">
            <div className="storage-layer">
              <div className="layer-content">
                <div className="layer-title">MongoDB Documents</div>
                <div className="layer-detail">
                  Embeddings stored as <strong>float32</strong><br/>
                  {dimensions} dims × 4 bytes = <strong>4,096 B</strong> per vector
                </div>
                <div className="layer-note">Unchanged by quantization</div>
              </div>
            </div>
            
            <div className="arrow-down">↓</div>
            
            <div className="storage-layer index-layer">
              <div className="layer-content">
                <div className="layer-title">Atlas Vector Search Index</div>
                <div className="layer-detail">
                  Vector payload compressed to <strong>int8</strong><br/>
                  {dimensions} dims × 1 byte = <strong>1,024 B</strong> per vector
                </div>
                <div className="layer-savings">75% smaller vector payload</div>
              </div>
            </div>
          </div>
        </div>

        {/* Important Clarification 
        <div className="clarification-box">
          <div className="clarification-title">⚠️ Important Distinction</div>
          <Body size="small">
            The Atlas Vector Search index is <strong>not</strong> just a copy of your embeddings. 
            It includes an HNSW graph structure and metadata for approximate nearest neighbor search.
          </Body>
          <Body size="small" style={{ marginTop: '8px' }}>
            <strong>Quantization reduces the vector payload portion</strong> of the index by 75%, 
            but total index size also includes ANN graph overhead.
          </Body>
        </div>*/}

        {/* Benefits */}
        <div className="benefits-section">
          <div className="section-title">Benefits</div>
          <div className="benefit">
            <span>Lower RAM pressure for vector search operations</span>
          </div>
          <div className="benefit">
            <span>Better scalability.. index more vectors per cluster</span>
          </div>
          <div className="benefit">
            <span>Faster distance computations with smaller vectors</span>
          </div>
          <div className="benefit">
            <span>Recall preserved with minimal accuracy loss</span>
          </div>
        </div>

        {/* Current Demo Stats */}
        <div className="current-stats">
          <div className="section-title">This Demo</div>
          <div className="stat-row">
            <span>Documents indexed:</span>
            <strong>{docCount.toLocaleString()}</strong>
          </div>
          <div className="stat-row">
            <span>Vector dimensions:</span>
            <strong>{dimensions}</strong>
          </div>
          <div className="stat-row">
            <span>Raw embeddings in docs:</span>
            <strong>{formatBytes(vectorBytesInDocs)}</strong>
          </div>
          {queryTimeMs && (
            <div className="stat-row highlight">
              <span>Last query time:</span>
              <strong>{queryTimeMs.toFixed(1)}ms</strong>
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        :global(.stats-panel) {
          background: ${palette.white};
          border: 1px solid ${palette.gray.light2};
        }
        .stats-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 16px;
          padding-bottom: 12px;
          border-bottom: 1px solid ${palette.gray.light2};
        }
        .stats-content {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .section-title {
          font-weight: 600;
          font-size: 13px;
          color: ${palette.gray.dark2};
          margin-bottom: 12px;
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        
        /* Storage Diagram */
        .explanation-section {
          padding: 16px;
          background: ${palette.gray.light3};
          border-radius: 8px;
        }
        .storage-diagram {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .storage-layer {
          display: flex;
          gap: 12px;
          padding: 12px;
          background: ${palette.white};
          border-radius: 6px;
          border: 1px solid ${palette.gray.light2};
        }
        .storage-layer.index-layer {
          background: ${palette.green.light3};
          border-color: ${palette.green.light2};
        }
        .layer-icon {
          font-size: 24px;
          flex-shrink: 0;
        }
        .layer-content {
          flex: 1;
        }
        .layer-title {
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 4px;
        }
        .layer-detail {
          font-size: 12px;
          color: ${palette.gray.dark1};
          line-height: 1.4;
        }
        .layer-note {
          font-size: 11px;
          color: ${palette.gray.base};
          font-style: italic;
          margin-top: 4px;
        }
        .layer-savings {
          font-size: 12px;
          color: ${palette.green.dark2};
          font-weight: 600;
          margin-top: 4px;
        }
        .arrow-down {
          text-align: center;
          font-size: 20px;
          color: ${palette.gray.base};
        }
        
        /* Clarification Box */
        .clarification-box {
          padding: 12px;
          background: ${palette.yellow.light3};
          border-radius: 8px;
          border-left: 4px solid ${palette.yellow.dark2};
        }
        .clarification-title {
          font-weight: 600;
          font-size: 13px;
          margin-bottom: 8px;
          color: ${palette.yellow.dark2};
        }
        
        /* Benefits */
        .benefits-section {
          padding: 12px;
          background: ${palette.gray.light3};
          border-radius: 8px;
        }
        .benefit {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: ${palette.gray.dark2};
          padding: 4px 0;
        }
        .benefit-icon {
          font-size: 14px;
          flex-shrink: 0;
        }
        
        /* Current Stats */
        .current-stats {
          padding: 12px;
          background: ${palette.gray.light3};
          border-radius: 8px;
        }
        .stat-row {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          padding: 4px 0;
        }
        .stat-row.highlight {
          color: ${palette.green.dark2};
          font-weight: 500;
          margin-top: 4px;
          padding-top: 8px;
          border-top: 1px solid ${palette.gray.light2};
        }
      `}</style>
    </Card>
  );
}
