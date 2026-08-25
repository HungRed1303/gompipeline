import { useState, useEffect } from 'react'
import axios from 'axios'

const ACTION_META = {
  STARTED:   { emoji: '▶️', color: 'var(--cobalt-lt)', label: 'Bắt đầu' },
  COMPLETED: { emoji: '✅', color: 'var(--success)', label: 'Hoàn thành' },
  ISSUE:     { emoji: '🚨', color: 'var(--danger)', label: 'Báo sự cố' },
}

const STAGES = [
  { id: 'FORMING', name: 'Tạo hình mộc' },
  { id: 'DRYING', name: 'Phơi sấy & Sửa mộc' },
  { id: 'PAINTING', name: 'Vẽ họa tiết' },
  { id: 'GLAZING', name: 'Tráng men' },
  { id: 'FIRING', name: 'Vào lò nung' },
  { id: 'QC', name: 'Kiểm định & Đóng gói' },
  { id: 'COMPLETED', name: 'Hoàn thành' },
]

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleString('vi-VN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

export default function ActivityLog({ refreshTrigger }) {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(false)

  // Filters
  const [filterCode, setFilterCode] = useState('')
  const [filterStage, setFilterStage] = useState('')
  const [filterOperator, setFilterOperator] = useState('')

  useEffect(() => {
    const fetchFilteredLogs = async () => {
      setLoading(true)
      try {
        const params = {}
        if (filterCode) params.order_code = filterCode
        if (filterStage) params.stage = filterStage
        if (filterOperator) params.operator = filterOperator

        const { data } = await axios.get('/api/logs', { params })
        setLogs(data)
      } catch (err) {
        console.error("Failed to fetch logs", err)
      } finally {
        setLoading(false)
      }
    }

    fetchFilteredLogs()
    // Also set up polling just for this view
    const interval = setInterval(fetchFilteredLogs, 30000)
    return () => clearInterval(interval)
  }, [filterCode, filterStage, filterOperator, refreshTrigger])

  return (
    <div className="activity-log">
      <div className="log-header">
        <h2 className="log-title">📋 Nhật Ký Hoạt Động Xưởng</h2>
        
        {/* Filters Toolbar */}
        <div className="log-filters">
          <input 
            type="text" 
            className="filter-input" 
            placeholder="Mã đơn (VD: GOM)..." 
            value={filterCode}
            onChange={e => setFilterCode(e.target.value)}
          />
          <select 
            className="filter-select"
            value={filterStage}
            onChange={e => setFilterStage(e.target.value)}
          >
            <option value="">Tất cả công đoạn</option>
            {STAGES.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
          </select>
          <input 
            type="text" 
            className="filter-input" 
            placeholder="Người thao tác..." 
            value={filterOperator}
            onChange={e => setFilterOperator(e.target.value)}
          />
        </div>
      </div>

      <div className="log-table-wrap">
        {loading && logs.length === 0 ? (
          <div className="loading-center"><div className="spinner" /><p>Đang tải nhật ký…</p></div>
        ) : logs.length === 0 ? (
          <p className="log-empty">Không tìm thấy hoạt động nào phù hợp.</p>
        ) : (
          <table className="log-table">
            <thead>
              <tr>
                <th>Thời gian</th>
                <th>Mã Đơn</th>
                <th>Công Đoạn</th>
                <th>Thao Tác</th>
                <th>Người Nhập</th>
                <th>Ghi Chú</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => {
                const meta = ACTION_META[log.action] || ACTION_META.STARTED
                return (
                  <tr key={log.id} className={log.action === 'ISSUE' ? 'issue-row' : ''}>
                    <td className="col-time">{fmtTime(log.timestamp)}</td>
                    <td className="col-code">{log.order_code}</td>
                    <td className="col-stage">
                      <span className="stage-badge">{log.stage_emoji} {log.stage_name}</span>
                    </td>
                    <td className="col-action" style={{ color: meta.color }}>
                      {meta.emoji} {meta.label}
                    </td>
                    <td className="col-op">{log.operator}</td>
                    <td className="col-note" title={log.note}>{log.note}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
