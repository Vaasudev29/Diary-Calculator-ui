import { useState, useEffect } from 'react';
import { Search, TrendingUp, TrendingDown, AlertTriangle, ArrowUpDown } from 'lucide-react';
import { formatIndianCurrency, formatPercent, formatNumber } from '../utils/formatters';

const API_BASE = 'http://localhost:8000';

function Customers() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [customers, setCustomers] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortConfig, setSortConfig] = useState({ key: 'revenue', direction: 'desc' });

  useEffect(() => {
    loadCustomers();
  }, []);

  async function loadCustomers() {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE}/api/customers`);
      if (!response.ok) throw new Error('Failed to fetch customers data');

      const data = await response.json();
      setCustomers(data.customers || []);
      setLoading(false);
    } catch (err) {
      console.error('Customers error:', err);
      setError(err.message);
      setLoading(false);
    }
  }

  // Sort customers
  const sortedCustomers = [...customers].sort((a, b) => {
    const aValue = a[sortConfig.key];
    const bValue = b[sortConfig.key];

    if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
    if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
    return 0;
  });

  // Filter customers by search term
  const filteredCustomers = sortedCustomers.filter(customer =>
    customer.customer.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Handle sort
  function handleSort(key) {
    setSortConfig(prevConfig => ({
      key,
      direction: prevConfig.key === key && prevConfig.direction === 'desc' ? 'asc' : 'desc',
    }));
  }

  // Handle customer click (will navigate to detail page in Phase 11)
  function handleCustomerClick(customer) {
    console.log('Customer clicked:', customer.customer);
    // Phase 11 will add navigation to customer detail page
  }

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>Loading customers...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-container">
        <AlertTriangle size={48} />
        <h2>Unable to load customers</h2>
        <p>{error}</p>
        <p>Please make sure the backend is running at http://localhost:8000</p>
        <button onClick={loadCustomers} className="retry-button">Retry</button>
      </div>
    );
  }

  // Calculate totals
  const totals = customers.reduce(
    (acc, customer) => ({
      revenue: acc.revenue + customer.revenue,
      cost: acc.cost + customer.cost,
      profit: acc.profit + customer.profit,
      quantity: acc.quantity + customer.quantity_tons,
    }),
    { revenue: 0, cost: 0, profit: 0, quantity: 0 }
  );

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1>Customers</h1>
          <p>Customer profitability analysis</p>
        </div>
        <div className="page-stats">
          <div className="page-stat">
            <span className="page-stat-label">Total Customers</span>
            <span className="page-stat-value">{customers.length}</span>
          </div>
          <div className="page-stat">
            <span className="page-stat-label">Total Revenue</span>
            <span className="page-stat-value">{formatIndianCurrency(totals.revenue)}</span>
          </div>
          <div className="page-stat">
            <span className="page-stat-label">Total Profit</span>
            <span className="page-stat-value">{formatIndianCurrency(totals.profit)}</span>
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="search-bar">
        <Search size={20} className="search-icon" />
        <input
          type="text"
          placeholder="Search customers..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="search-input"
        />
        {searchTerm && (
          <button onClick={() => setSearchTerm('')} className="search-clear">
            Clear
          </button>
        )}
      </div>

      {/* Results count */}
      {searchTerm && (
        <p className="search-results">
          Found {filteredCustomers.length} of {customers.length} customers
        </p>
      )}

      {/* Customers Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('customer')} className="sortable">
                <div className="th-content">
                  Customer
                  <ArrowUpDown size={16} />
                </div>
              </th>
              <th onClick={() => handleSort('quantity_tons')} className="sortable numeric">
                <div className="th-content">
                  Quantity (tons)
                  <ArrowUpDown size={16} />
                </div>
              </th>
              <th onClick={() => handleSort('revenue')} className="sortable numeric">
                <div className="th-content">
                  Revenue
                  <ArrowUpDown size={16} />
                </div>
              </th>
              <th onClick={() => handleSort('cost')} className="sortable numeric">
                <div className="th-content">
                  Cost
                  <ArrowUpDown size={16} />
                </div>
              </th>
              <th onClick={() => handleSort('profit')} className="sortable numeric">
                <div className="th-content">
                  Profit
                  <ArrowUpDown size={16} />
                </div>
              </th>
              <th onClick={() => handleSort('margin_percent')} className="sortable numeric">
                <div className="th-content">
                  Margin
                  <ArrowUpDown size={16} />
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            {filteredCustomers.length === 0 ? (
              <tr>
                <td colSpan="6" className="no-results">
                  No customers found matching "{searchTerm}"
                </td>
              </tr>
            ) : (
              filteredCustomers.map((customer, idx) => (
                <tr
                  key={idx}
                  onClick={() => handleCustomerClick(customer)}
                  className="clickable-row"
                >
                  <td className="customer-name">{customer.customer}</td>
                  <td className="numeric">{formatNumber(customer.quantity_tons)}</td>
                  <td className="numeric">{formatIndianCurrency(customer.revenue)}</td>
                  <td className="numeric">{formatIndianCurrency(customer.cost)}</td>
                  <td className="numeric profit-cell">
                    <span className={customer.profit >= 0 ? 'positive' : 'negative'}>
                      {formatIndianCurrency(customer.profit)}
                    </span>
                  </td>
                  <td className="numeric margin-cell">
                    <span className="margin-badge" style={{ 
                      background: customer.margin_percent > 20 ? '#d1fae5' : 
                                  customer.margin_percent > 10 ? '#fef3c7' : '#fee2e2',
                      color: customer.margin_percent > 20 ? '#059669' : 
                             customer.margin_percent > 10 ? '#d97706' : '#dc2626'
                    }}>
                      {formatPercent(customer.margin_percent)}
                      {customer.margin_percent > 20 && <TrendingUp size={14} />}
                      {customer.margin_percent <= 10 && <TrendingDown size={14} />}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer info */}
      <div className="table-footer">
        <p>
          Showing {filteredCustomers.length} customer{filteredCustomers.length !== 1 ? 's' : ''}
        </p>
        <p className="table-footer-note">
          Click on a customer row to view detailed information (Phase 11)
        </p>
      </div>
    </div>
  );
}

export default Customers;
