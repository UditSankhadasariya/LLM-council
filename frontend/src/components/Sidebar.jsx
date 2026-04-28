import { useRef } from 'react';
import './Sidebar.css';

function formatDateLabel(dateStr) {
  const today = new Date();
  const todayStr = today.getFullYear() + '-' +
    String(today.getMonth() + 1).padStart(2, '0') + '-' +
    String(today.getDate()).padStart(2, '0');

  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.getFullYear() + '-' +
    String(yesterday.getMonth() + 1).padStart(2, '0') + '-' +
    String(yesterday.getDate()).padStart(2, '0');

  if (dateStr === todayStr) return 'Today';
  if (dateStr === yesterdayStr) return 'Yesterday';

  const [year, month, day] = dateStr.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function shiftDate(dateStr, days) {
  const [year, month, day] = dateStr.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  d.setDate(d.getDate() + days);
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0');
}

function getToday() {
  const d = new Date();
  return d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0');
}

export default function Sidebar({
  conversations,
  currentConversationId,
  onSelectConversation,
  onNewConversation,
  selectedDate,
  availableDates,
  onDateChange,
  isOpen,
  onToggle,
}) {
  const dateInputRef = useRef(null);
  const today = getToday();
  const isToday = selectedDate === today;

  return (
    <div className={`sidebar ${isOpen ? '' : 'is-collapsed'}`}>
      <div className="sidebar-header">
        <div className="sidebar-header-top">
          <h1>LLM Council</h1>
          <button
            className="sidebar-toggle"
            onClick={onToggle}
            title="Hide sidebar"
            aria-label="Hide sidebar"
          >
            &#8249;
          </button>
        </div>
        <button className="new-conversation-btn" onClick={onNewConversation}>
          + New Conversation
        </button>
      </div>

      <div className="date-navigator">
        <button
          className="date-nav-btn"
          onClick={() => onDateChange(shiftDate(selectedDate, -1))}
          title="Previous day"
        >
          &#8249;
        </button>
        <div className="date-display" onClick={() => dateInputRef.current?.showPicker()}>
          {formatDateLabel(selectedDate)}
          <input
            ref={dateInputRef}
            type="date"
            className="date-picker-input"
            value={selectedDate}
            max={today}
            onChange={(e) => {
              if (e.target.value) onDateChange(e.target.value);
            }}
          />
        </div>
        <button
          className="calendar-icon-btn"
          onClick={() => dateInputRef.current?.showPicker()}
          title="Pick a date"
          aria-label="Pick a date"
        >
          <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        </button>
        <button
          className="date-nav-btn"
          onClick={() => onDateChange(shiftDate(selectedDate, 1))}
          disabled={isToday}
          title="Next day"
        >
          &#8250;
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div className="no-conversations">No conversations on this day</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className={`conversation-item ${
                conv.id === currentConversationId ? 'active' : ''
              }`}
              onClick={() => onSelectConversation(conv.id)}
            >
              <div className="conversation-title">
                {conv.title || 'New Conversation'}
              </div>
              <div className="conversation-meta">
                {conv.message_count} messages
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
