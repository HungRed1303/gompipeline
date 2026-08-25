import { useState } from 'react'
import { PlusCircle, TextAlignLeft, User, PaperPlaneRight, Sparkle } from '@phosphor-icons/react'

const EXAMPLES = [
  'Đơn 200 Bình gốm họa tiết sen men lam cao 35cm, nung 1280°C, hoàn thành 10 ngày',
  '50 Tô gốm men trắng đường kính 20cm, nung 1200°C, giao trong 5 ngày',
  '100 Bình hoa trúc men nâu cao 40cm, nung nhiệt độ cao 1300°C, deadline 14 ngày',
  '30 Lọ gốm men ngọc họa tiết rồng cao 25cm, nung 1260°C, khẩn cấp 3 ngày',
]

export default function OrderForm({ onSubmit, addNotif }) {
  const [desc, setDesc]       = useState('')
  const [operator, setOp]     = useState('')
  const [loading, setLoading] = useState(false)
  const [preview, setPreview] = useState(null)

  const handleSubmit = async () => {
    if (!desc.trim()) return
    setLoading(true)
    try {
      await onSubmit(desc, operator || 'System')
      addNotif('success', `Đã nhận đơn hàng`, 'AI đang chạy ngầm để bóc tách...')
      setDesc('') // Clear immediately
    } catch (err) {
      addNotif('error', '❌ Lỗi tạo đơn', err?.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="order-form">
      <p className="form-title">
        <PlusCircle size={20} weight="bold" /> Tạo Đơn Hàng Mới
      </p>

      {/* Quick examples */}
      <div style={{ marginBottom: 14 }}>
        <p className="examples-label">Ví dụ nhanh</p>
        {EXAMPLES.map((ex, i) => (
          <button key={i} className="example-btn"
            onClick={() => { setDesc(ex); setPreview(null) }}>
            {ex}
          </button>
        ))}
      </div>

      <div className="form-group">
        <label className="form-label">
          <TextAlignLeft size={16} weight="bold" /> Mô tả đơn hàng
        </label>
        <textarea
          className="form-textarea"
          value={desc}
          onChange={e => { setDesc(e.target.value); setPreview(null) }}
          placeholder="Nhập số lượng, loại gốm, men, nhiệt độ, deadline…"
          rows={5}
        />
      </div>

      <div className="form-group">
        <label className="form-label">
          <User size={16} weight="bold" /> Người tạo đơn
        </label>
        <input className="form-input" type="text"
          placeholder="Tên quản lý / thợ…"
          value={operator} onChange={e => setOp(e.target.value)} />
      </div>

      <div className="form-actions">
        <button
          className="btn-ok-adv"
          onClick={handleSubmit}
          disabled={loading || !desc.trim()}
          style={{ width: '100%', display: 'flex', justifyContent: 'center', gap: 6, alignItems: 'center' }}
        >
          {loading ? <><span className="spinner-sm" style={{ borderTopColor: 'white' }} /> Đang gửi...</> : <><PaperPlaneRight size={18} weight="bold" /> Gửi yêu cầu</>}
        </button>
      </div>

      {/* AI specs preview */}
      {preview && (
        <div className="ai-preview">
          <p className="ai-preview-title"><Sparkle size={18} weight="fill" /> Kết quả AI bóc tách:</p>
          <div className="specs-grid">
            {[
              ['Số lượng',     preview.quantity     && `${preview.quantity} cái`],
              ['Nhiệt độ nung', preview.firing_temp_c && `${preview.firing_temp_c}°C`],
              ['Loại men',     preview.glaze_type],
              ['Họa tiết',     preview.pattern],
              ['Đất sét',      preview.clay_kg_estimate && `${preview.clay_kg_estimate} kg`],
              ['Deadline',     preview.deadline_days    && `${preview.deadline_days} ngày`],
            ].filter(([, v]) => v).map(([label, val]) => (
              <div key={label} className="spec-box">
                <p className="spec-box-label">{label}</p>
                <p className="spec-box-val">{val}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
