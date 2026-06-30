import { NavLink } from 'react-router-dom'

const PROJECT_NAV = [
  { label: 'Tickets', path: 'tickets' },
  { label: 'Dashboard', path: 'dashboard' },
  { label: 'Dispatcher', path: 'dispatcher' },
  { label: 'Batches', path: 'dispatcher/batches' },
  { label: 'Execution Rules', path: 'rules' },
  { label: 'Worktrees', path: 'worktrees' },
  { label: 'Logs', path: 'logs' },
  { label: 'Daemon', path: 'daemon' },
  { label: 'Agent Layout', path: 'agent-layout' },
]

const GLOBAL_NAV = [
  { label: 'Runtime', to: '/runtime-dashboard' },
  { label: 'Environments', to: '/environments' },
  { label: 'Sandboxes', to: '/sandboxes' },
  { label: 'Global Settings', to: '/settings' },
]

const navItemClass = ({ isActive }) =>
  `block px-3 py-1.5 rounded text-sm transition-colors ${
    isActive
      ? 'bg-gray-700 text-white font-medium'
      : 'text-gray-300 hover:bg-gray-700 hover:text-white'
  }`

export default function ProjectSidebar({ projects, activeProject, onSelect }) {
  return (
    <aside className="w-56 bg-gray-800 text-white min-h-screen flex flex-col shrink-0">
      <div className="px-4 py-4 border-b border-gray-700">
        <NavLink to="/projects" className="text-sm font-bold text-white hover:text-gray-200">
          AI Dev Factory
        </NavLink>
      </div>

      <div className="px-4 py-3 border-b border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
            Projects
          </span>
          <NavLink
            to="/import-project"
            className="text-gray-400 hover:text-white text-lg leading-none"
            title="Import project"
          >
            +
          </NavLink>
        </div>
        <ul className="space-y-0.5">
          {projects.map(project => (
            <li key={project.name}>
              <button
                onClick={() => onSelect(project.name)}
                className={`w-full text-left px-3 py-1.5 rounded text-sm transition-colors ${
                  project.name === activeProject
                    ? 'bg-blue-600 text-white font-medium'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`}
              >
                {project.name}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {activeProject && (
        <div className="px-4 py-3 border-b border-gray-700">
          <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 truncate" title={activeProject}>
            {activeProject}
          </p>
          <ul className="space-y-0.5">
            {PROJECT_NAV.map(({ label, path }) => (
              <li key={path}>
                <NavLink
                  to={`/projects/${activeProject}/${path}`}
                  className={navItemClass}
                >
                  {label}
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="px-4 py-3 mt-auto border-t border-gray-700">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
          Global
        </p>
        <ul className="space-y-0.5">
          {GLOBAL_NAV.map(({ label, to }) => (
            <li key={to}>
              <NavLink to={to} className={navItemClass}>
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  )
}
