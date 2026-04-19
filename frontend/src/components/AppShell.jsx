import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  LayoutDashboard, Dumbbell, ClipboardCheck, LineChart,
  Images, Settings, LogOut, Menu, X
} from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { path: '/',         label: 'Overview',   icon: LayoutDashboard, section: 'main' },
  { path: '/plan',     label: 'Plan',       icon: Dumbbell,        section: 'main' },
  { path: '/checkin',  label: 'Check-in',   icon: ClipboardCheck,  section: 'main' },
  { path: '/history',  label: 'History',    icon: LineChart,       section: 'main' },
  { path: '/photos',   label: 'Photos',     icon: Images,          section: 'main' },
  { path: '/settings', label: 'Settings',   icon: Settings,        section: 'secondary' },
]

export function Mark({ size = 28 }) {
  // Custom mark — layered F / forward arrow, sage+clay, scales cleanly
  return (
    <svg width={size} height={size} viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="1" y="1" width="38" height="38" rx="9" fill="#1C1A14" />
      <path d="M12 11H28V15H16V19H26V23H16V29H12V11Z" fill="#FAF7EE" />
      <circle cx="30.5" cy="28.5" r="2.5" fill="#B94A1E" />
    </svg>
  )
}

export function Wordmark({ size = 28 }) {
  return (
    <div className="flex items-center gap-2.5">
      <Mark size={size} />
      <div className="flex flex-col leading-none">
        <span className="font-display font-bold text-ink-900 text-[17px] tracking-tight">
          FitAgent
        </span>
        <span className="text-[9px] font-mono uppercase text-ink-400 tnum mt-0.5" style={{ letterSpacing: '0.18em' }}>
          Evidence · Agents · You
        </span>
      </div>
    </div>
  )
}

function NavItem({ item, active, onClick }) {
  const Icon = item.icon
  return (
    <button
      onClick={onClick}
      className={clsx('nav-item', active ? 'nav-item-active' : 'nav-item-inactive')}
    >
      <Icon size={15} strokeWidth={active ? 2.25 : 1.75} />
      <span>{item.label}</span>
    </button>
  )
}

export default function AppShell({ children }) {
  const { user, profile, logout } = useAuth()
  const navigate  = useNavigate()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)

  const goal = profile?.goal?.replace('_', ' ') ?? ''
  const initials = (profile?.name ?? user?.username ?? 'U')
    .split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)

  function handleNav(path) {
    navigate(path)
    setOpen(false)
  }

  async function handleLogout() {
    await logout()
    navigate('/login')
  }

  const mainNav      = NAV.filter(n => n.section === 'main')
  const secondaryNav = NAV.filter(n => n.section === 'secondary')

  const sidebar = (
    <aside className="flex flex-col h-full bg-paper-100 hair-r w-64 flex-shrink-0">
      {/* Brand */}
      <div className="px-5 pt-6 pb-5 hair-b">
        <Wordmark />
      </div>

      {/* User pill */}
      <div className="px-4 py-4 hair-b">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-lg bg-ink-800 text-paper-50 flex items-center justify-center text-[11px] font-display font-bold shadow-card">
              {initials}
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-sage-500 border-2 border-paper-100" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[13px] font-semibold text-ink-800 truncate">
              {profile?.name ?? user?.username}
            </p>
            <p className="text-[11px] text-ink-400 capitalize truncate">
              {goal || 'onboarding'} · {profile?.fitness_level ?? '—'}
            </p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 overflow-y-auto">
        <p className="eyebrow px-3 mb-2">Workspace</p>
        <div className="flex flex-col gap-0.5">
          {mainNav.map(item => (
            <NavItem
              key={item.path}
              item={item}
              active={pathname === item.path}
              onClick={() => handleNav(item.path)}
            />
          ))}
        </div>

        <p className="eyebrow px-3 mb-2 mt-6">Account</p>
        <div className="flex flex-col gap-0.5">
          {secondaryNav.map(item => (
            <NavItem
              key={item.path}
              item={item}
              active={pathname === item.path}
              onClick={() => handleNav(item.path)}
            />
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-3 py-3 hair-t">
        <button onClick={handleLogout} className="nav-item nav-item-inactive w-full">
          <LogOut size={15} strokeWidth={1.75} />
          <span>Sign out</span>
        </button>
      </div>
    </aside>
  )

  return (
    <div className="min-h-screen flex">
      {/* Desktop sidebar */}
      <div className="hidden md:flex">{sidebar}</div>

      {/* Mobile overlay */}
      {open && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="absolute inset-0 bg-ink-900/30 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative flex">{sidebar}</div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Mobile top bar */}
        <div className="md:hidden flex items-center justify-between px-4 py-3 bg-paper-100 hair-b">
          <Wordmark size={24} />
          <button onClick={() => setOpen(!open)} className="btn-ghost p-2">
            {open ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto page-enter">
          {children}
        </main>
      </div>
    </div>
  )
}
