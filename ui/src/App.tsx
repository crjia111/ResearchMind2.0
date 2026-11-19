import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ChatPage from './pages/ChatPage'
import SettingsPage from './pages/SettingsPage'
import DiagnosticPage from './pages/DiagnosticPage'
import StorageValidator from './components/StorageValidator'
import { useAutoSave } from './hooks/useAutoSave'

const routerFutureFlags = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
} as const

function App() {
  useAutoSave(30000)

  return (
    <StorageValidator>
      <div className="min-h-screen bg-transparent">
        <Router future={routerFutureFlags}>
          <Routes>
            <Route path="/diagnostic" element={<DiagnosticPage />} />
            <Route path="/" element={<Layout><ChatPage /></Layout>} />
            <Route path="/settings" element={<Layout><SettingsPage /></Layout>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
      </div>
    </StorageValidator>
  )
}

export default App
