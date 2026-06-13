import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Documents from './pages/Documents'
import DocumentDetail from './pages/DocumentDetail'
import Ingestion from './pages/Ingestion'
import Coverage from './pages/Coverage'
import FutureModules from './pages/FutureModules'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/documents/:id" element={<DocumentDetail />} />
        <Route path="/ingestion" element={<Ingestion />} />
        <Route path="/coverage" element={<Coverage />} />
        <Route path="/future-modules" element={<FutureModules />} />
      </Routes>
    </Layout>
  )
}