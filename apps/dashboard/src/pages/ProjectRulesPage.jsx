import { useParams } from 'react-router-dom'
import ProjectRulesPanel from '../components/ProjectRulesPanel'

export default function ProjectRulesPage() {
  const { projectId } = useParams()
  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">Project Rules</h1>
      <ProjectRulesPanel projectId={projectId} />
    </div>
  )
}
