'use client';

import { useState, useEffect } from 'react';
import Button from '@leafygreen-ui/button';
import Tooltip from '@leafygreen-ui/tooltip';
import { Body } from '@leafygreen-ui/typography';
import { palette } from '@leafygreen-ui/palette';

/**
 * DomainSwitcher component for switching between domains.
 * 
 * @param {Object} props
 * @param {Array} props.domains - Available domains
 * @param {string} props.activeDomain - Currently active domain ID
 * @param {Function} props.onDomainChange - Callback when domain changes
 */
export default function DomainSwitcher({
  domains = [],
  activeDomain = 'adas',
  onDomainChange,
}) {
  return (
    <div className="domain-switcher">
      <Body size="small" className="label">Domain:</Body>
      <div className="domain-buttons">
        {domains.map((domain) => (
          <Tooltip
            key={domain.id}
            trigger={
              <Button
                variant={activeDomain === domain.id ? 'primary' : 'default'}
                size="small"
                onClick={() => domain.enabled && onDomainChange?.(domain.id)}
                disabled={!domain.enabled}
                className={`domain-button ${!domain.enabled ? 'disabled' : ''}`}
              >
                <span className="domain-icon">{domain.icon}</span>
                {domain.name}
              </Button>
            }
            enabled={!domain.enabled}
          >
            {domain.enabled 
              ? domain.description 
              : `${domain.name} - Coming Soon`
            }
          </Tooltip>
        ))}
      </div>

      <style jsx>{`
        .domain-switcher {
          display: flex;
          align-items: center;
          gap: 12px;
        }
        .label {
          color: ${palette.gray.dark1};
        }
        .domain-buttons {
          display: flex;
          gap: 8px;
        }
        :global(.domain-button) {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        :global(.domain-button.disabled) {
          opacity: 0.5;
        }
        .domain-icon {
          font-size: 16px;
        }
      `}</style>
    </div>
  );
}
