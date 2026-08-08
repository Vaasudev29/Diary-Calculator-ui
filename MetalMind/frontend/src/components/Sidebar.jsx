import { LayoutDashboard, Users, Package, AlertTriangle, TrendingUp, Database } from 'lucide-react';

function Sidebar({ activePage, onNavigate }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'customers', label: 'Customers', icon: Users },
    { id: 'products', label: 'Products', icon: Package },
    { id: 'risks', label: 'Risks', icon: AlertTriangle },
    { id: 'cross-sell', label: 'Cross-Sell', icon: TrendingUp },
    { id: 'data', label: 'Data', icon: Database },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1 className="sidebar-title">MetalMind</h1>
        <p className="sidebar-subtitle">Commercial Intelligence for Metals & Mining</p>
      </div>
      <nav className="sidebar-nav">
        {menuItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={`nav-item ${activePage === item.id ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
            >
              <Icon size={20} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </div>
  );
}

export default Sidebar;
