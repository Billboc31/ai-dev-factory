import { useEffect, useRef } from 'react'

export default function usePolling(callback, delay, key = undefined) {
  const savedCallback = useRef(callback)

  useEffect(() => {
    savedCallback.current = callback
  })

  useEffect(() => {
    if (delay == null) return undefined
    savedCallback.current()
    const id = setInterval(() => savedCallback.current(), delay)
    return () => clearInterval(id)
  }, [delay, key]) // eslint-disable-line react-hooks/exhaustive-deps
}
