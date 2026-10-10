interface ErrorBannerProps {
  message: string;
  onRetry?: (() => void) | undefined;
}

export function ErrorBanner({ message, onRetry }: ErrorBannerProps) {
  return (
    <div className="error-banner" role="alert">
      <span>{message}</span>
      {onRetry && (
        <button type="button" className="btn btn-small btn-danger" onClick={onRetry}>
          Erneut versuchen
        </button>
      )}
    </div>
  );
}
