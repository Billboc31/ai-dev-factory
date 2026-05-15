import { renderHook } from '@testing-library/react'
import usePolling from '../src/hooks/usePolling'

describe('usePolling', () => {
  beforeEach(() => { vi.useFakeTimers() })
  afterEach(() => { vi.useRealTimers() })

  it('calls callback immediately on mount', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 5000))
    expect(callback).toHaveBeenCalledTimes(1)
  })

  it('calls callback again after delay', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 5000))
    vi.advanceTimersByTime(5000)
    expect(callback).toHaveBeenCalledTimes(2)
  })

  it('calls callback for each elapsed interval', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, 1000))
    vi.advanceTimersByTime(3000)
    expect(callback).toHaveBeenCalledTimes(4) // 1 immediate + 3 intervals
  })

  it('clears interval on unmount — no zombie polling', () => {
    const callback = vi.fn()
    const { unmount } = renderHook(() => usePolling(callback, 1000))
    unmount()
    vi.advanceTimersByTime(10000)
    expect(callback).toHaveBeenCalledTimes(1) // only the immediate mount call
  })

  it('does not poll when delay is null', () => {
    const callback = vi.fn()
    renderHook(() => usePolling(callback, null))
    vi.advanceTimersByTime(10000)
    expect(callback).not.toHaveBeenCalled()
  })

  it('restarts interval and calls immediately when key changes', () => {
    const callback = vi.fn()
    const { rerender } = renderHook(({ key }) => usePolling(callback, 2000, key), {
      initialProps: { key: 'a' }
    })
    expect(callback).toHaveBeenCalledTimes(1)

    rerender({ key: 'b' })
    expect(callback).toHaveBeenCalledTimes(2) // immediate call after key change

    vi.advanceTimersByTime(2000)
    expect(callback).toHaveBeenCalledTimes(3)
  })

  it('does not restart interval when callback identity changes', () => {
    const spy = vi.fn()
    let callCount = 0
    const { rerender } = renderHook(({ cb }) => usePolling(cb, 1000), {
      initialProps: { cb: () => spy(++callCount) }
    })
    expect(spy).toHaveBeenCalledTimes(1)

    rerender({ cb: () => spy(++callCount) }) // new function identity, same delay, no key
    // No extra immediate call — interval continues unchanged
    expect(spy).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(1000)
    expect(spy).toHaveBeenCalledTimes(2) // interval fires once
  })
})
