import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import {
  LayoutDashboard, Dumbbell, ClipboardCheck, LineChart,
  Camera, Settings, LogOut, Menu, X, Zap, ChevronRight
} from 'lucide-react'
import clsx from 'clsx'

const NAV = [
  { path: '/',         label: 'Dashboard',       icon: LayoutDashboard },
  { path: '/plan',     label: 'My Plan',          icon: Dumbbell        },
  { path: '/checkin',  label: 'Check-in',         icon: ClipboardCheck  },
  { path: '/history',  label: 'History',          icon: LineChart       },
  { path: '/photos',   label: 'Progress Photos',  icon: Camera          },
  { path: '/settings', label: 'Settings',         icon: Settings        },
]

function Logo() {
  return (
    <div className="flex items-center gap-2.5">
      <div className="w-8 h-8 rounded-xl bg-sage-500 flex items-center justify-center shadow-card">
        <Zap size={16} className="text-white" strokeWidth={2.5} />
      </div>
      <span className="font-display font-bold text-ink-900 text-lg tracking-tight">FitAgent</span>
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
      <Icon size={17} strokeWidth={active ? 2.5 : 2} />
      <span>{item.label}</span>
      {active && <ChevronRight size={14} className="ml-auto opacity-60" />}
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

  const sidebar = (
    <aside className="flex flex-col h-full bg-cream-200 border-r border-cream-400 w-64 flex-shrink-0">
      {/* Header */}
      <div className="px-5 pt-6 pb-4 border-b border-cream-400">
        <Logo />
        {/* User pill */}
        <div className="mt-4 flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-sage-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
            {initials}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-ink-800 truncate">{profile?.name ?? user?.username}</p>
            <p className="text-xs text-ink-400 capitalize truncate">{goal} · {profile?.fitness_level}</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1 overflow-y-auto">
        {NAV.map(item => (
          <NavItem
            key={item.path}
            item={item}
            active={pathname === item.path}
            onClick={() => handleNav(item.path)}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="px-3 pb-5 border-t border-cream-400 pt-3">
        <button
          onClick={handleLogout}
          className="nav-item nav-item-inactive w-full text-red-500 hover:bg-red-50 hover:text-red-600"
        >
          <LogOut size={17} strokeWidth={2} />
          <span>Log out</span>
        </button>
      </div>
    </aside>
  )

  return (
    <div className="min-h-screen flex bg-cream-100">
      {/* Desktop sidebar */}
      <div className="hidden md:flex">{sidebar}</div>

      {/* Mobile overlay */}
      {open && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={() => setOpen(false)} />
          <div className="relative flex">{sidebar}</div>
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Mobile top bar */}
        <div className="md:hidden flex items-center justify-between px-4 py-3 bg-cream-200 border-b border-cream-400">
          <Logo />
          <button onClick={() => setOpen(!open)} className="btn-ghost p-2">
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto px-4 md:px-8 py-6 page-enter">
          {children}
        </main>
      </div>
    </div>
  )
}
