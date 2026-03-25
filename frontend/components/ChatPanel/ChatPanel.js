import { useState, useRef, useEffect } from 'react';
import { Body, H3, Label } from '@leafygreen-ui/typography';
import { palette } from '@leafygreen-ui/palette';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const SUGGESTED_QUESTIONS = [
  { text: 'What are the rarest events in this dataset?' },
  { text: 'Show me events that happen at night during overcast conditions' },
  { text: 'Compare foggy vs clear weather driving scenarios', hitl: true },
  { text: 'What is the distribution of weather conditions?' },
  { text: 'Find the most unusual driving conditions' },
];

// ---------------------------------------------------------------------------
// ApprovalCard — shown when the agent wants to run a tool that needs approval
// ---------------------------------------------------------------------------

function ApprovalCard({ approval, onDecide }) {
  const [decided, setDecided] = useState(false);
  const [choice, setChoice] = useState(null);

  const handleClick = (approved) => {
    setDecided(true);
    setChoice(approved);
    onDecide(approved);
  };

  return (
    <div className="approval-card">
      <div className="approval-header">
        <span className="approval-icon">🔐</span>
        <span className="approval-title">Tool approval required</span>
      </div>
      <div className="approval-body">
        <p className="approval-desc">
          The agent wants to run <code className="approval-tool">{approval.tool_name}</code>:
        </p>
        <pre className="approval-input">
          {JSON.stringify(approval.tool_input, null, 2)}
        </pre>
        {!decided ? (
          <div className="approval-btns">
            <button className="btn-approve" onClick={() => handleClick(true)}>✓ Approve</button>
            <button className="btn-reject"  onClick={() => handleClick(false)}>✗ Reject</button>
          </div>
        ) : (
          <div className={`approval-decision ${choice ? 'approved' : 'rejected'}`}>
            {choice ? '✓ Approved — running tool…' : '✗ Rejected — tool will be skipped.'}
          </div>
        )}
      </div>
      <style jsx>{`
        .approval-card {
          border: 2px solid ${palette.yellow.base};
          background: #fffdf0;
          border-radius: 10px;
          overflow: hidden;
          font-size: 12px;
          margin: 4px 0;
          max-width: 100%;
        }
        .approval-header {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 7px 10px;
          background: ${palette.yellow.light3};
          border-bottom: 1px solid ${palette.yellow.base};
          font-weight: 700;
          color: ${palette.yellow.dark2};
        }
        .approval-icon { font-size: 14px; }
        .approval-title { font-size: 12px; }
        .approval-body { padding: 8px 10px; }
        .approval-desc { margin: 0 0 6px; color: ${palette.gray.dark2}; }
        .approval-tool {
          background: ${palette.yellow.light3};
          color: ${palette.yellow.dark2};
          padding: 1px 5px;
          border-radius: 4px;
          font-size: 11px;
          font-weight: 700;
        }
        .approval-input {
          background: rgba(0,0,0,0.04);
          border: 1px solid ${palette.gray.light2};
          border-radius: 6px;
          padding: 6px 8px;
          font-size: 11px;
          white-space: pre-wrap;
          word-break: break-all;
          max-height: 120px;
          overflow-y: auto;
          margin: 0 0 8px;
        }
        .approval-btns { display: flex; gap: 8px; }
        .btn-approve, .btn-reject {
          flex: 1;
          padding: 6px 0;
          border: none;
          border-radius: 6px;
          font-size: 12px;
          font-weight: 700;
          cursor: pointer;
        }
        .btn-approve { background: ${palette.green.dark1}; color: white; }
        .btn-approve:hover { background: ${palette.green.dark2}; }
        .btn-reject  { background: ${palette.red.base}; color: white; }
        .btn-reject:hover  { background: ${palette.red.dark2}; }
        .approval-decision {
          padding: 6px 10px;
          border-radius: 6px;
          font-weight: 600;
          font-size: 12px;
          text-align: center;
        }
        .approval-decision.approved { background: ${palette.green.light3}; color: ${palette.green.dark2}; }
        .approval-decision.rejected { background: ${palette.red.light3}; color: ${palette.red.dark2}; }
      `}</style>
    </div>
  );
}

