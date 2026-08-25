import { useState } from 'react'
import { 
  Thermometer, CalendarBlank, Sparkle, PaintBrush, 
  Wall, Hash, Warning, ArrowsClockwise, CaretRight, 
  CheckCircle, ArrowBendUpLeft
} from '@phosphor-icons/react'

const PRIO = {
  1: { label: 'Khẩn cấp', color: '#c44e1a' },
  2: { label: 'Bình thường', color: '#2e6ba8' },
  3: { label: 'Thấp',   color: '#4a4a4a' },
}

const STAGES = [
  { id: 'FORMING', name: 'Tạo Hình Mộc' },
  { id: 'DRYING', name: 'Phơi Sấy & Sửa' },
  { id: 'PAINTING', name: 'Vẽ Họa Tiết' },
  { id: 'GLAZING', name: 'Tráng Men' },
  { id: 'FIRING', name: 'Nung' },
  { id: 'QC', name: 'Kiểm Tra (QC)' },
  { id: 'COMPLETED', name: 'Hoàn Thành' },
]

export default function BatchCard({ batch, stageColor, onAdvance, onIssue, onRework }) {
  const [modal, setModal]     = useState(null)   // null | 'advance' | 'issue' | 'rework'
  const [operator, setOp]     = useState('')
  const [note, setNote]       = useState('')
  const [loading, setLoading] = useState(false)
  const [reworkQty, setReworkQty] = useState(batch?.quantity || 1)
  const [targetStage, setTargetStage] = useState('')

  const prio    = PRIO[batch.priority] || PRIO[2]
  const specs   = batch.specs || {}
  const isIssue = batch.status === 'ISSUE'
  const isDone  = batch.status === 'COMPLETED'

  const currentStageIdx = STAGES.findIndex(s => s.id === batch.current_stage)
  const prevStages = currentStageIdx > 0 ? STAGES.slice(0, currentStageIdx) : []

  const open = (type) => { setModal(type); setNote(''); }
  const close = () => setModal(null)

  const handleOk = async () => {
    setLoading(true)
    try {
      if (modal === 'advance') {
        await onAdvance(batch.id, operator || 'Không rõ', note, batch.current_stage)
      } else if (modal === 'issue') {
        await onIssue(batch.id, note || 'Sự cố không xác định', operator || 'Không rõ')
      } else if (modal === 'rework') {
        await onRework(batch.id, reworkQty, targetStage, operator || 'Không rõ', note, batch.current_stage)
      }
      close()
    } catch { /* error handled in App */ }
    finally { setLoading(false) }
  }

  return (
    <>
      <div className={`b-card${isIssue ? ' issue' : ''}`}>
        <div className="card-body">
          <div className="card-top">
            <span className="order-code">{batch.order_code}</span>
            <span className="prio-badge" style={{ backgroundColor: prio.color }}>
              {prio.label}
            </span>
          </div>

          <p className="product-name">{batch.product_name}</p>
          
          {batch.status === 'PENDING_PARSING' ? (
            <div className="parsing-state" style={{ marginTop: 12, display: 'flex', alignItems: 'center', gap: 8, color: 'var(--info)' }}>
              <span className="spinner-sm" style={{ borderTopColor: 'var(--info)' }}></span>
              <span style={{ fontSize: '0.8rem', fontWeight: 500 }}>AI đang bóc tách dữ liệu...</span>
            </div>
          ) : (
            <>
              <p className="qty-row">
                <Hash size={16} weight="bold" /> {batch.quantity.toLocaleString('vi-VN')} cái
              </p>

              {isIssue && <span className="issue-flag"><Warning size={16} weight="fill" /> Đang có sự cố</span>}

              <div className="specs-grid">
                {specs.rework_count > 0 && (
                  <div className="spec-item col-full rework-chip">
                    <ArrowsClockwise size={16} weight="bold" /> Rework {specs.rework_count}
                  </div>
                )}
                {specs.firing_temp_c && (
                  <div className="spec-item">
                    <Thermometer size={16} /> <span>{specs.firing_temp_c}°C</span>
                  </div>
                )}
                {specs.deadline_days && (
                  <div className="spec-item">
                    <CalendarBlank size={16} /> <span>{specs.deadline_days}d</span>
                  </div>
                )}
                {specs.glaze_type && (
                  <div className="spec-item">
                    <Sparkle size={16} /> <span>{specs.glaze_type}</span>
                  </div>
                )}
                {specs.pattern && (
                  <div className="spec-item">
                    <PaintBrush size={16} /> <span>{specs.pattern}</span>
                  </div>
                )}
                {specs.clay_kg_estimate && (
                  <div className="spec-item">
                    <Wall size={16} /> <span>{specs.clay_kg_estimate}kg</span>
                  </div>
                )}
              </div>

              <p className="card-date">
                {batch.created_at
                  ? new Date(batch.created_at).toLocaleDateString('vi-VN', { day:'2-digit', month:'2-digit' })
                  : '—'}
              </p>
            </>
          )}
        </div>

        {!isDone && batch.status !== 'PENDING_PARSING' && (
          <div className="card-actions">
            <button className="btn-adv" onClick={() => open('advance')}>
              <CaretRight size={16} weight="bold" /> Chuyển công đoạn
            </button>
            {prevStages.length > 0 && (
              <button className="btn-iss btn-rework" title="Tách mẻ / Rework" 
                onClick={() => { setTargetStage(prevStages[prevStages.length-1].id); setReworkQty(batch.quantity); open('rework'); }}>
                <ArrowBendUpLeft size={16} weight="bold" />
              </button>
            )}
            <button className="btn-iss" title="Báo sự cố" onClick={() => open('issue')}>
              <Warning size={16} weight="bold" />
            </button>
          </div>
        )}
      </div>

      {/* Modal */}
      {modal && (
        <div className="modal-bg" onClick={close}>
          <div className="modal-box" onClick={e => e.stopPropagation()}>
            <p className="modal-title">
              {modal === 'advance' ? 'Xác nhận chuyển công đoạn' : modal === 'issue' ? 'Báo sự cố' : 'Tách mẻ / Rework'}
            </p>
            <p className="modal-sub">{batch.order_code} — {batch.product_name}</p>

            {modal === 'rework' && (
              <>
                <label className="modal-label">Số lượng lỗi / cần quay lại</label>
                <input className="modal-input" type="number" min={1} max={batch.quantity}
                  value={reworkQty} onChange={e => setReworkQty(Number(e.target.value))} />

                <label className="modal-label">Quay lại công đoạn</label>
                <select className="modal-input" value={targetStage} onChange={e => setTargetStage(e.target.value)}>
                  {prevStages.map(s => (
                    <option key={s.id} value={s.id}>{s.name}</option>
                  ))}
                </select>
                {specs.rework_count > 0 && (
                  <p style={{color: '#c44e1a', fontSize: '0.85rem', marginTop: 4}}>⚠️ Mẻ (hoặc gốc) này đã rework {specs.rework_count} lần. Hãy cẩn thận vòng lặp!</p>
                )}
              </>
            )}

            <label className="modal-label">Người thực hiện</label>
            <input className="modal-input" type="text"
              placeholder="Tên thợ / quản lý…"
              value={operator} onChange={e => setOp(e.target.value)} />

            <label className="modal-label">
              {modal === 'advance' ? 'Ghi chú (không bắt buộc)' : modal === 'issue' ? 'Mô tả sự cố *' : 'Lý do Rework *'}
            </label>
            <textarea className="modal-textarea" rows={3}
              placeholder={modal === 'advance' ? 'Ghi chú thêm…' : modal === 'issue' ? 'Ví dụ: 10 sản phẩm nứt men…' : 'Ghi rõ lỗi để thợ khắc phục...'}
              value={note} onChange={e => setNote(e.target.value)} />

            <div className="modal-actions">
              <button className="btn-cancel" onClick={close}>Hủy</button>
              <button
                className={modal === 'advance' ? 'btn-ok-adv' : 'btn-ok-iss'}
                disabled={loading || ((modal === 'issue' || modal === 'rework') && !note.trim()) || (modal === 'rework' && (reworkQty < 1 || reworkQty > batch.quantity))}
                onClick={handleOk}
              >
                {loading
                  ? <><span className="spinner-sm" /> Đang xử lý…</>
                  : modal === 'advance' ? <><CheckCircle size={18} weight="bold" /> Xác nhận</> : <><Warning size={18} weight="bold" /> Báo sự cố</>
                }
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
