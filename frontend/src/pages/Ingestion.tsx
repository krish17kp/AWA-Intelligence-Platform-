import { useEffect, useState, useCallback } from 'react'
import { getIngestionRuns, getIngestionRunEvents, type IngestionRun, type IngestionEventItem } from '../api/client'
import DataTable from '../components/DataTable'
import StateMessage from '../components/StateMessage'

export default function Ingestion() {
  const [runs, setRuns] = useState<IngestionRun[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [eventsModal, setEventsModal] = useState<{ runId: number; events: IngestionEventItem[]; loading: boolean } | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getIngestionRuns()
      setRuns(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load ingestion runs')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handleViewEvents(runId: number) {
    setEventsModal({ runId, events: [], loading: true })
    try {
      const events = await getIngestionRunEvents(runId)
      setEventsModal({ runId, events, loading: false })
    } catch {
      setEventsModal({ runId, events: [], loading: false })
    }
  }

  const columns = [
    { key: 'run_id', label: 'Run ID' },
    { key: 'source', label: 'Source' },
    { key: 'run_type', label: 'Run Type', render: (v: unknown) => String(v || '-') },
    {
      key: 'status',
      label: 'Status',
      render: (v: unknown) => {
        const s = v as string
        const cls = s === 'completed' || s === 'success' ? 'bg-green-100 text-green-800'
          : s === 'failed' || s === 'error' ? 'bg-red-100 text-red-800'
          : s === 'dry_run' ? 'bg-blue-100 text-blue-800'
          : 'bg-yellow-100 text-yellow-800'
        return <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{s}</span>
      },
    },
    {
      key: 'started_at',
      label: 'Started',
      render: (v: unknown) => v ? new Date(v as string).toLocaleString() : '-',
    },
    {
      key: 'completed_at',
      label: 'Completed',
      render: (v: unknown) => v ? new Date(v as string).toLocaleString() : '-',
    },
    { key: 'records_found', label: 'Records Found' },
    { key: 'new_documents', label: 'New Docs' },
    { key: 'duplicates_skipped', label: 'Duplicates' },
    { key: 'failed_documents', label: 'Failed' },
    {
      key: 'error_message',
      label: 'Error',
      render: (v: unknown) => v ? <span className="text-red-600 text-xs">{v as string}</span> : '-',
    },
    {
      key: 'run_id',
      label: 'Events',
      render: (v: unknown) => (
        <button
          onClick={() => handleViewEvents(v as number)}
          className="px-2 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
        >
          View Events
        </button>
      ),
    },
  ]

  const rows = runs.map((r) => ({ ...r } as unknown as Record<string, unknown>))

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Ingestion Runs</h2>
      {loading ? (
        <StateMessage type="loading" />
      ) : error ? (
        <StateMessage type="error" message={error} onRetry={load} />
      ) : runs.length === 0 ? (
        <StateMessage type="empty" message="No ingestion runs recorded yet." />
      ) : (
        <DataTable columns={columns} rows={rows} emptyMessage="No ingestion runs recorded yet." />
      )}

      {eventsModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50" onClick={() => setEventsModal(null)}>
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full mx-4 max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
              <h3 className="text-sm font-semibold text-gray-700">Events — Run #{eventsModal.runId}</h3>
              <button onClick={() => setEventsModal(null)} className="text-gray-400 hover:text-gray-600 text-lg leading-none">&times;</button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {eventsModal.loading ? (
                <StateMessage type="loading" />
              ) : eventsModal.events.length === 0 ? (
                <StateMessage type="empty" message="No events recorded for this run." />
              ) : (
                <div className="space-y-2">
                  {eventsModal.events.map((evt) => (
                    <div key={evt.id} className="flex items-start gap-3 text-sm p-3 bg-gray-50 rounded border border-gray-100">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium shrink-0 ${
                        evt.event_type.includes('fail') || evt.event_type === 'document_failed' ? 'bg-red-100 text-red-700'
                          : evt.event_type === 'duplicate_skipped' ? 'bg-yellow-100 text-yellow-700'
                          : evt.event_type === 'run_started' || evt.event_type === 'run_completed' ? 'bg-blue-100 text-blue-700'
                          : 'bg-green-100 text-green-700'
                      }`}>
                        {evt.event_type}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className="text-gray-700">{evt.message || '-'}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {evt.created_at ? new Date(evt.created_at).toLocaleString() : ''}
                          {evt.document_id ? ` | doc: ${evt.document_id}` : ''}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}