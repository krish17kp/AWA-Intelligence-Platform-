import { NavLink } from 'react-router-dom'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/documents', label: 'Documents' },
  { to: '/ingestion', label: 'Ingestion' },
  { to: '/coverage', label: 'Coverage' },
  { to: '/future-modules', label: 'Future Modules' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      <aside className="w-56 bg-white border-r border-gray-200 flex-shrink-0 flex flex-col">
        <div className="px-5 py-4 border-b border-gray-200">
          <h1 className="text-sm font-semibold text-gray-800 uppercase tracking-wide">
            AWA Intelligence
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">Platform</p>
        </div>
        <nav className="flex-1 px-3 py-4 space-y-1">
          {links.map((link) => (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-3 border-t border-gray-200 text-xs text-gray-400">
          v0.1.0
        </div>
      </aside>
      <main className="flex-1 overflow-auto">
        <header className="bg-white border-b border-gray-200 px-6 py-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-800">
              AWA Intelligence Platform
            </h2>
          </div>
        </header>
        <div className="p-6">{children}</div>
      </main>
    </div>
  )
}