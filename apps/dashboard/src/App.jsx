import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import TicketsPage from './pages/TicketsPage'
import TicketDetailPage from './pages/TicketDetailPage'
import DaemonPage from './pages/DaemonPage'
import BoardPage from './pages/BoardPage'
import ProjectMapPage from './pages/ProjectMapPage'
import IssueMapperActivityPage from './pages/IssueMapperActivityPage'
import ProjectSidebar from './components/ProjectSidebar'
import useProjects from './hooks/useProjects'

function Nav({ activeProject }) {
  const linkClass = ({ isActive }) =>
    isActive ? 'text-blue-300 font-medium' : 'text-gray-300 hover:text-white'

  return (
    <nav className="bg-gray-900 text-white px-6 py-3 flex items-center gap-6">
      <span className="font-bold text-lg mr-2">{activeProject}</span>
      <NavLink to="/" className={linkClass} end>Tickets</NavLink>
      <NavLink to="/daemon" className={linkClass}>Daemon</NavLink>
      <NavLink to="/board" className={linkClass}>Board</NavLink>
      <NavLink to="/project-map" className={linkClass}>Project Map</NavLink>
      <NavLink to="/mapper-activity" className={linkClass}>Mapper Activity</NavLink>
    </nav>
  )
}

export default function App() {
  const { projects } = useProjects()
  const [activeProject, setActiveProject] = useState(null)

  useEffect(() => {
    if (projects.length > 0 && activeProject === null) {
      setActiveProject(projects[0].name)
    }
  }, [projects]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Nav activeProject={activeProject ?? 'ai-dev-factory'} />
        <div className="flex">
          <ProjectSidebar
            projects={projects}
            activeProject={activeProject}
            onSelect={setActiveProject}
          />
          <main className="p-6 flex-1">
            <Routes>
              <Route path="/" element={<TicketsPage />} />
              <Route path="/tickets/:id" element={<TicketDetailPage />} />
              <Route path="/daemon" element={<DaemonPage />} />
              <Route path="/board" element={<BoardPage />} />
              <Route path="/project-map" element={<ProjectMapPage />} />
              <Route path="/mapper-activity" element={<IssueMapperActivityPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  )
}
