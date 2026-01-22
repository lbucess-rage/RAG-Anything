import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Search,
  FileText,
  MessageSquare,
  ScrollText,
  Settings,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/query', icon: Search, label: 'Query Tester' },
  { to: '/documents', icon: FileText, label: 'Documents' },
  { to: '/consultation', icon: MessageSquare, label: 'Consultation' },
  { to: '/logs', icon: ScrollText, label: 'Log Viewer' },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export default function Sidebar({ open, onToggle }) {
  return (
    <aside
      className={cn(
        'flex flex-col bg-sidebar border-r border-sidebar-border transition-all duration-300',
        open ? 'w-64' : 'w-16'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between h-16 px-4 border-b border-sidebar-border">
        {open && (
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold text-sm">RA</span>
            </div>
            <span className="font-semibold text-sidebar-foreground">RAG-Anything</span>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggle}
          className="ml-auto"
        >
          {open ? <ChevronLeft className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-2 space-y-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors',
                'hover:bg-sidebar-accent hover:text-sidebar-accent-foreground',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-sidebar-foreground'
              )
            }
          >
            <Icon className="h-5 w-5 flex-shrink-0" />
            {open && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-sidebar-border">
        {open && (
          <div className="text-xs text-muted-foreground">
            <p>RAG-Anything API</p>
            <p>v1.0.0</p>
          </div>
        )}
      </div>
    </aside>
  )
}
