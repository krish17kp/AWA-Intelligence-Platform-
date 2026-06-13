const modules = [
  { name: 'OCR + QA Queue', description: 'Optical character recognition for scanned documents and human review queue for quality assurance.' },
  { name: 'Entity Extraction', description: 'Automated extraction of facilities, inspectors, and regulated entities from documents.' },
  { name: 'Facility Profiles', description: 'Searchable profiles with inspection history, enforcement actions, and license status.' },
  { name: 'Inspector Analytics', description: 'Trend analysis and performance metrics for inspectors and inspection programs.' },
  { name: 'AI Research Assistant', description: 'Natural language query interface over the full document corpus.' },
  { name: 'Case / Evidence Binder', description: 'Organize documents, extracts, and annotations into structured case files.' },
  { name: 'FOIA', description: 'Freedom of Information Act request tracking and response management.' },
  { name: 'Public Portal', description: 'Public-facing interface for transparency and stakeholder access.' },
  { name: 'Graph Intelligence', description: 'Relationship mapping across entities, facilities, and enforcement actions.' },
]

export default function FutureModules() {
  return (
    <div>
      <h2 className="text-xl font-semibold text-gray-800 mb-2">Future Modules</h2>
      <p className="text-sm text-gray-500 mb-6">These modules are planned but not yet implemented.</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {modules.map((mod) => (
          <div
            key={mod.name}
            className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm opacity-60"
          >
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-gray-700">{mod.name}</h3>
              <span className="px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-500">
                Planned
              </span>
            </div>
            <p className="text-xs text-gray-500">{mod.description}</p>
          </div>
        ))}
      </div>
    </div>
  )
}