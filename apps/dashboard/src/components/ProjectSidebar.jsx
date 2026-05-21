export default function ProjectSidebar({ projects, activeProject, onSelect }) {
  return (
    <aside className="w-48 bg-gray-800 text-white min-h-screen p-4 shrink-0">
      <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
        Projects
      </h2>
      <ul className="space-y-1">
        {projects.map(project => (
          <li key={project.name}>
            <button
              onClick={() => onSelect(project.name)}
              className={`w-full text-left px-3 py-2 rounded text-sm transition-colors ${
                project.name === activeProject
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700 hover:text-white'
              }`}
            >
              {project.name}
            </button>
          </li>
        ))}
      </ul>
    </aside>
  )
}
