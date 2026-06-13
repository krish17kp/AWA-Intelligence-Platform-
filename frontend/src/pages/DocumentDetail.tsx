import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getDocument, getDocumentText, getDocumentRaw, type DocumentDetail, type DocumentText, type DocumentRaw } from '../api/client'
import StateMessage from '../components/StateMessage'

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [doc, setDoc] = useState<DocumentDetail | null>(null)
  const [text, setText] = useState<DocumentText | null>(null)
  const [raw, setRaw] = useState<DocumentRaw | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    const docId = Number(id)
    setLoading(true)
    setError(null)
    Promise.all([
      getDocument(docId),
      getDocumentText(docId),
      getDocumentRaw(docId),
    ])
      .then(([docData, textData, rawData]) => {
        setDoc(docData)
        setText(textData)
        setRaw(rawData)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Failed to load document')
      })
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <StateMessage type="loading" />
  if (error) return <StateMessage type="error" message={error} />
  if (!doc) return <StateMessage type="empty" message="Document not found." />

  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-6">{doc.title || 'Untitled Document'}</h2>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="space-y-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Details</h3>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-gray-500">Source Name</dt>
                <dd className="font-medium">{doc.source_name}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Source Type</dt>
                <dd className="font-medium">{doc.source_type}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Document Date</dt>
                <dd className="font-medium">{doc.document_date ? new Date(doc.document_date).toLocaleDateString() : '-'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Retrieved</dt>
                <dd className="font-medium">{doc.retrieved_at ? new Date(doc.retrieved_at).toLocaleString() : '-'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Source URL</dt>
                <dd className="font-medium">
                  <a href={doc.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline text-xs break-all">
                    {doc.source_url}
                  </a>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Canonical Key</dt>
                <dd className="font-medium text-xs font-mono">{doc.canonical_key || '-'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Content Hash</dt>
                <dd className="font-medium text-xs font-mono">{doc.content_hash}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">MIME Type</dt>
                <dd className="font-medium">{doc.mime_type || '-'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">File Size</dt>
                <dd className="font-medium">{doc.file_size_bytes ? `${(doc.file_size_bytes / 1024).toFixed(1)} KB` : '-'}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-gray-500">Extraction Status</dt>
                <dd>
                  <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                    doc.extraction_status === 'extracted' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {doc.extraction_status}
                  </span>
                </dd>
              </div>
            </dl>
          </div>

          {raw && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Raw Storage</h3>
              <dl className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-gray-500">Storage Available</dt>
                  <dd className="font-medium">{raw.storage_available ? 'Yes' : 'No'}</dd>
                </div>
                {raw.raw_storage_path && (
                  <div className="flex justify-between">
                    <dt className="text-gray-500">Storage Path</dt>
                    <dd className="font-medium text-xs font-mono">{raw.raw_storage_path}</dd>
                  </div>
                )}
              </dl>
              <p className="mt-2 text-xs text-gray-400">{raw.note}</p>
            </div>
          )}
        </div>

        <div className="space-y-4">
          {text && text.text_available && (
            <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Extracted Text ({text.block_count} blocks)
              </h3>
              <div className="max-h-96 overflow-y-auto bg-gray-50 rounded p-3 text-xs font-mono whitespace-pre-wrap border border-gray-100">
                {text.extracted_text}
              </div>
            </div>
          )}

          <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Metadata</h3>
            {doc.raw_metadata_json ? (
              <pre className="max-h-64 overflow-y-auto bg-gray-50 rounded p-3 text-xs font-mono whitespace-pre-wrap border border-gray-100">
                {JSON.stringify(doc.raw_metadata_json, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-gray-400">No metadata available.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}