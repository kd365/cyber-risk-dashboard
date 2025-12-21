import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658', '#ff7c43', '#a4de6c'];

function CompanyGrowth({ ticker }) {
  const [growthData, setGrowthData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [fromCache, setFromCache] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const fetchGrowthData = async (forceRefresh = false) => {
    if (forceRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const url = forceRefresh
        ? `/api/company-growth/${ticker}?refresh=true`
        : `/api/company-growth/${ticker}`;
      const growthRes = await fetch(url);

      if (!growthRes.ok) {
        const errData = await growthRes.json();
        throw new Error(errData.error || 'Failed to fetch company growth data');
      }

      const growth = await growthRes.json();
      setGrowthData(growth);
      setFromCache(growth.from_cache || false);
    } catch (err) {
      console.error('Error fetching growth data:', err);
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    if (ticker) {
      fetchGrowthData(false);
    }
  }, [ticker]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px' }}>
        <div style={{ fontSize: '48px', marginBottom: '20px' }}>...</div>
        <p>Loading company growth data for {ticker}...</p>
        <p style={{ fontSize: '12px', color: '#888' }}>Fetching from Explorium API</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        textAlign: 'center',
        padding: '40px',
        background: '#fff3cd',
        borderRadius: '8px',
        border: '1px solid #ffc107'
      }}>
        <h3>Unable to Load Growth Data</h3>
        <p>{error}</p>
        <p style={{ fontSize: '12px', color: '#856404' }}>
          Ensure EXPLORIUM_API_KEY environment variable is set on the backend
        </p>
      </div>
    );
  }

  if (!growthData) {
    return (
      <div style={{ textAlign: 'center', padding: '40px' }}>
        <p>No growth data available for {ticker}</p>
      </div>
    );
  }

  // Prepare workforce composition from Explorium's perc_*_roles data
  const workforceData = growthData?.job_velocity?.by_category
    ? Object.entries(growthData.job_velocity.by_category)
        .map(([name, value]) => ({ name, value: value }))
        .filter(d => d.value > 0)
        .sort((a, b) => b.value - a.value)
    : [];

  return (
    <div>
      {/* Company Header */}
      <div style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: 'white',
        padding: '20px 30px',
        borderRadius: '8px',
        marginBottom: '20px'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ margin: 0 }}>
              {growthData.company?.name || ticker}
            </h2>
            <p style={{ margin: '5px 0 0 0', opacity: 0.9 }}>
              {growthData.company?.industry} | Founded {growthData.company?.founded}
            </p>
            <p style={{ margin: '5px 0 0 0', opacity: 0.8, fontSize: '12px' }}>
              {growthData.company?.headquarters}
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {fromCache && (
              <span style={{
                background: 'rgba(255,255,255,0.2)',
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '11px',
                fontWeight: '500'
              }}>
                Cached
              </span>
            )}
            <button
              onClick={() => fetchGrowthData(true)}
              disabled={refreshing}
              style={{
                background: 'rgba(255,255,255,0.2)',
                border: '1px solid rgba(255,255,255,0.3)',
                borderRadius: '6px',
                padding: '6px 12px',
                color: 'white',
                cursor: refreshing ? 'not-allowed' : 'pointer',
                fontSize: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                opacity: refreshing ? 0.7 : 1
              }}
              title="Refresh data from Explorium API"
            >
              <span style={{
                display: 'inline-block',
                animation: refreshing ? 'spin 1s linear infinite' : 'none'
              }}>
                ↻
              </span>
              {refreshing ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '30px'
      }}>
        <MetricCard
          title="Employee Count"
          value={growthData.employee_count?.toLocaleString() || 'N/A'}
          subtitle="LinkedIn employee range"
        />
        <MetricCard
          title="Hiring Events (90d)"
          value={growthData.job_velocity?.total_postings || 0}
          subtitle={growthData.job_velocity?.postings_per_week ? `~${growthData.job_velocity.postings_per_week}/week` : 'Based on detected events'}
        />
        <MetricCard
          title="Hiring Trend"
          value={formatTrend(growthData.job_velocity?.trend)}
          color={getTrendColor(growthData.job_velocity?.trend)}
          subtitle="Calculated from workforce changes"
        />
      </div>

      {/* Hiring Trend Explanation */}
      <div style={{
        background: '#e7f3ff',
        border: '1px solid #b3d9ff',
        borderRadius: '8px',
        padding: '15px',
        marginBottom: '20px'
      }}>
        <h4 style={{ marginTop: 0, marginBottom: '10px', color: '#004085' }}>About Hiring Trend</h4>
        <p style={{ margin: 0, fontSize: '13px', color: '#004085', lineHeight: '1.5' }}>
          The hiring trend is derived from Explorium's business events API, which tracks workforce changes
          including hiring activity by department. <strong>Accelerating</strong> indicates increased hiring events,
          <strong> Stable</strong> indicates consistent activity, and <strong> Slowing</strong> indicates decreased hiring.
          This metric reflects detected hiring patterns over the past 90 days.
        </p>
      </div>

      {/* Workforce Composition */}
      <div style={{
        background: '#f8f9fa',
        padding: '20px',
        borderRadius: '8px',
        marginBottom: '20px'
      }}>
        <h4 style={{ marginTop: 0, marginBottom: '5px' }}>Workforce Composition by Department</h4>
        <p style={{ margin: '0 0 15px 0', fontSize: '12px', color: '#666' }}>
          Percentage of workforce in each department (from Explorium workforce trends)
        </p>
        {workforceData.length > 0 ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
            {/* Bar Chart */}
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={workforceData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" unit="%" />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={100}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip formatter={(value) => `${value}%`} />
                <Bar dataKey="value" fill="#667eea" />
              </BarChart>
            </ResponsiveContainer>

            {/* Pie Chart */}
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={workforceData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, value }) => value >= 5 ? `${name} ${value}%` : ''}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {workforceData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => `${value}%`} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        ) : (
          <p style={{ textAlign: 'center', color: '#888' }}>No workforce composition data available</p>
        )}
      </div>

      {/* Recent Hiring Events */}
      {growthData.recent_events && growthData.recent_events.length > 0 && (
        <div style={{
          background: '#f8f9fa',
          padding: '20px',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <h4 style={{ marginTop: 0, marginBottom: '15px' }}>Recent Hiring Events</h4>
          <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#e9ecef', position: 'sticky', top: 0 }}>
                  <th style={thStyle}>Department</th>
                  <th style={thStyle}>Job Titles</th>
                  <th style={thStyle}>Location</th>
                  <th style={thStyle}>Date</th>
                </tr>
              </thead>
              <tbody>
                {growthData.recent_events.map((event, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #e9ecef' }}>
                    <td style={tdStyle}>
                      <span style={{
                        background: '#667eea',
                        color: 'white',
                        padding: '2px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        textTransform: 'capitalize'
                      }}>
                        {event.data?.department || 'N/A'}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      {event.data?.job_titles?.join(', ') || 'N/A'}
                    </td>
                    <td style={tdStyle}>{event.data?.location || 'N/A'}</td>
                    <td style={tdStyle}>{formatDate(event.event_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Data Freshness */}
      <div style={{
        marginTop: '20px',
        textAlign: 'right',
        fontSize: '11px',
        color: '#888'
      }}>
        Data from Explorium API | Last updated: {formatDate(growthData.data_freshness)}
        {fromCache && ' (from cache)'}
      </div>

      {/* CSS for spin animation */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// Helper Components
function MetricCard({ title, value, subtitle, color }) {
  return (
    <div style={{
      background: '#f8f9fa',
      padding: '20px',
      borderRadius: '8px',
      textAlign: 'center'
    }}>
      <div style={{
        fontSize: '28px',
        fontWeight: 'bold',
        color: color || '#2c3e50'
      }}>
        {value}
      </div>
      <div style={{ fontSize: '13px', color: '#333', marginTop: '8px', fontWeight: '500' }}>{title}</div>
      {subtitle && (
        <div style={{ fontSize: '11px', color: '#888', marginTop: '4px' }}>{subtitle}</div>
      )}
    </div>
  );
}

// Helper Functions
function getTrendColor(trend) {
  switch (trend) {
    case 'accelerating': return '#28a745';
    case 'decelerating': return '#dc3545';
    case 'stable': return '#17a2b8';
    case 'new_hiring': return '#28a745';
    default: return '#6c757d';
  }
}

function formatTrend(trend) {
  switch (trend) {
    case 'accelerating': return 'Accelerating';
    case 'decelerating': return 'Slowing';
    case 'stable': return 'Stable';
    case 'new_hiring': return 'New Hiring';
    default: return 'Unknown';
  }
}

function formatDate(dateStr) {
  if (!dateStr) return 'N/A';
  try {
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return dateStr;
  }
}

// Table styles
const thStyle = {
  padding: '12px',
  textAlign: 'left',
  borderBottom: '2px solid #dee2e6',
  fontSize: '12px',
  fontWeight: 'bold'
};

const tdStyle = {
  padding: '10px 12px',
  fontSize: '13px'
};

export default CompanyGrowth;
