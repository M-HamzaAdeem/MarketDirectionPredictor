import { DisclaimerBanner } from './components/dashboard/DisclaimerBanner'

function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <DisclaimerBanner />
      <main className="flex-1 flex items-center justify-center">
        <h1 className="text-2xl font-medium text-slate-300">
          Market Direction Predictor — dashboard coming in a later phase
        </h1>
      </main>
    </div>
  )
}

export default App
