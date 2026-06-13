import { useEffect, useState, useCallback } from 'react'
import { getIngestionRuns, type IngestionRun } from '../api/client'
import DataTable from '../components/DataTable'
import StateMessage from '../components/StateMessage'

export default function Ingestion() {
  const [runs, setRuns] = useState<IngestionRun[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

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
    { key: 'new_documents', label: 'New Documents' },
    { key: 'duplicates_skipped', label: 'Duplicates' },
    { key: 'failed_documents', label: 'Failed' },
    { key: 'error_message', label: 'Error', render: (v: unknown) => v ? <span className="text-red-600 text-xs">{v as string}</span> : '-' },
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
    </div>
  )
}