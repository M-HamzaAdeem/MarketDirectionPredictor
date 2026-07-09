import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { DisclaimerBanner } from '../dashboard/DisclaimerBanner'
import { FeedStatusIndicator } from '../dashboard/FeedStatusIndicator'
import { SourceToggle } from '../dashboard/SourceToggle'

const NAV_LINK_BASE_CLASS = 'rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-400'

const NAV_LINK_CLASS = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? `${NAV_LINK_BASE_CLASS} font-semibold text-slate-100 underline underline-offset-4`
    : `${NAV_LINK_BASE_CLASS} text-slate-400 hover:text-slate-200`

interface AppShellProps {
  children: ReactNode
}

export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <DisclaimerBanner />

      <header className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
        <div className="flex items-center gap-6">
          <h1 className="text-lg font-semibold">Market Direction Predictor</h1>
          <nav className="flex items-center gap-4 text-sm">
            <NavLink to="/" end className={NAV_LINK_CLASS}>
              Dashboard
            </NavLink>
            <NavLink to="/settings" className={NAV_LINK_CLASS}>
              Settings
            </NavLink>
          </nav>
        </div>
        <div className="flex items-center gap-4">
          <SourceToggle />
          <FeedStatusIndicator />
        </div>
      </header>

      <main className="flex-1 space-y-8 px-6 py-6">{children}</main>
    </div>
  )
}
