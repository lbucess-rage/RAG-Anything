import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './components/Dashboard'
import QueryTester from './components/QueryTester'
import DocumentManager from './components/DocumentManager'
import ConsultationSimulator from './components/ConsultationSimulator'
import LogViewer from './components/LogViewer'
import Settings from './components/Settings'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="query" element={<QueryTester />} />
          <Route path="documents" element={<DocumentManager />} />
          <Route path="consultation" element={<ConsultationSimulator />} />
          <Route path="logs" element={<LogViewer />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
