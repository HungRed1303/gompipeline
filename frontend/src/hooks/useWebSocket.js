import { useState, useEffect, useRef } from 'react'

/**
 * useWebSocket — auto-reconnecting WebSocket hook.
 * @param {string} url  - WebSocket URL (relative /ws or absolute ws://...)
 * @param {Function} onMessage - callback(rawString) for each incoming message
 * @returns {{ connected: boolean }}
 */
export default function useWebSocket(url, onMessage) {
  const [connected, setConnected] = useState(false)
  const wsRef      = useRef(null)
  const retryRef   = useRef(null)
  const onMsgRef   = useRef(onMessage)

  // Keep callback ref fresh without re-triggering effect
  useEffect(() => { onMsgRef.current = onMessage }, [onMessage])

  useEffect(() => {
    // Resolve relative /ws to absolute ws:// URL
    const resolveUrl = () => {
      if (url.startsWith('ws')) return url
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
      return `${proto}://${window.location.host}${url}`
    }

    const connect = () => {
      const absUrl = resolveUrl()
      const ws = new WebSocket(absUrl)
      wsRef.current = ws

      ws.onopen = () => setConnected(true)

      ws.onmessage = (ev) => {
        try { onMsgRef.current(ev.data) } catch { /* ignore */ }
      }

      ws.onclose = () => {
        setConnected(false)
        retryRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = () => ws.close()
    }

    connect()

    return () => {
      clearTimeout(retryRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null   // prevent reconnect on unmount
        wsRef.current.close()
      }
    }
  }, [url]) // url is stable; onMessage is via ref

  return { connected }
}
