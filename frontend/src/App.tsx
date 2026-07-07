import { Route, Routes } from 'react-router-dom'
import { useMarketSocket } from './hooks/useMarketSocket'
import { DashboardPage } from './pages/DashboardPage'
import { SettingsPage } from './pages/SettingsPage'

function App() {
  // Called once here, above the routes, so the WebSocket connection (and
  // the live store it feeds) survives navigation between pages instead of
  // disconnecting/reconnecting every time the route changes.
  useMarketSocket()

  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/settings" element={<SettingsPage />} />
    </Routes>
  )
}

export default App
