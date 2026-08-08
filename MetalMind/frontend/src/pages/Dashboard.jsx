import { useState, useEffect } from 'react';
import { DollarSign, TrendingUp, Package, Users, AlertTriangle, Target } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import StatCard from '../components/StatCard';
import { formatIndianCurrency, formatPercent, formatNumber } from '../utils/formatters';

const API_BASE = 'http://localhost:8000';

function Dashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [risks, setRisks] = useState([]);
  const [crossSell, setCrossSell] = useState([]);

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function loadDashboardData() {
    try {
      setLoading(true);
      setError(null);

      // Fetch all dashboard data
      const [summaryRes, customersRes, productsRes, risksRes, crossSellRes] = await Promise.all([
        fetch(`${API_BASE}/api/summary`),
        fetch(`${API_BASE}/api/customers`),
        fetch(`${API_BASE}/api/products`),
        fetch(`${API_BASE}/api/risks`),
        fetch(`${API_BASE}/api/cross-sell`),
      ]);

      if (!summaryRes.ok) throw new Error('Failed to fetch summary data');
      if (!customersRes.ok) throw new Error('Failed to fetch customers data');
      if (!productsRes.ok) throw new Error('Failed to fetch products data');
      if (!risksRes.ok) throw new Error('Failed to fetch risks data');
      if (!crossSellRes.ok) throw new Error('Failed to fetch cross-sell data');

      const summaryData = await summaryRes.json();
      const customersData = await customersRes.json();
      const productsData = await productsRes.json();
      const risksData = await risksRes.json();
      const crossSellData = await crossSellRes.json();

      setSummary(summaryData);
      setCustomers(customersData.customers || []);
      setProducts(productsData.products || []);
      setRisks(risksData.risks || []);
      setCrossSell(crossSellData.opportunities || []);

      setLoading(false);
    } catch (err) {
      console.error('Dashboard error:', err);
      setError(err.message);
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <AlertTriangle size={48} />
        <h2>Unable to connect to the backend</h2>
        <p>{error}</p>
        <p>Please make sure FastAPI is running at http://localhost:8000</p>
        <button onClick={loadDashboardData} className="retry-button">Retry</button>
      </div>
    );
  }

  // Prepare chart data - top 8 customers and products
  const topCustomers = customers.slice(0, 8).map(c => ({
    name: c.customer,
    revenue: c.revenue,
    profit: c.profit,
  }));

  const topProducts = products.slice(0, 6).map(p => ({
    name: p.product,
    revenue: p.revenue,
    profit: p.profit,
  }));

  // Top risks (limit to 5)
  const topRisks = risks.slice(0, 5);

  // Top cross-sell opportunities (limit to 5)
  const topCrossSell = crossSell.slice(0, 5);

  return (
    <div className="dashboard">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <p>Commercial Intelligence Overview</p>
      </div>

      {/* KPI Cards */}
      <div className="stats-grid">
        <StatCard
          title="Total Revenue"
          value={formatIndianCurrency(summary.total_revenue)}
          icon={DollarSign}
        />
        <StatCard
          title="Total Cost"
          value={formatIndianCurrency(summary.total_cost)}
          icon={TrendingUp}
        />
        <StatCard
          title="Total Profit"
          value={formatIndianCurrency(summary.total_profit)}
          icon={DollarSign}
        />
        <StatCard
          title="Gross Margin"
          value={formatPercent(summary.gross_margin_percent)}
          icon={TrendingUp}
        />
        <StatCard
          title="Total Quantity"
          value={`${formatNumber(summary.total_quantity_tons)} tons`}
          icon={Package}
        />
        <StatCard
          title="Number of Customers"
          value={summary.number_of_customers}
          icon={Users}
        />
      </div>

      {/* Charts Section */}
      <div className="charts-grid">
        {/* Customer Profitability Chart */}
        <div className="chart-card">
          <h2 className="chart-title">Top Customers by Revenue & Profit</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topCustomers}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip formatter={(value) => formatIndianCurrency(value)} />
              <Legend />
              <Bar dataKey="revenue" fill="#3b82f6" name="Revenue" />
              <Bar dataKey="profit" fill="#10b981" name="Profit" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Product Profitability Chart */}
        <div className="chart-card">
          <h2 className="chart-title">Product Profitability</h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={topProducts}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} />
              <YAxis />
              <Tooltip formatter={(value) => formatIndianCurrency(value)} />
              <Legend />
              <Bar dataKey="revenue" fill="#8b5cf6" name="Revenue" />
              <Bar dataKey="profit" fill="#f59e0b" name="Profit" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Preview Sections */}
      <div className="preview-grid">
        {/* At-Risk Customers */}
        <div className="preview-card">
          <h2 className="preview-title">
            <AlertTriangle size={20} />
            At-Risk Customers
          </h2>
          {topRisks.length === 0 ? (
            <p className="preview-empty">No high-risk customers identified</p>
          ) : (
            <div className="risk-list">
              {topRisks.map((risk, idx) => (
                <div key={idx} className="risk-item">
                  <div className="risk-header">
                    <span className="risk-customer">{risk.customer}</span>
                    <span className={`risk-badge risk-${risk.risk_level.toLowerCase()}`}>
                      {risk.risk_level}
                    </span>
                  </div>
                  <p className="risk-reason">{risk.reason}</p>
                  <div className="risk-metrics">
                    <span>Revenue: {formatIndianCurrency(risk.revenue)}</span>
                    <span>Margin: {formatPercent(risk.margin_percent)}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Cross-Sell Opportunities */}
        <div className="preview-card">
          <h2 className="preview-title">
            <Target size={20} />
            Cross-Sell Opportunities
          </h2>
          {topCrossSell.length === 0 ? (
            <p className="preview-empty">No cross-sell opportunities found</p>
          ) : (
            <div className="cross-sell-list">
              {topCrossSell.map((opp, idx) => (
                <div key={idx} className="cross-sell-item">
                  <div className="cross-sell-header">
                    <span className="cross-sell-customer">{opp.customer}</span>
                    <span className="cross-sell-value">
                      {formatIndianCurrency(opp.estimated_opportunity)}
                    </span>
                  </div>
                  <p className="cross-sell-product">→ {opp.recommended_product}</p>
                  <p className="cross-sell-reason">{opp.reason}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