function TraceEntry({ entry }) {
  const [expanded, setExpanded] = useState(false);
  const isCall = entry.type === 'tool_call';
  return (
    <div className={`trace-entry ${isCall ? 'call' : 'result'}`}>
      <button className="trace-toggle" onClick={() => setExpanded(e => !e)}>
        <span className="trace-icon">{isCall ? '🔧' : '📦'}</span>
        <span className="trace-label">
          {isCall ? `Tool call: ${entry.name}` : `Result: ${entry.name}`}
        </span>
        <span className="trace-chevron">{expanded ? '▲' : '▼'}</span>
      </button>
      {expanded && (
        <pre className="trace-body">
          {JSON.stringify(isCall ? entry.input : entry.output, null, 2)}
        </pre>
      )}
      <style jsx>{`
        .trace-entry { margin: 4px 0; border-radius: 6px; overflow: hidden; font-size: 12px; }
        .trace-entry.call { border: 1px solid ${palette.blue.light2}; background: ${palette.blue.light3}; }
        .trace-entry.result { border: 1px solid ${palette.green.light2}; background: ${palette.green.light3}; }
        .trace-toggle {
          width: 100%; display: flex; align-items: center; gap: 6px;
          padding: 5px 8px; background: none; border: none;
          cursor: pointer; text-align: left; color: ${palette.gray.dark2};
          font-size: 12px; font-weight: 600;
        }
        .trace-icon { font-size: 13px; }
        .trace-label { flex: 1; }
        .trace-chevron { font-size: 10px; color: ${palette.gray.dark1}; }
        .trace-body {
          margin: 0; padding: 8px; font-size: 11px; white-space: pre-wrap;
          word-break: break-all; color: ${palette.gray.dark2};
          border-top: 1px solid ${palette.gray.light2};
          background: rgba(255,255,255,0.6);
          max-height: 200px; overflow-y: auto;
        }
      `}</style>
    </div>
  );
}

const TOOL_INFO = [
  {
    name: 'search_events',
    icon: '🔍',
    description: 'Searches the MongoDB Atlas database for driving events using hybrid vector + text search. Use it for questions about specific conditions (e.g. "foggy night on a highway"), rare scenarios, weather, season, or time of day.',
    params: ['query — natural language description', 'limit — max results (default 5, max 10)', 'domain — "adas" or "industrial"'],
  },
  {
    name: 'get_stats',
    icon: '📊',
    description: 'Returns aggregate statistics from the dataset: distribution of seasons, times of day, weather conditions, and average rarity score. Useful for "what is most/least common?" questions.',
    params: ['(no parameters required)'],
  },
  {
    name: 'compare_scenarios',
    icon: '⚖️',
    description: 'Runs two parallel searches and returns both result sets side by side. Great for direct comparisons like "foggy vs clear" or "night vs day".',
    params: ['query1 — first scenario description', 'query2 — second scenario description', 'limit — results per scenario (default 3)', 'domain — "adas" or "industrial"'],
  },
];

function ToolsPanel() {
  return (
    <div className="tools-panel">
      <div className="tools-title">🛠 Agent Tools</div>
      {TOOL_INFO.map(tool => (
        <div key={tool.name} className="tool-item">
          <div className="tool-header">
            <span className="tool-icon">{tool.icon}</span>
            <code className="tool-name">{tool.name}</code>
          </div>
          <p className="tool-desc">{tool.description}</p>
          <ul className="tool-params">
            {tool.params.map((p, i) => <li key={i}>{p}</li>)}
          </ul>
        </div>
      ))}
      <style jsx>{`
        .tools-panel {
          padding: 10px 14px 6px;
          border-top: 1px solid ${palette.gray.light2};
          background: #f7fbf7;
          overflow-y: auto;
          max-height: 240px;
          flex-shrink: 0;
        }
        .tools-title { font-size: 12px; font-weight: 700; color: ${palette.green.dark2}; margin-bottom: 8px; }
        .tool-item { margin-bottom: 10px; padding-bottom: 10px; border-bottom: 1px solid ${palette.gray.light2}; }
        .tool-item:last-child { border-bottom: none; margin-bottom: 0; }
        .tool-header { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
        .tool-icon { font-size: 13px; }
        .tool-name { font-size: 12px; font-weight: 700; background: ${palette.green.light3}; color: ${palette.green.dark2}; padding: 1px 6px; border-radius: 4px; }
        .tool-desc { font-size: 11px; color: ${palette.gray.dark2}; margin: 4px 0; line-height: 1.45; }
        .tool-params { margin: 2px 0 0 14px; padding: 0; font-size: 11px; color: ${palette.gray.dark1}; }
        .tool-params li { margin-bottom: 1px; }
      `}</style>
    </div>
  );
}

