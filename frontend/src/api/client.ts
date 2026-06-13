const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json()
}

export interface HealthResponse {
  status: string
  service: string
  version: string
  database: string
  storage: string
  storage_mode: string
  timestamp: string
}

export interface StatsResponse {
  total_documents: number
  total_raw_files_preserved: number
  total_documents_with_text: number
  total_duplicates_skipped: number
  duplicate_tracking_note?: string
  total_failed_documents: number
  failed_documents_note?: string
  total_ingestion_runs: number
  latest_ingestion_run: {
    id: number
    source: string
    status: string
    started_at: string | null
    completed_at: string | null
    records_found: number
    records_saved: number
  } | null
  extraction_success_rate: number
  qa_needed_count: number
}

export interface DocumentItem {
  id: number
  title: string | null
  source_name: string
  source_type: string
  source_url: string
  document_date: string | null
  retrieved_at: string | null
  content_hash: string
  canonical_key: string | null
  raw_storage_path: string
  text_extracted: boolean
  extraction_status: string
  duplicate_of: number | null
}

export interface PaginatedDocuments {
  items: DocumentItem[]
  page: number
  page_size: number
  total: number
}

export interface DocumentDetail {
  id: number
  title: string | null
  source_name: string
  source_type: string
  source_url: string
  document_date: string | null
  retrieved_at: string | null
  content_hash: string
  canonical_key: string | null
  raw_storage_path: string
  mime_type: string | null
  file_size_bytes: number | null
  raw_metadata_json: Record<string, unknown> | null
  text_extracted: boolean
  extraction_status: string
  duplicate_of: number | null
  created_at: string | null
  updated_at: string | null
}

export interface DocumentText {
  document_id: number
  text_available: boolean
  block_count: number
  extracted_text: string
  extraction_status: string
}

export interface DocumentRaw {
  document_id: number
  storage_available: boolean
  raw_storage_path: string | null
  source_url: string
  download_url: string | null
  note: string
}

export interface IngestionRun {
  run_id: number
  source: string
  run_type: string | null
  status: string
  started_at: string | null
  completed_at: string | null
  records_found: number
  new_documents: number
  duplicates_skipped: number
  failed_documents: number
  date_range_start: string | null
  date_range_end: string | null
  error_message: string | null
}

export interface CoverageResponse {
  historical_backfill_status: string
  message: string
  total_documents: number
  total_documents_with_text: number
  sources_attempted: string[]
  date_ranges_attempted: { start: string; end: string }[]
  total_records_by_source: Record<string, number>
  last_successful_run: {
    id: number
    source: string
    status: string
    started_at: string | null
    completed_at: string | null
    records_found: number
    records_saved: number
  } | null
  coverage_snapshots: unknown[]
  coverage_snapshots_note?: string
  historical_backfill_details?: string
}

export interface BackfillPlanRequest {
  source: string
  start_date: string
  end_date: string
  max_pages: number
  dry_run: boolean
}

export interface BackfillPlanResponse {
  source: string
  start_date: string
  end_date: string
  max_pages: number
  dry_run: boolean
  planned_stages: string[]
  warning: string
}

export function getHealth(): Promise<HealthResponse> {
  return request('/health')
}

export function getStats(): Promise<StatsResponse> {
  return request('/stats')
}

export interface GetDocumentsParams {
  page?: number
  page_size?: number
  q?: string
  source_type?: string
  extraction_status?: string
  date_from?: string
  date_to?: string
}

export function getDocuments(params?: GetDocumentsParams): Promise<PaginatedDocuments> {
  const qp = new URLSearchParams()
  if (params) {
    if (params.page) qp.set('page', String(params.page))
    if (params.page_size) qp.set('page_size', String(params.page_size))
    if (params.q) qp.set('q', params.q)
    if (params.source_type) qp.set('source_type', params.source_type)
    if (params.extraction_status) qp.set('extraction_status', params.extraction_status)
    if (params.date_from) qp.set('date_from', params.date_from)
    if (params.date_to) qp.set('date_to', params.date_to)
  }
  const qs = qp.toString()
  return request(`/documents${qs ? `?${qs}` : ''}`)
}

export function getDocument(id: number): Promise<DocumentDetail> {
  return request(`/documents/${id}`)
}

export function getDocumentText(id: number): Promise<DocumentText> {
  return request(`/documents/${id}/text`)
}

export function getDocumentRaw(id: number): Promise<DocumentRaw> {
  return request(`/documents/${id}/raw`)
}

export function getIngestionRuns(): Promise<IngestionRun[]> {
  return request('/ingestion/runs')
}

export function getCoverage(): Promise<CoverageResponse> {
  return request('/coverage')
}

export function createBackfillPlan(payload: BackfillPlanRequest): Promise<BackfillPlanResponse> {
  return request('/backfill/plan', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}