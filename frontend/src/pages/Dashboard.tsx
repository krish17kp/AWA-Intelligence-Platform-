import { useEffect, useState } from 'react'
import { getStats, type StatsResponse } from '../api/client'
import Card from '../components/Card'
import StateMessage from '../components/StateMessage'

export default function Dashboard() {
  const [stats, setStats] = useState<StatsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await getStats()
      setStats(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load stats')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return <StateMessage type="loading" />
  if (error) return <StateMessage type="error" message={error} onRetry={load} />
  if (!stats) return <StateMessage type="empty" message="No stats available." />

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Dashboard</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="Total Documents" value={stats.total_documents} variant="info" />
        <Card title="Raw Files Preserved" value={stats.total_raw_files_preserved} variant="success" />
        <Card title="Documents With Text" value={stats.total_documents_with_text} variant="success" />
        <Card title="Duplicates Skipped" value={stats.total_duplicates_skipped} subtitle={stats.duplicate_tracking_note} variant="warning" />
        <Card title="Failed Documents" value={stats.total_failed_documents} subtitle={stats.failed_documents_note} variant="danger" />
        <Card title="Ingestion Runs" value={stats.total_ingestion_runs} variant="info" />
        <Card
          title="Extraction Success Rate"
          value={`${stats.extraction_success_rate}%`}
          variant={stats.extraction_success_rate > 50 ? 'success' : 'warning'}
        />
        <Card title="QA Needed" value={stats.qa_needed_count} variant="default" />
      </div>

      {stats.latest_ingestion_run && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">Latest Ingestion Run</h3>
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-500">Source:</span>
                <p className="font-medium">{stats.latest_ingestion_run.source}</p>
              </div>
              <div>
                <span className="text-gray-500">Status:</span>
                <p className="font-medium">{stats.latest_ingestion_run.status}</p>
              </div>
              <div>
                <span className="text-gray-500">Records Found:</span>
                <p className="font-medium">{stats.latest_ingestion_run.records_found}</p>
              </div>
              <div>
                <span className="text-gray-500">Records Saved:</span>
                <p className="font-medium">{stats.latest_ingestion_run.records_saved}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}