export default function Notifications({ notifications, onDismiss }) {
  return (
    <div className="notifs">
      {notifications.map(n => (
        <div key={n.id} className={`notif ${n.type}`}>
          <div className="notif-body">
            <span className="notif-title">{n.title}</span>
            {n.message && <p className="notif-msg">{n.message}</p>}
          </div>
          <button className="notif-close" onClick={() => onDismiss(n.id)}>×</button>
        </div>
      ))}
    </div>
  )
}
