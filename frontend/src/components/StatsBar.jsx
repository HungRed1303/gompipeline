export default function StatsBar({ stats }) {
  return (
    <div className="stats-bar">
      <div className="stat-card" title="Tổng số mẻ gốm">
        <span className="stat-val">{stats.total}</span>
        <span className="stat-lbl">Tổng mẻ</span>
      </div>
      <div className="stat-card" title="Đang sản xuất">
        <span className="stat-val c-blue">{stats.active}</span>
        <span className="stat-lbl">Đang SX</span>
      </div>
      <div className="stat-card" title="Đang nung lò">
        <span className="stat-val c-fire">{stats.firing}</span>
        <span className="stat-lbl">🔥 Nung lò</span>
      </div>
      <div className="stat-card" title="Đang có sự cố">
        <span className="stat-val c-red">{stats.issues}</span>
        <span className="stat-lbl">Sự cố</span>
      </div>
      <div className="stat-card" title="Đã hoàn thành">
        <span className="stat-val c-green">{stats.completed}</span>
        <span className="stat-lbl">Xong</span>
      </div>
    </div>
  )
}
