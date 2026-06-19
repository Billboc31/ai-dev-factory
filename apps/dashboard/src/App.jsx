import { useState, useEffect, createContext, useContext } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation, useParams } from 'react-router-dom'
import TicketDetailPage from './pages/TicketDetailPage'
import DaemonPage from './pages/DaemonPage'
import BoardPage from './pages/BoardPage'
import ProjectMapPage from './pages/ProjectMapPage'
import IssueMapperActivityPage from './pages/IssueMapperActivityPage'
import DeployerPage from './pages/DeployerPage'
import SandboxPanel from './components/SandboxPanel'
import AutoFixPanel from './components/AutoFixPanel'
import ProjectSidebar from './components/ProjectSidebar'
import RuntimeDashboardPage from './pages/RuntimeDashboardPage'
import EnvironmentsPage from './pages/EnvironmentsPage'
import ProjectsPage from './pages/ProjectsPage'
import ImportProjectPage from './pages/ImportProjectPage'
import ProjectDashboardPage from './pages/ProjectDashboardPage'
import ProjectTicketsPage from './pages/ProjectTicketsPage'
import ProjectWorktreesPage from './pages/ProjectWorktreesPage'
import ProjectLogsPage from './pages/ProjectLogsPage'
import ProjectAgentLayoutPage from './pages/ProjectAgentLayoutPage'
import useProjects from './hooks/useProjects'

export const ActiveProjectContext = createContext(null)

function SmartHomeRedirect() {
  const activeProject = useContext(ActiveProjectContext)
  if (activeProject) {
    return <Navigate to={`/projects/${activeProject}/tickets`} replace />
  }
  return <Navigate to="/projects" replace />
}

function ProjectDaemonPage() {
  const { projectId } = useParams()
  return <DaemonPage projectId={projectId} />
}

function AppLayout() {
  const { projects } = useProjects()
  const location = useLocation()
  const navigate = useNavigate()
  const [activeProject, setActiveProject] = useState(
    () => localStorage.getItem('activeProject') || null
  )

  useEffect(() => {
    const match = location.pathname.match(/^\/projects\/([^/]+)/)
    if (match) {
      const urlProjectId = match[1]
      if (urlProjectId !== activeProject) {
        setActiveProject(urlProjectId)
        localStorage.setItem('activeProject', urlProjectId)
      }
    }
  }, [location.pathname]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (projects.length > 0 && !activeProject) {
      const first = projects[0].name
      setActiveProject(first)
      localStorage.setItem('activeProject', first)
    }
  }, [projects]) // eslint-disable-line react-hooks/exhaustive-deps

  const handleSelectProject = (projectId) => {
    setActiveProject(projectId)
    localStorage.setItem('activeProject', projectId)
    navigate(`/projects/${projectId}/tickets`)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <ProjectSidebar
        projects={projects}
        activeProject={activeProject}
        onSelect={handleSelectProject}
      />
      <main className="flex-1 p-6 overflow-auto">
        <ActiveProjectContext.Provider value={activeProject}>
          <Routes>
            <Route path="/" element={<SmartHomeRedirect />} />
            <Route path="/projects" element={<ProjectsPage />} />
            <Route path="/import-project" element={<ImportProjectPage />} />
            <Route path="/projects/:projectId/dashboard" element={<ProjectDashboardPage />} />
            <Route path="/projects/:projectId/tickets" element={<ProjectTicketsPage />} />
            <Route path="/projects/:projectId/tickets/:id" element={<TicketDetailPage />} />
            <Route path="/projects/:projectId/worktrees" element={<ProjectWorktreesPage />} />
            <Route path="/projects/:projectId/logs" element={<ProjectLogsPage />} />
            <Route path="/projects/:projectId/daemon" element={<ProjectDaemonPage />} />
            <Route path="/projects/:projectId/agent-layout" element={<ProjectAgentLayoutPage />} />
            {/* Legacy routes not yet migrated to project-scoped URLs */}
            <Route path="/project-map" element={<ProjectMapPage projectId={activeProject} />} />
            <Route path="/mapper-activity" element={<IssueMapperActivityPage projectId={activeProject} />} />
            <Route path="/deployer" element={<DeployerPage projectId={activeProject} />} />
            <Route path="/sandboxes" element={<SandboxPanel />} />
            <Route path="/environments" element={<EnvironmentsPage projectId={activeProject} />} />
            <Route path="/auto-fix" element={<AutoFixPanel projectId={activeProject} />} />
            <Route path="/runtime-dashboard" element={<RuntimeDashboardPage />} />
            <Route path="/board" element={<BoardPage projectId={activeProject} />} />
          </Routes>
        </ActiveProjectContext.Provider>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  )
}