export default function ChatPanel({ open, onClose, onAgentSearch }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hi! I am the MongoDB AI Agent. Ask me about rare events, dataset statistics, or specific driving conditions.' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [showTools, setShowTools] = useState(false);
  // Real-time trace accumulation during streaming
  const [liveTrace, setLiveTrace] = useState([]);
  const liveTraceRef = useRef([]);
  const messagesEndRef = useRef(null);
  // Human-in-the-loop approval state
  const [pendingApproval, setPendingApproval] = useState(null);

  // Auto-scroll whenever messages or live trace changes
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, liveTrace, loading]);

  const sendMessage = async (text) => {
    const msg = (text || input).trim();
    if (!msg) return;

    const apiMessages = [...messages, { role: 'user', content: msg }]
      .filter(m => m.role === 'user' || m.role === 'assistant')
      .map(m => ({ role: m.role, content: m.content }));
    const newMessages = [...messages, { role: 'user', content: msg }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);
    liveTraceRef.current = [];
    setLiveTrace([]);

    try {
      const res = await fetch(`${API_BASE_URL}/api/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // hold incomplete line

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const data = line.slice(6).trim();
          if (data === '[DONE]') continue;
          try {
            const event = JSON.parse(data);
            if (event.type === 'trace') {
              liveTraceRef.current = [...liveTraceRef.current, event.entry];
              setLiveTrace([...liveTraceRef.current]);
              // Mirror search_events calls into the main search panel
              if (
                event.entry?.type === 'tool_call' &&
                event.entry?.name === 'search_events' &&
                event.entry?.input?.query &&
                typeof onAgentSearch === 'function'
              ) {
                onAgentSearch({ query: event.entry.input.query });
              }
            } else if (event.type === 'approval_required') {
              // HITL: agent is paused — show approval card, stream is blocked on backend
              setPendingApproval({
                approval_key: event.approval_key,
                tool_name: event.tool_name,
                tool_input: event.tool_input,
              });
            } else if (event.type === 'response') {
              setPendingApproval(null);
              setMessages(prev => [
                ...prev,
                { role: 'assistant', content: event.content, trace: liveTraceRef.current },
              ]);
              liveTraceRef.current = [];
              setLiveTrace([]);
            } else if (event.type === 'error') {
              throw new Error(event.message);
            }
          } catch (parseErr) {
            // ignore malformed SSE lines
          }
        }
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}`, trace: [] }]);
    } finally {
      setLoading(false);
      setPendingApproval(null);
      liveTraceRef.current = [];
      setLiveTrace([]);
    }
  };

  const handleApproval = async (approved) => {
    if (!pendingApproval) return;
    const { approval_key } = pendingApproval;
    // Clear the card immediately so the UI feels responsive
    setPendingApproval(null);
    try {
      await fetch(`${API_BASE_URL}/api/chat/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approval_key, approved }),
      });
    } catch (err) {
      console.error('Approval POST failed:', err);
    }
    // The backend unblocks and the SSE stream resumes — no further action needed here
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (!open) return null;

  const panelWidth  = isExpanded ? 700 : 480;
  const panelHeight = isExpanded ? '85vh' : 620;

  return (
    <div className="chat-panel" style={{ width: panelWidth, height: panelHeight }}>
      <div className="chat-header">
        <div className="chat-header-left">
          <span className="chat-header-icon">🤖</span>
          <H3 style={{ color: palette.white, margin: 0 }}>MongoDB AI Agent</H3>
        </div>
        <div className="chat-header-actions">
          <button className="icon-btn" title="Agent tools" onClick={() => setShowTools(t => !t)}>
            🛠
          </button>
          <button className="icon-btn" title={isExpanded ? 'Shrink' : 'Expand'} onClick={() => setIsExpanded(e => !e)}>
            {isExpanded ? '⊡' : '⊞'}
          </button>
          <button className="icon-btn close-btn" onClick={onClose}>✕</button>
        </div>
      </div>

      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-row ${msg.role}`}>
            {msg.role === 'assistant' && <div className="avatar">🤖</div>}
            <div className="bubble-wrap">
              <div className={`bubble ${msg.role}`}>
                <Body style={{ color: msg.role === 'user' ? palette.white : palette.gray.dark3, margin: 0 }}>
                  {msg.content}
                </Body>
              </div>
              {msg.trace && msg.trace.length > 0 && (
                <div className="trace-section">
                  <Label style={{ color: palette.gray.dark1, fontSize: '11px', fontWeight: 600 }}>
                    ⚙ Agent Execution Trace
                  </Label>
                  {msg.trace.map((entry, j) => (
                    <TraceEntry key={j} entry={entry} />
                  ))}
                </div>
              )}
            </div>
            {msg.role === 'user' && <div className="avatar user-avatar">👤</div>}
          </div>
        ))}

        {/* Real-time live trace — shown while agent is running */}
        {loading && liveTrace.length > 0 && (
          <div className="chat-row assistant">
            <div className="avatar">🤖</div>
            <div className="bubble-wrap">
              <div className="trace-section live-trace">
                <Label style={{ color: palette.gray.dark1, fontSize: '11px', fontWeight: 600 }}>
                  ⚙ Agent thinking…
                </Label>
                {liveTrace.map((entry, j) => (
                  <TraceEntry key={j} entry={entry} />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* HITL approval card — shown when agent pauses for user approval */}
        {pendingApproval && (
          <div className="chat-row assistant">
            <div className="avatar">🤖</div>
            <div className="bubble-wrap">
              <ApprovalCard approval={pendingApproval} onDecide={handleApproval} />
            </div>
          </div>
        )}

        {/* Typing indicator — shown while waiting before any trace arrives */}
        {loading && liveTrace.length === 0 && !pendingApproval && (
          <div className="chat-row assistant">
            <div className="avatar">🤖</div>
            <div className="bubble assistant typing">
              <span className="dot" /><span className="dot" /><span className="dot" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Tool info panel — toggled by 🛠 button in header */}
      {showTools && <ToolsPanel />}

      {/* Suggested questions — collapsible */}
      <div className="suggestions-wrapper">
        <button className="suggestions-toggle" onClick={() => setShowSuggestions(s => !s)}>
          <span>💡 Suggested questions</span>
          <span className="toggle-chevron">{showSuggestions ? '▲' : '▼'}</span>
        </button>
        {showSuggestions && !loading && (
          <div className="suggestions">
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button
                key={i}
                className={`suggestion-chip${q.hitl ? ' suggestion-chip--hitl' : ''}`}
                onClick={() => sendMessage(q.text)}
                title={q.hitl ? 'Triggers the Human-in-the-Loop approval workflow' : undefined}
              >
                {q.hitl && <span className="hitl-badge">🔐 Human in the loop demo</span>}
                {q.text}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="chat-input-row">
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about rare events, conditions, stats..."
          rows={2}
          disabled={loading}
        />
        <button className="send-btn" onClick={() => sendMessage()} disabled={loading || !input.trim()}>Send</button>
      </div>
      <style jsx>{`
        .chat-panel {
          position: fixed;
          right: 32px;
          bottom: 32px;
          max-width: 95vw;
          max-height: 90vh;
          background: ${palette.white};
          border-radius: 16px;
          box-shadow: 0 8px 32px rgba(0,0,0,0.22);
          z-index: 1000;
          display: flex;
          flex-direction: column;
          overflow: hidden;
          transition: width 0.25s ease, height 0.25s ease;
        }
        .chat-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 14px 16px;
          background: ${palette.green.dark2};
          flex-shrink: 0;
        }
        .chat-header-left {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .chat-header-icon { font-size: 20px; }
        .chat-header-actions {
          display: flex;
          align-items: center;
          gap: 6px;
        }
        .icon-btn {
          background: rgba(255,255,255,0.18);
          border: none;
          border-radius: 50%;
          width: 30px;
          height: 30px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 15px;
          font-weight: 700;
          color: ${palette.white};
          cursor: pointer;
          padding: 0;
          flex-shrink: 0;
        }
        .icon-btn:hover { background: rgba(255,255,255,0.3); }
        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 16px 12px;
          background: #f0f4f0;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .chat-row {
          display: flex;
          align-items: flex-end;
          gap: 8px;
        }
        .chat-row.user { flex-direction: row-reverse; }
        .avatar { font-size: 22px; flex-shrink: 0; width: 32px; text-align: center; }
        .user-avatar { font-size: 18px; }
        .bubble-wrap {
          display: flex;
          flex-direction: column;
          max-width: 80%;
        }
        .chat-row.user .bubble-wrap { align-items: flex-end; }
        .bubble {
          padding: 10px 14px;
          border-radius: 18px;
          line-height: 1.5;
          word-break: break-word;
        }
        .bubble.user {
          background: ${palette.green.dark1};
          border-bottom-right-radius: 4px;
        }
        .bubble.assistant {
          background: ${palette.white};
          border: 1px solid ${palette.gray.light2};
          border-bottom-left-radius: 4px;
          box-shadow: 0 1px 3px rgba(0,0,0,0.06);
        }
        .bubble.typing {
          display: flex;
          align-items: center;
          gap: 5px;
          padding: 12px 16px;
          min-width: 56px;
        }
        .dot {
          display: inline-block;
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: ${palette.gray.light1};
          animation: bounce 1.2s infinite ease-in-out;
        }
        .dot:nth-child(2) { animation-delay: 0.2s; }
        .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); background: ${palette.gray.light1}; }
          40% { transform: translateY(-6px); background: ${palette.green.base}; }
        }
        .trace-section { margin-top: 6px; width: 100%; }
        .live-trace { padding: 8px 10px; background: ${palette.white}; border: 1px solid ${palette.gray.light2}; border-radius: 12px; }
        .suggestions-wrapper {
          border-top: 1px solid ${palette.gray.light2};
          background: ${palette.white};
          flex-shrink: 0;
        }
        .suggestions-toggle {
          width: 100%;
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 6px 12px;
          background: none;
          border: none;
          cursor: pointer;
          font-size: 12px;
          font-weight: 600;
          color: ${palette.green.dark2};
        }
        .suggestions-toggle:hover { background: ${palette.green.light3}; }
        .toggle-chevron { font-size: 10px; color: ${palette.gray.dark1}; }
        .suggestions {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          padding: 4px 12px 10px;
          background: ${palette.white};
        }
        .suggestion-chip {
          background: ${palette.green.light3};
          color: ${palette.green.dark2};
          border: 1px solid ${palette.green.light2};
          border-radius: 16px;
          padding: 5px 12px;
          font-size: 12px;
          font-weight: 500;
          cursor: pointer;
          white-space: nowrap;
          transition: background 0.15s;
        }
        .suggestion-chip:hover { background: ${palette.green.light2}; }
        .suggestion-chip--hitl {
          background: #fff8e6;
          color: ${palette.yellow.dark2};
          border-color: ${palette.yellow.base};
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 2px;
          padding: 6px 12px;
        }
        .suggestion-chip--hitl:hover { background: #fff0c2; }
        .hitl-badge {
          font-size: 10px;
          font-weight: 700;
          color: ${palette.yellow.dark2};
          letter-spacing: 0.03em;
          text-transform: uppercase;
        }
        .chat-input-row {
          display: flex;
          gap: 8px;
          padding: 12px 14px;
          border-top: 1px solid ${palette.gray.light2};
          background: ${palette.white};
          flex-shrink: 0;
        }
        textarea {
          flex: 1;
          border-radius: 20px;
          border: 1px solid ${palette.gray.light2};
          padding: 8px 14px;
          font-size: 14px;
          resize: none;
          outline: none;
          font-family: inherit;
          background: #f5f5f5;
        }
        textarea:focus {
          border-color: ${palette.green.base};
          background: ${palette.white};
        }
        .send-btn {
          background: ${palette.green.dark1};
          color: white;
          border: none;
          border-radius: 20px;
          padding: 8px 18px;
          font-weight: 600;
          cursor: pointer;
          font-size: 14px;
          white-space: nowrap;
          flex-shrink: 0;
        }
        .send-btn:hover:not(:disabled) { background: ${palette.green.dark2}; }
        .send-btn:disabled {
          background: ${palette.gray.light2};
          color: ${palette.gray.dark1};
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
}
