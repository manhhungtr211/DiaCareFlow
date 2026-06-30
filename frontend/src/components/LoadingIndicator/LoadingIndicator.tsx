import './LoadingIndicator.css';

export function LoadingIndicator() {
  return (
    <div className="loading-indicator" aria-label="Đang tải...">
      <div className="loading-indicator__avatar">
        <span className="loading-indicator__avatar-icon">🩺</span>
      </div>
      <div className="loading-indicator__dots">
        <span className="loading-indicator__dot" />
        <span className="loading-indicator__dot" />
        <span className="loading-indicator__dot" />
      </div>
    </div>
  );
}
