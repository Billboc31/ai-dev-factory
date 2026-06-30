import { Link, useParams } from 'react-router-dom'
import ProjectRulesPanel from '../components/ProjectRulesPanel'

export default function ProjectRulesPage() {
  const { projectId } = useParams()
  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-2">Execution Rules</h1>
      <p className="text-sm text-gray-500 mb-6">
        Per-project policy gates (Human Approval, cost limits, …). Global runtime
        values (models, dispatcher mode, …) are in{' '}
        <Link to="/settings" className="text-blue-600 hover:text-blue-800 underline">
          Global Settings
        </Link>
        .
      </p>
      <ProjectRulesPanel projectId={projectId} />
    </div>
  )
}
