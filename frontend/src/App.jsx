import { useState, useEffect, useCallback, useRef } from 'react'
import { Kanban, ListDashes, Shapes } from '@phosphor-icons/react'
import KanbanBoard from './components/KanbanBoard'
import OrderForm from './components/OrderForm'
import ActivityLog from './components/ActivityLog'
import StatsBar from './components/StatsBar'
import Notifications from './components/Notifications'
import useWebSocket from './hooks/useWebSocket'
import axios from 'axios'

const API = '/api'

export default function App() {
  const [batches, setBatches] = useState([])
  const [refreshTrigger, setRefreshTrigger] = useState(0)
  const [notifications, setNotifications] = useState([])
  const [loading, setLoading] = useState(true)
  const [leftOpen, setLeftOpen] = useState(true)
  const [activeTab, setActiveTab] = useState('kanban') // 'kanban' | 'log'

  /* ── Notifications ─────────────────────────────────────────── */
  const addNotif = useCallback((type, title, message) => {
    const id = Date.now() + Math.random()
    setNotifications(p => [...p, { id, type, title, message }])
    setTimeout(() => setNotifications(p => p.filter(n => n.id !== id)), 5200)
  }, [])

  /* ── WebSocket ─────────────────────────────────────────────── */
  const { connected } = useWebSocket('/ws', useCallback((raw) => {
    try {
      const data = JSON.parse(raw)
      switch (data.type) {
        case 'BATCH_CREATED':
          setBatches(p => [data.batch, ...p.filter(b => b.id !== data.batch.id)])
          addNotif('success', `📦 Đơn mới: ${data.batch.order_code}`, data.batch.product_name)
          break
        case 'BATCH_ADVANCED':
          setBatches(p => p.map(b => b.id === data.batch.id ? data.batch : b))
          addNotif('info', `${data.batch.stage_emoji} ${data.batch.order_code}`, `→ ${data.stage_name}`)
          break
        case 'BATCH_ISSUE':
          setBatches(p => p.map(b => b.id === data.batch.id ? data.batch : b))
          addNotif('error', `🚨 Sự cố: ${data.batch.order_code}`, data.issue)
          break
        case 'BATCH_REWORKED':
          setRefreshTrigger(p => p + 1)
          break
      }
      if (data.type !== 'BATCH_REWORKED') {
          setRefreshTrigger(p => p + 1)
      }
    } catch { /* ignore */ }
  }, [addNotif]))



  useEffect(() => {
    const fetchBatches = async () => {
      try {
        const { data } = await axios.get(`${API}/batches`)
        setBatches(data)
      } catch { /* ignore */ } finally {
        setLoading(false)
      }
    }
    fetchBatches()
  }, [refreshTrigger])

  /* ── Actions ───────────────────────────────────────────────── */
  const handleCreateOrder = async (description, operator) => {
    const { data } = await axios.post(`${API}/orders`, { description, operator })
    return data
  }

  const handleAdvance = async (batchId, operator, note, expected_stage) => {
    try {
      await axios.post(`${API}/batches/${batchId}/advance`, { operator, note, expected_stage })
    } catch (e) {
      addNotif('error', 'Lỗi chuyển công đoạn', e.response?.data?.detail || e.message)
      throw e
    }
  }

  const handleIssue = async (batchId, issue, operator) => {
    try {
      await axios.post(`${API}/batches/${batchId}/issue`, { issue, operator })
    } catch (e) {
      addNotif('error', 'Lỗi báo sự cố', e.response?.data?.detail || e.message)
      throw e
    }
  }

  const handleRework = async (batchId, rework_qty, target_stage, operator, note, expected_stage) => {
    try {
      await axios.post(`${API}/batches/${batchId}/rework`, { rework_qty, target_stage, operator, note, expected_stage })
    } catch (e) {
      addNotif('error', 'Lỗi Tách mẻ/Rework', e.response?.data?.detail || e.message)
      throw e
    }
  }

  /* ── Stats ─────────────────────────────────────────────────── */
  const stats = {
    total:     batches.length,
    active:    batches.filter(b => b.status === 'ACTIVE').length,
    firing:    batches.filter(b => b.current_stage === 'FIRING').length,
    issues:    batches.filter(b => b.status === 'ISSUE').length,
    completed: batches.filter(b => b.status === 'COMPLETED').length,
  }

  return (
    <div className="app">

      {/* ── Header ── */}
      <header className="app-header">
        <div className="header-brand">
          <span className="header-logo"><Shapes size={24} weight="duotone" /></span>
          <div>
            <h1 className="header-title">GOM Pipeline</h1>
            <p className="header-sub">Hệ Thống Điều Phối Xưởng Gốm</p>
          </div>
        </div>

        <StatsBar stats={stats} />

        <div className="header-status">
          <span className={`ws-dot ${connected ? 'on' : 'off'}`} />
          <span className="ws-label">{connected ? 'Live' : 'Offline'}</span>
        </div>
      </header>

      {/* ── Body ── */}
      <div className="app-body">
        
        {/* Nav Sidebar */}
        <nav className="nav-sidebar">
          <button 
            className={`nav-item ${activeTab === 'kanban' ? 'active' : ''}`} 
            onClick={() => setActiveTab('kanban')}
            title="Bảng Công Đoạn"
          >
            <span className="nav-icon"><Kanban size={20} weight="bold" /></span>
            <span className="nav-text">Kanban</span>
          </button>
          
          <button 
            className={`nav-item ${activeTab === 'log' ? 'active' : ''}`} 
            onClick={() => setActiveTab('log')}
            title="Nhật Ký Hoạt Động"
          >
            <span className="nav-icon"><ListDashes size={20} weight="bold" /></span>
            <span className="nav-text">Nhật ký</span>
          </button>
        </nav>

        {/* Tab Content */}
        <div className="tab-content">
          {activeTab === 'kanban' ? (
            <>
              {/* Left sidebar */}
              <aside className={`sidebar sidebar-left ${leftOpen ? 'open' : ''}`}>
                <button className="toggle-btn left-toggle" onClick={() => setLeftOpen(v => !v)}
                  title={leftOpen ? 'Thu gọn' : 'Mở rộng'}>
                  {leftOpen ? '◀' : '▶'}
                </button>
                {leftOpen && (
                  <OrderForm onSubmit={handleCreateOrder} addNotif={addNotif} />
                )}
              </aside>

              {/* Kanban */}
              <main className="main-area">
                {loading
                  ? <div className="loading-center"><div className="spinner" /><p>Đang tải dữ liệu xưởng…</p></div>
                  : <KanbanBoard 
                      batches={batches} 
                      onAdvance={handleAdvance} 
                      onIssue={handleIssue} 
                      onRework={handleRework}
                    />
                }
              </main>
            </>
          ) : (
            <main className="main-area log-view-full">
              <ActivityLog refreshTrigger={refreshTrigger} />
            </main>
          )}
        </div>
      </div>

      {/* Notifications */}
      <Notifications notifications={notifications}
        onDismiss={(id) => setNotifications(p => p.filter(n => n.id !== id))} />
    </div>
  )
}
