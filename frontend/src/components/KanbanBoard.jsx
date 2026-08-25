import { useState } from 'react'
import BatchCard from './BatchCard'

const STAGES = [
  { id: 'FORMING',   name: 'Tạo Hình Mộc',       emoji: '🏺', color: 'var(--s-forming)',   cls: '' },
  { id: 'DRYING',    name: 'Phơi Sấy & Sửa',      emoji: '☀️', color: 'var(--s-drying)',    cls: '' },
  { id: 'PAINTING',  name: 'Vẽ Họa Tiết',          emoji: '🎨', color: 'var(--s-painting)',  cls: '' },
  { id: 'GLAZING',   name: 'Tráng Men',             emoji: '✨', color: 'var(--s-glazing)',   cls: '' },
  { id: 'FIRING',    name: 'Vào Lò Nung',           emoji: '🔥', color: 'var(--s-firing)',    cls: 'firing-col' },
  { id: 'QC',        name: 'QC & Đóng Gói',         emoji: '✅', color: 'var(--s-qc)',        cls: '' },
  { id: 'COMPLETED', name: 'Hoàn Thành',            emoji: '📦', color: 'var(--s-completed)', cls: '' },
]

export default function KanbanBoard({ batches, onAdvance, onIssue, onRework }) {
  const [collapsedCols, setCollapsedCols] = useState({})

  const toggleCol = (id) => {
    setCollapsedCols(prev => ({ ...prev, [id]: !prev[id] }))
  }

  return (
    <div className="kanban-board">
      {STAGES.map(stage => {
        const cards = batches.filter(b =>
          b.current_stage === stage.id &&
          (stage.id !== 'COMPLETED' ? b.status !== 'COMPLETED' : b.status === 'COMPLETED')
        )

        const isCollapsed = collapsedCols[stage.id]

        return (
          <div key={stage.id} className={`k-col ${stage.cls} ${isCollapsed ? 'collapsed' : ''}`}>
            
            {/* Header */}
            <div className="k-col-head" onClick={() => isCollapsed && toggleCol(stage.id)}>
              {!isCollapsed && <span className="k-col-emoji">{stage.emoji}</span>}
              
              <div className="k-col-info">
                <p className="k-col-name">{stage.name.toUpperCase()}</p>
                <span className="k-col-cnt" style={{ backgroundColor: stage.color }}>
                  {cards.length}
                </span>
              </div>

              {/* Toggle button */}
              <button 
                className="col-toggle-btn" 
                onClick={(e) => { e.stopPropagation(); toggleCol(stage.id); }}
                title={isCollapsed ? "Mở rộng" : "Thu gọn"}
              >
                {isCollapsed ? '↔' : '→←'}
              </button>
            </div>

            {/* Body */}
            {!isCollapsed && (
              <div className="k-col-body">
                {cards.length === 0
                  ? <div className="k-empty">Không có mẻ nào</div>
                  : cards.map(batch => (
                      <BatchCard
                        key={batch.id}
                        batch={batch}
                        stageColor={stage.color}
                        onAdvance={onAdvance}
                        onIssue={onIssue}
                        onRework={onRework}
                      />
                    ))
                }
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
