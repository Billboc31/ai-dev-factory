export const COLUMN_DEFS = [
  { id: 'queued',        label: 'Queued',        color: 'bg-gray-50 border-gray-200' },
  { id: 'running',       label: 'Running',       color: 'bg-blue-50 border-blue-200' },
  { id: 'waiting_human', label: 'Waiting Human', color: 'bg-orange-50 border-orange-300' },
  { id: 'done',          label: 'Done',          color: 'bg-green-50 border-green-200' },
]

export const STATE_TO_COLUMN = {
  QUEUED:                           'queued',
  READY:                            'queued',
  PLANNED:                          'queued',
  PLAN_FIX_REQUIRED:                'queued',
  IMPLEMENTATION_FIX_REQUIRED:      'queued',

  RUNNING:                          'running',
  IMPLEMENTING:                     'running',
  TESTING:                          'running',
  REVIEWING:                        'running',
  PLAN_APPROVED:                    'running',
  IMPLEMENTATION_APPROVED:          'running',
  CONFLICT_RESOLVING:               'running',

  PLAN_REVIEW_NEEDED:               'waiting_human',
  IMPLEMENTATION_REVIEW_NEEDED:     'waiting_human',
  CONFLICT_RESOLUTION_NEEDED:       'waiting_human',
  CONFLICT_RESOLVED_REVIEW_NEEDED:  'waiting_human',

  TEST_COMPLETE:                    'done',
  COMPLETE:                         'done',
  COMPLETED:                        'done',
  MERGED:                           'done',
  ARCHIVED:                         'done',
  FAILED:                           'done',
  CONFLICT_RESOLUTION_FAILED:       'done',
}

export function columnForState(state) {
  return STATE_TO_COLUMN[state] ?? 'queued'
}

export const STATE_BADGE_COLORS = {
  COMPLETE:                         'bg-green-100 text-green-800',
  TEST_COMPLETE:                    'bg-green-100 text-green-800',
  PLAN_REVIEW_NEEDED:               'bg-orange-100 text-orange-800 ring-1 ring-orange-300',
  IMPLEMENTATION_REVIEW_NEEDED:     'bg-orange-100 text-orange-800 ring-1 ring-orange-300',
  PLAN_FIX_REQUIRED:                'bg-orange-50 text-orange-700',
  IMPLEMENTATION_FIX_REQUIRED:      'bg-orange-50 text-orange-700',
  PLAN_APPROVED:                    'bg-blue-100 text-blue-800',
  IMPLEMENTATION_APPROVED:          'bg-blue-100 text-blue-800',
  RUNNING:                          'bg-yellow-100 text-yellow-800',
  FAILED:                           'bg-red-100 text-red-800',
  CONFLICT_RESOLUTION_NEEDED:       'bg-red-100 text-red-800',
  CONFLICT_RESOLVING:               'bg-yellow-100 text-yellow-800',
  CONFLICT_RESOLVED_REVIEW_NEEDED:  'bg-blue-100 text-blue-800',
  CONFLICT_RESOLUTION_FAILED:       'bg-red-200 text-red-900',
}

export function stateBadgeClass(state) {
  if (STATE_BADGE_COLORS[state]) return STATE_BADGE_COLORS[state]
  const match = Object.entries(STATE_BADGE_COLORS).find(([k]) => state?.includes(k))
  return match ? match[1] : 'bg-gray-100 text-gray-700'
}
