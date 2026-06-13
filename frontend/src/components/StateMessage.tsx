interface StateMessageProps {
  type: 'loading' | 'error' | 'empty'
  message?: string
  onRetry?: () => void
}

export default function StateMessage({ type, message, onRetry }: StateMessageProps) {
  const defaultMessages = {
    loading: 'Loading...',
    error: 'Something went wrong.',
    empty: 'No data available.',
  }

  const styles = {
    loading: 'text-blue-600',
    error: 'text-red-600',
    empty: 'text-gray-500',
  }

  return (
    <div className={`flex flex-col items-center justify-center py-16 ${styles[type]}`}>
      {type === 'loading' && (
        <svg className="animate-spin h-8 w-8 mb-3" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      <p className="text-sm font-medium">{message || defaultMessages[type]}</p>
      {type === 'error' && onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  )
}