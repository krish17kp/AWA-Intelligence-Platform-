import { useCallback, useEffect, useState } from 'react'
import {
  createBackfillPlan,
  getCoverage,
  runBackfill,
  type BackfillPlanResponse,
  type BackfillRunResponse,
  type CoverageResponse,
} from '../api/client'
import Card from '../components/Card'
import DataTable from '../components/DataTable'
import StateMessage from '../components/StateMessage'

const SOURCES = [
  { value: 'aphis_inspections', label: 'APHIS Inspections' },
  { value: 'aphis_enforcement', label: 'APHIS Enforcement' },
  { value: 'federal_register', label: 'Federal Register' },
  { value: 'ecfr', label: 'eCFR' },
]

const STATE_CODES = [
  'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
  'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
  'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
  'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
  'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
  'DC',
]

export default function Coverage() {
  const [coverage, setCoverage] = useState<CoverageResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const [planSource, setPlanSource] = useState('aphis_inspections')
  const [planStart, setPlanStart] = useState('2026-01-01')
  const [planEnd, setPlanEnd] = useState('2026-06-14')
  const [planPages, setPlanPages] = useState(2)
  const [planPageSize, setPlanPageSize] = useState(50)
  const [planDryRun, setPlanDryRun] = useState(true)
  const [planForceRefresh, setPlanForceRefresh] = useState(false)
  const [planStateCode, setPlanStateCode] = useState('TX')
  const [planIncludeAllStates, setPlanIncludeAllStates] = useState(false)
  const [planConfirmLargeRun, setPlanConfirmLargeRun] = useState(false)
  const [planResult, setPlanResult] = useState<BackfillPlanResponse | null>(null)
  const [runResult, setRunResult] = useState<BackfillRunResponse | null>(null)
  const [planError, setPlanError] = useState<string | null>(null)
  const [planSubmitting, setPlanSubmitting] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setCoverage(await getCoverage())
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load coverage')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const isStateAwareSource = planSource === 'aphis_inspections'
  const unsafeAllStateRealRun =
    isStateAwareSource &&
    planIncludeAllStates &&
    !planDryRun &&
    !planConfirmLargeRun

  function stateRequestFields() {
    return {
      state_code:
        isStateAwareSource && !planIncludeAllStates
          ? planStateCode || undefined
          : undefined,
      include_all_states: isStateAwareSource && planIncludeAllStates,
      confirm_large_run: isStateAwareSource && planConfirmLargeRun,
    }
  }

  async function handlePreviewPlan(e: React.FormEvent) {
    e.preventDefault()
    setPlanSubmitting(true)
    setPlanError(null)
    setPlanResult(null)
    setRunResult(null)
    try {
      setPlanResult(await createBackfillPlan({
        source: planSource,
        start_date: planStart,
        end_date: planEnd,
        max_pages: planPages,
        dry_run: true,
        ...stateRequestFields(),
      }))
    } catch (e: unknown) {
      setPlanError(e instanceof Error ? e.message : 'Failed to create plan')
    } finally {
      setPlanSubmitting(false)
    }
  }

  async function handleRunBackfill(e: React.FormEvent) {
    e.preventDefault()
    setPlanSubmitting(true)
    setPlanError(null)
    setPlanResult(null)
    setRunResult(null)
    try {
      setRunResult(await runBackfill({
        source: planSource,
        start_date: planStart,
        end_date: planEnd,
        max_pages: planPages,
        page_size: planPageSize,
        dry_run: planDryRun,
        force_refresh: planForceRefresh,
        ...stateRequestFields(),
      }))
      void load()
    } catch (e: unknown) {
      setPlanError(e instanceof Error ? e.message : 'Failed to run backfill')
    } finally {
      setPlanSubmitting(false)
    }
  }

  if (loading) return <StateMessage type="loading" />
  if (error) return <StateMessage type="error" message={error} onRetry={load} />
  if (!coverage) return <StateMessage type="empty" message="No coverage data available." />

  const snapshotsColumns = [
    { key: 'id', label: 'ID' },
    { key: 'source', label: 'Source' },
    { key: 'state_code', label: 'State' },
    { key: 'records_found', label: 'Records Found' },
    { key: 'records_preserved', label: 'Preserved' },
    { key: 'duplicates_skipped', label: 'Duplicates' },
    { key: 'status', label: 'Status' },
  ]
  const snapshotsRows = coverage.latest_coverage_snapshots.map((snapshot) => ({
    ...snapshot,
    state_code: snapshot.state_code || 'N/A',
  }))

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Coverage Status</h2>

      <div className="rounded-lg border border-yellow-300 bg-yellow-50 p-4 mb-6">
        <p className="text-sm font-medium text-yellow-800">{coverage.message}</p>
        {coverage.known_limitations.length > 0 && (
          <ul className="mt-2 list-disc list-inside text-xs text-yellow-700 space-y-0.5">
            {coverage.known_limitations.map((limitation) => (
              <li key={limitation}>{limitation}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card title="Backfill Status" value={coverage.historical_backfill_status} variant="warning" />
        <Card title="Sources Attempted" value={coverage.sources_attempted.length} variant="info" />
        <Card title="States Attempted" value={coverage.states_attempted.length} variant="info" />
        <Card title="Records by Source" value={Object.keys(coverage.total_records_by_source).length} variant="info" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Sources Attempted</h3>
          {coverage.sources_attempted.length === 0 ? (
            <p className="text-sm text-gray-400">No sources attempted yet.</p>
          ) : (
            <ul className="space-y-1">
              {coverage.sources_attempted.map((source) => (
                <li key={source} className="text-sm text-gray-700 flex justify-between">
                  <span>{source}</span>
                  <span className="font-medium">{coverage.total_records_by_source[source] || 0}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">States Attempted</h3>
          {coverage.states_attempted.length === 0 ? (
            <p className="text-sm text-gray-400">No state coverage snapshots recorded.</p>
          ) : (
            <ul className="space-y-1 max-h-52 overflow-y-auto">
              {coverage.states_attempted.map((state) => (
                <li key={state} className="text-sm text-gray-700 flex justify-between">
                  <span>{state}</span>
                  <span className="font-medium">{coverage.total_records_by_state[state] || 0}</span>
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
            coverage.date_ranges_attempted.map((range, index) => (
              <p key={`${range.source}-${range.state_code}-${index}`} className="text-sm text-gray-700">
                {range.state_code ? `${range.state_code}: ` : ''}{range.start} - {range.end}
              </p>
            ))
          )}
        </div>
      </div>

      {coverage.last_successful_run && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Last Successful Run</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div><span className="text-gray-500">Source:</span><p className="font-medium">{coverage.last_successful_run.source}</p></div>
            <div><span className="text-gray-500">Status:</span><p className="font-medium">{coverage.last_successful_run.status}</p></div>
            <div><span className="text-gray-500">Records:</span><p className="font-medium">{coverage.last_successful_run.records_found}</p></div>
            <div><span className="text-gray-500">New Docs:</span><p className="font-medium">{coverage.last_successful_run.new_documents}</p></div>
          </div>
        </div>
      )}

      {coverage.latest_coverage_snapshots.length > 0 && (
        <div className="mb-6 rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
          <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Latest Coverage Snapshots</h3>
          <DataTable columns={snapshotsColumns} rows={snapshotsRows} emptyMessage="No snapshots available." />
        </div>
      )}

      <div className="mt-8 rounded-lg border border-blue-200 bg-white p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-4">Run Controlled Backfill</h3>
        <form onSubmit={handleRunBackfill} className="space-y-3">
          <div className="flex flex-wrap gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Source</label>
              <select
                value={planSource}
                onChange={(e) => {
                  setPlanSource(e.target.value)
                  setPlanIncludeAllStates(false)
                  setPlanConfirmLargeRun(false)
                }}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {SOURCES.map((source) => (
                  <option key={source.value} value={source.value}>{source.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">State Code</label>
              <select
                value={planStateCode}
                onChange={(e) => setPlanStateCode(e.target.value)}
                disabled={!isStateAwareSource || planIncludeAllStates}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-100 disabled:text-gray-400"
              >
                <option value="">Backend default (TX)</option>
                {STATE_CODES.map((state) => (
                  <option key={state} value={state}>{state}</option>
                ))}
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
                max={50}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-20"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Page Size</label>
              <input
                type="number"
                value={planPageSize}
                onChange={(e) => setPlanPageSize(Number(e.target.value))}
                min={1}
                max={200}
                className="px-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 w-20"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={planDryRun}
                onChange={(e) => setPlanDryRun(e.target.checked)}
                className="rounded border-gray-300"
              />
              Dry Run
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={planForceRefresh}
                onChange={(e) => setPlanForceRefresh(e.target.checked)}
                className="rounded border-gray-300"
              />
              Force Refresh
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={planIncludeAllStates}
                onChange={(e) => {
                  setPlanIncludeAllStates(e.target.checked)
                  if (!e.target.checked) setPlanConfirmLargeRun(false)
                }}
                disabled={!isStateAwareSource}
                className="rounded border-gray-300"
              />
              Include All States
            </label>
            <label className="flex items-center gap-1.5 text-sm">
              <input
                type="checkbox"
                checked={planConfirmLargeRun}
                onChange={(e) => setPlanConfirmLargeRun(e.target.checked)}
                disabled={!isStateAwareSource || !planIncludeAllStates}
                className="rounded border-gray-300"
              />
              Confirm Large Run
            </label>
          </div>

          {isStateAwareSource && planIncludeAllStates && !planDryRun && (
            <div className="rounded border border-red-300 bg-red-50 p-3 text-sm text-red-700">
              All-state real backfill is a large operation and requires Confirm Large Run.
            </div>
          )}

          <div className="flex gap-3">
            <button
              type="button"
              onClick={handlePreviewPlan}
              disabled={planSubmitting}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 transition-colors"
            >
              Preview Plan
            </button>
            <button
              type="submit"
              disabled={planSubmitting || unsafeAllStateRealRun}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {planSubmitting ? 'Running...' : planDryRun ? 'Run Dry Run' : 'Run Backfill'}
            </button>
          </div>
        </form>

        {planError && <p className="mt-3 text-sm text-red-600">{planError}</p>}

        {planResult && (
          <div className="mt-4 p-3 bg-gray-50 rounded border border-gray-200">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">Planned Stages</h4>
            <ul className="space-y-1">
              {planResult.planned_stages.map((stage, index) => (
                <li key={stage} className="text-sm text-gray-600 flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-xs font-medium">{index + 1}</span>
                  {stage}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-gray-600">
              <span className="font-semibold">Filters:</span> {JSON.stringify(planResult.filters)}
            </p>
            <p className="mt-2 text-xs text-yellow-700">{planResult.warning}</p>
          </div>
        )}

        {runResult && (
          <div className="mt-4 p-4 rounded border border-blue-200 bg-blue-50">
            <h4 className="text-sm font-semibold text-gray-700 mb-2">
              Run {runResult.dry_run ? 'Dry Run' : 'Complete'} - Result
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div><span className="text-gray-500">Run ID:</span><p className="font-medium">{runResult.run_id}</p></div>
              <div><span className="text-gray-500">Status:</span><p className={`font-medium ${runResult.status === 'failed' ? 'text-red-600' : 'text-green-600'}`}>{runResult.status}</p></div>
              <div><span className="text-gray-500">Records Found:</span><p className="font-medium">{runResult.records_found}</p></div>
              <div><span className="text-gray-500">New Documents:</span><p className="font-medium">{runResult.new_documents}</p></div>
              <div><span className="text-gray-500">Duplicates Skipped:</span><p className="font-medium">{runResult.duplicates_skipped}</p></div>
              <div><span className="text-gray-500">Failed:</span><p className="font-medium">{runResult.failed_documents}</p></div>
              <div><span className="text-gray-500">Preserved:</span><p className="font-medium">{runResult.records_preserved}</p></div>
              <div><span className="text-gray-500">Extracted:</span><p className="font-medium">{runResult.records_extracted}</p></div>
            </div>
            <div className="mt-3 rounded border border-blue-100 bg-white p-3 text-xs text-gray-700">
              <p><span className="font-semibold">State:</span> {runResult.state_code || (runResult.include_all_states ? 'All states' : 'N/A')}</p>
              <p><span className="font-semibold">Date range:</span> {runResult.date_range_start} - {runResult.date_range_end}</p>
              <p><span className="font-semibold">Filters:</span> {JSON.stringify(runResult.filters)}</p>
              <p><span className="font-semibold">Coverage snapshot:</span> {runResult.coverage_snapshot_id ?? 'Not created for dry run'}</p>
            </div>
            {runResult.errors.length > 0 && (
              <div className="mt-2 text-xs text-red-600">
                {runResult.errors.map((runError) => <p key={runError}>{runError}</p>)}
              </div>
            )}
            <p className="mt-3 text-xs text-yellow-700">{runResult.warning}</p>
            {runResult.known_limitations.length > 0 && (
              <ul className="mt-2 list-disc list-inside text-xs text-yellow-700">
                {runResult.known_limitations.map((limitation) => (
                  <li key={limitation}>{limitation}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
