import { useEffect, useState, useCallback } from 'react'
import { getCoverage, createBackfillPlan, type CoverageResponse, type BackfillPlanResponse } from '../api/client'
import Card from '../components/Card'
import StateMessage from '../components/StateMessage'

export default function Coverage() {
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [planSource, setPlanSource] = useState('aphis_inspections')
  const [planStart, setPlanStart] = useState('2020-01-01')
  const [planEnd, setPlanEnd] = useState('2026-06-13')
  const [planPages, setPlanPages] = useState(10)
  const [planDryRun, setPlanDryRun] = useState(true)
  const [planResult, setPlanResult] = useState<BackfillPlanResponse | null>(null)
  const [planError, setPlanError] = useState<string | null>(null)
  const [planSubmitting, setPlanSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getCoverage()
      setCoverage(data)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load coverage')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function handlePlanSubmit(e: React.FormEvent) {
    e.preventDefault()
    setPlanSubmitting(true)
    setPlanError(null)
    setPlanResult(null)
    try {
      const result = await createBackfillPlan({
        source: planSource,
        start_date: planStart,
        end_date: planEnd,
        max_pages: planPages,
        dry_run: planDryRun,
      })
      setPlanResult(result)
    } catch (e: unknown) {
      setPlanError(e instanceof Error ? e.message : 'Failed to create plan')
    } finally {
      setPlanSubmitting(false)
    }
  }

  if (loading) return <StateMessage type="loading" />
  if (error) return <StateMessage type="error" message={error} onRetry={load} />
  if (!coverage) return <StateMessage type="empty" message="No coverage data available." />

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Coverage Status</h2>

      <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4 mb-6">
        <p className="text-sm font-medium text-yellow-800">
          {coverage.message}
        </p>
        {coverage.historical_backfill_details && (
          <p className="mt-2 text-xs text-yellow-700">
            {coverage.historical_backfill_details}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card title="Total Documents" value={coverage.total_documents} variant="info" />
        <Card title="Documents With Text" value={coverage.total_documents_with_text} variant="success" />
        <Card title="Backfill Status" value={coverage.historical_backfill_status} variant="warning" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Sources Attempted</h3>
          {coverage.sources_attempted.length === 0 ? (
            <p className="text-sm text-gray-400">No sources attempted yet.</p>
          ) : (
            <ul className="space-y-1">
              {coverage.sources_attempted.map((s) => (
                <li key={s} className="text-sm text-gray-700 flex justify-between">
                  <span>{s}</span>
                  <span className="font-medium">{coverage.total_records_by_source[s] || 0}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Date Ranges Attempted</h3>
          {coverage.date_ranges_attempted.length === 0 ? (
            <p className="text-sm text-gray-400">No date ranges recorded.</p>
          ) : (
            coverage.date_ranges_attempted.map((dr, i) => (
              <p key={i} className="text-sm text-gray-700">
                {dr.start} — {dr.end}
              </p>
            ))
          )}
        </div>
      </div>

      {coverage.last_successful_run && (
        <div className="mt-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Last Successful Run</h3>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-sm">
            <div><span className="text-gray-500">Source:</span><p className="font-medium">{coverage.last_successful_run.source}</p></div>
            <div><span className="text-gray-500">Status:</span><p className="font-medium">{coverage.last_successful_run.status}</p></div>
            <div><span className="text-gray-500">Records:</span><p className="font-medium">{coverage.last_successful_run.records_found}</p></div>
            <div><span className="text-gray-500">Saved:</span><p className="font-medium">{coverage.last_successful_run.records_saved}</p></div>
          </div>
        </div>
      )}

      <div className="mt-8 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Backfill Plan</h3>
        <form onSubmit={handlePlanSubmit} className="space-y-3">
          <div className="flex flex-wrap gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Source</label>
              <select
                value={planSource}
                onChange={(e) => setPlanSource(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="aphis_inspections">APHIS Inspections</option>
                <option value="aphis_enforcement">APHIS Enforcement</option>
                <option value="ecfr">eCFR</option>
                <option value="federal_register">Federal Register</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Start Date</label>
              <input
                type="date"
                value={planStart}
                onChange={(e) => setPlanStart(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">End Date</label>
              <input
                type="date"
                value={planEnd}
                onChange={(e) => setPlanEnd(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Max Pages</label>
              <input
                type="number"
                value={planPages}
                onChange={(e) => setPlanPages(Number(e.target.value))}
                min={1}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-20"
              />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={planDryRun}
                  onChange={(e) => setPlanDryRun(e.target.checked)}
                  className="rounded border-gray-300"
                />
                Dry Run
              </label>
            </div>
            <div className="flex items-end">
              <button
                type="submit"
                disabled={planSubmitting}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {planSubmitting ? 'Creating...' : 'Create Plan'}
              </button>
            </div>
          </div>
        </form>

        {planError && (
          <p className="mt-3 text-sm text-red-600">{planError}</p>
        )}

        {planResult && (
          <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Planned Stages</h4>
            <ul className="space-y-1">
              {planResult.planned_stages.map((stage, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-medium">{i + 1}</span>
                  {stage}
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-yellow-700">{planResult.warning}</p>
          </div>
        )}
      </div>
    </div>
  )
}