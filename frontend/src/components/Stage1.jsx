import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import './Stage1.css';

export default function Stage1({ responses, expectedModels, isLoading }) {
  const [activeTab, setActiveTab] = useState(0);

  // Show nothing only if there are no responses AND no expected models (historical conversation with no data)
  if ((!responses || responses.length === 0) && !expectedModels) {
    return null;
  }

  const completedModels = new Set(responses.map((r) => r.model));

  // During progressive loading, show tabs for all expected models
  const showProgressiveTabs = isLoading && expectedModels && expectedModels.length > 0;
  const tabModels = showProgressiveTabs ? expectedModels : responses.map((r) => r.model);

  const activeModel = tabModels[activeTab];
  const activeResponse = responses.find((r) => r.model === activeModel);
  const isPending = showProgressiveTabs && !completedModels.has(activeModel);

  return (
    <div className="stage stage1">
      <h3 className="stage-title">
        Stage 1: Individual Responses
        {isLoading && (
          <span className="stage1-progress">
            ({responses.length}/{tabModels.length})
          </span>
        )}
      </h3>

      <div className="tabs">
        {tabModels.map((model, index) => {
          const isComplete = completedModels.has(model);
          const tabPending = showProgressiveTabs && !isComplete;
          return (
            <button
              key={model}
              className={`tab ${activeTab === index ? 'active' : ''} ${tabPending ? 'tab-pending' : ''}`}
              onClick={() => setActiveTab(index)}
            >
              {model}
              {tabPending && <span className="tab-spinner" />}
            </button>
          );
        })}
      </div>

      <div className="tab-content">
        {isPending ? (
          <div className="model-loading">
            <div className="spinner"></div>
            <span>Waiting for {activeModel}...</span>
          </div>
        ) : activeResponse ? (
          <>
            <div className="model-name">{activeResponse.model}</div>
            <div className="response-text markdown-content">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{activeResponse.response}</ReactMarkdown>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}
