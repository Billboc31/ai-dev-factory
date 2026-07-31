import { useState, useEffect, useCallback } from 'react'

const STORAGE_KEY = 'workspace_layout'
const MIN_WIDTH = 280
const MIN_HEIGHT = 400

function getMaxDimensions(mode) {
  const vw = window.innerWidth
  const vh = window.innerHeight
  if (mode === 'floating') {
    return { maxWidth: Math.min(900, vw - 48), maxHeight: vh - 48 }
  }
  return { maxWidth: Math.min(800, vw - 320), maxHeight: vh }
}

function clampLayout(layout) {
  const vw = window.innerWidth
  const vh = window.innerHeight
  const { maxWidth, maxHeight } = getMaxDimensions(layout.mode)
  const width = Math.max(MIN_WIDTH, Math.min(maxWidth, layout.width || 320))
  const height = Math.max(MIN_HEIGHT, Math.min(maxHeight, layout.height || 600))
  if (layout.mode !== 'floating') return { ...layout, width, height }
  const x = Math.max(0, Math.min(vw - width, layout.x ?? Math.round((vw - width) / 2)))
  const y = Math.max(0, Math.min(vh - height, layout.y ?? Math.round((vh - height) / 2)))
  return { ...layout, width, height, x, y }
}

function defaultLayout() {
  const width = 320
  const height = 600
  return {
    mode: 'floating',
    width,
    height,
    x: Math.max(0, Math.round((window.innerWidth - width) / 2)),
    y: Math.max(0, Math.round((window.innerHeight - height) / 2)),
  }
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function saveToStorage(layout) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(layout))
  } catch {}
}

export default function useWorkspaceLayout() {
  const [layout, setLayout] = useState(() => {
    const stored = loadFromStorage()
    return clampLayout(stored ?? defaultLayout())
  })

  useEffect(() => {
    saveToStorage(layout)
  }, [layout])

  useEffect(() => {
    const onResize = () => setLayout(prev => clampLayout(prev))
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const setMode = useCallback(mode => setLayout(prev => clampLayout({ ...prev, mode })), [])
  const setPosition = useCallback(({ x, y }) => setLayout(prev => ({ ...prev, x, y })), [])
  const setSize = useCallback(({ width, height }) => setLayout(prev => ({ ...prev, width, height })), [])

  return { layout, setMode, setPosition, setSize }
}
