import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { getDocuments, type DocumentItem } from '../api/client'
import DataTable from '../components/DataTable'
import StateMessage from '../components/StateMessage'

function shortHash(hash: string): string {
  return hash.length > 12 ? `${hash.slice(0, 6)}...${hash.slice(-4)}` : hash
}

export default function Documents() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [data, setData] = useState<{ items: DocumentItem[]; total: number; page: number; page_size: number } | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const page = Number(searchParams.get('page')) || 1
  const q = searchParams.get('q') || ''
  const sourceType = searchParams.get('source_type') || ''
  const extractionStatus = searchParams.get('extraction_status') || ''

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await getDocuments({
        page,
        page_size: 25,
        q: q || undefined,
        source_type: sourceType || undefined,
        extraction_status: extractionStatus || undefined,
      })
      setData(result)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [page, q, sourceType, extractionStatus])

  useEffect(() => { load() }, [load])

  function updateParam(key: string, value: string) {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== 'page') next.set('page', '1')
    setSearchParams(next)
  }

  const columns = [
    { key: 'title', label: 'Title', render: (v: unknown) => <span className="font-medium text-gray-900">{String(v || 'Untitled')}</span> },
    { key: 'source_type', label: 'Source Type' },
    { key: 'source_name', label: 'Source' },
    {
      key: 'retrieved_at',
      label: 'Retrieved',
      render: (v: unknown) => v ? new Date(v as string).toLocaleDateString() : '-',
    },
    {
      key: 'content_hash',
      label: 'Hash',
      render: (v: unknown) => <code className="text-xs text-gray-500">{shortHash(v as string)}</code>,
    },
    {
      key: 'extraction_status',
      label: 'Extraction',
      render: (v: unknown) => {
        const s = v as string
        const cls = s === 'extracted' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
        return <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${cls}`}>{s}</span>
      },
    },
    {
      key: 'raw_storage_path',
      label: 'Raw Preserved',
      render: (v: unknown) => v ? <span className="text-green-600 font-medium">Yes</span> : <span className="text-gray-400">No</span>,
    },
    {
      key: 'id',
      label: '',
      render: (v: unknown) => (
        <button
          onClick={() => navigate(`/documents/${v}`)}
          className="px-3 py-1 text-xs font-medium text-blue-700 bg-blue-50 rounded hover:bg-blue-100 transition-colors"
        >
          View
        </button>
      ),
    },
  ]

  const rows = (data?.items || []).map((d) => ({ ...d } as unknown as Record<string, unknown>))

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Documents</h2>

      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search..."
          value={q}
          onChange={(e) => updateParam('q', e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-48"
        />
        <select
          value={sourceType}
          onChange={(e) => updateParam('source_type', e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Types</option>
          <option value="awa_inspection_report">Inspection Report</option>
          <option value="awa_enforcement_action">Enforcement Action</option>
          <option value="ecfr">eCFR</option>
          <option value="federal_register">Federal Register</option>
        </select>
        <select
          value={extractionStatus}
          onChange={(e) => updateParam('extraction_status', e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          <option value="">All Status</option>
          <option value="extracted">Extracted</option>
          <option value="pending">Pending</option>
        </select>
      </div>

      {loading ? (
        <StateMessage type="loading" />
      ) : error ? (
        <StateMessage type="error" message={error} onRetry={load} />
      ) : data && data.items.length === 0 ? (
        <StateMessage type="empty" message="No documents available yet. Run ingestion to populate the repository." />
      ) : (
        <>
          <DataTable columns={columns} rows={rows} />
          {data && data.total > 0 && (
            <div className="flex items-center justify-between mt-4 text-sm text-gray-600">
              <span>
                Page {data.page} of {Math.max(1, Math.ceil(data.total / data.page_size))} ({data.total} total)
              </span>
              <div className="flex gap-2">
                <button
                  disabled={data.page <= 1}
                  onClick={() => updateParam('page', String(data.page - 1))}
                  className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50"
                >
                  Previous
                </button>
                <button
                  disabled={data.page * data.page_size >= data.total}
                  onClick={() => updateParam('page', String(data.page + 1))}
                  className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}