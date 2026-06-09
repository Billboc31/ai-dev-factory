import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import ProjectSidebar from '../src/components/ProjectSidebar'

const PROJECTS = [
  { name: 'project-alpha' },
  { name: 'project-beta' },
]

function renderSidebar({ projects = PROJECTS, activeProject = null, onSelect = vi.fn() } = {}) {
  return render(
    <MemoryRouter>
      <ProjectSidebar projects={projects} activeProject={activeProject} onSelect={onSelect} />
    </MemoryRouter>
  )
}

describe('ProjectSidebar', () => {
  it('renders all project names', () => {
    renderSidebar()
    expect(screen.getByRole('button', { name: 'project-alpha' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'project-beta' })).toBeInTheDocument()
  })

  it('calls onSelect with the project name when a project button is clicked', async () => {
    const onSelect = vi.fn()
    renderSidebar({ onSelect })
    await userEvent.click(screen.getByRole('button', { name: 'project-alpha' }))
    expect(onSelect).toHaveBeenCalledWith('project-alpha')
  })

  it('shows per-project nav links when activeProject is set', () => {
    renderSidebar({ activeProject: 'project-alpha' })
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Tickets' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Worktrees' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Logs' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Daemon' })).toBeInTheDocument()
  })

  it('does not show per-project nav links when no activeProject is set', () => {
    renderSidebar({ activeProject: null })
    expect(screen.queryByRole('link', { name: 'Dashboard' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Tickets' })).not.toBeInTheDocument()
  })

  it('per-project nav links point to the active project routes', () => {
    renderSidebar({ activeProject: 'project-alpha' })
    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute(
      'href',
      '/projects/project-alpha/dashboard'
    )
    expect(screen.getByRole('link', { name: 'Tickets' })).toHaveAttribute(
      'href',
      '/projects/project-alpha/tickets'
    )
  })

  it('renders global nav links (Runtime, Environments, Sandboxes)', () => {
    renderSidebar()
    expect(screen.getByRole('link', { name: 'Runtime' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Environments' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Sandboxes' })).toBeInTheDocument()
  })

  it('renders the import project + link', () => {
    renderSidebar()
    expect(screen.getByTitle('Import project')).toBeInTheDocument()
  })
})
