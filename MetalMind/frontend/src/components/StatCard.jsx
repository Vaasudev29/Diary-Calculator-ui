function StatCard({ title, value, icon: Icon, trend }) {
  return (
    <div className="stat-card">
      <div className="stat-card-header">
        <h3 className="stat-card-title">{title}</h3>
        {Icon && <Icon size={24} className="stat-card-icon" />}
      </div>
      <div className="stat-card-value">{value}</div>
      {trend && <div className="stat-card-trend">{trend}</div>}
    </div>
  );
}

export default StatCard;
