// frontend/src/components/TimeSeriesForecast.jsx
import React, { useState, useEffect } from 'react';
import {
  Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  Area, ComposedChart, ResponsiveContainer, ReferenceLine
} from 'recharts';

function TimeSeriesForecast({ ticker }) {
  const [forecast, setForecast] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [forecastDays, setForecastDays] = useState(30);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [fromCache, setFromCache] = useState(false);

  const fetchData = (forceRefresh = false) => {
    setLoading(true);
    if (forceRefresh) setRefreshing(true);

    const refreshParam = forceRefresh ? '&refresh=true' : '';

    // Fetch forecast
    fetch(`/api/forecast?ticker=${ticker}&days=${forecastDays}${refreshParam}`)
      .then(res => res.json())
      .then(data => {
        setForecast(data);
        setFromCache(data.from_cache || false);
      })
      .catch(err => console.error('Error fetching forecast:', err));

    // Fetch model evaluation
    fetch(`/api/evaluate/${ticker}`)
      .then(res => res.json())
      .then(data => setEvaluation(data))
      .catch(err => console.error('Error fetching evaluation:', err));

    // Fetch financial data
    fetch(`/api/financials/${ticker}`)
      .then(res => res.json())
      .then(data => {
        setFinancials(data);
        setLoading(false);
        setRefreshing(false);
      })
      .catch(err => {
        console.error('Error fetching financials:', err);
        setLoading(false);
        setRefreshing(false);
      });
  };

  useEffect(() => {
    fetchData(false);
  }, [ticker, forecastDays]);

  if (loading || !forecast) {
    return (
      <div style={{ padding: '40px', textAlign: 'center', color: '#7f8c8d' }}>
        <div style={{ fontSize: '24px', marginBottom: '10px' }}>...</div>
        <div>Loading forecast data...</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      {/* Header */}
      <div style={{ marginBottom: '30px' }}>
        <h2 style={{ color: '#2c3e50', marginBottom: '10px' }}>
          Stock Price Forecast - {ticker}
        </h2>
        <p style={{ color: '#7f8c8d', fontSize: '14px' }}>
          AI-powered stock price prediction using Prophet with cybersecurity risk indicators
        </p>
        <div style={{
          marginTop: '15px',
          padding: '12px 15px',
          background: '#e8f4fd',
          borderRadius: '6px',
          borderLeft: '4px solid #007bff',
          fontSize: '12px',
          color: '#495057'
        }}>
          <strong>Model Configuration:</strong> Prophet with <code>changepoint_prior_scale=0.05</code> (conservative trend flexibility)
          and <code>seasonality_prior_scale=10</code> (strong seasonality patterns).
          Includes daily, weekly, and yearly seasonality with cybersecurity sentiment and volatility as external regressors.
        </div>
      </div>

      {/* Forecast Period Selector */}
      <div style={{
        marginBottom: '25px',
        padding: '15px',
        background: '#f8f9fa',
        borderRadius: '8px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '15px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
          <span style={{ fontWeight: 'bold', color: '#2c3e50' }}>Forecast Period:</span>
          <div style={{ display: 'flex', gap: '10px' }}>
            {[30, 60, 90].map(days => (
              <button
                key={days}
                onClick={() => setForecastDays(days)}
                style={{
                  padding: '8px 16px',
                  border: forecastDays === days ? '2px solid #007bff' : '1px solid #dee2e6',
                  borderRadius: '6px',
                  background: forecastDays === days ? '#007bff' : 'white',
                  color: forecastDays === days ? 'white' : '#495057',
                  fontWeight: forecastDays === days ? 'bold' : 'normal',
                  cursor: 'pointer',
                  fontSize: '14px'
                }}
              >
                {days} Days
              </button>
            ))}
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {fromCache && (
            <span style={{ fontSize: '12px', color: '#28a745' }}>
              Loaded from cache
            </span>
          )}
          <button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            style={{
              padding: '8px 16px',
              border: '1px solid #28a745',
              borderRadius: '6px',
              background: refreshing ? '#ccc' : '#28a745',
              color: 'white',
              fontWeight: 'bold',
              cursor: refreshing ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            {refreshing ? 'Refreshing...' : 'Refresh Forecast'}
          </button>
        </div>
      </div>

      {/* Model Performance Metrics */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginBottom: '30px'
      }}>
        <MetricCard
          title="MAPE"
          value={evaluation?.mape ? `${evaluation.mape.toFixed(2)}%` : 'N/A'}
          subtitle="Mean Absolute % Error"
          info="Lower is better - measures prediction accuracy"
        />
        <MetricCard
          title="Expected Return"
          value={forecast.expected_return_pct ? `${forecast.expected_return_pct > 0 ? '+' : ''}${forecast.expected_return_pct.toFixed(2)}%` : 'N/A'}
          subtitle={`${forecastDays}-day prediction`}
          positive={forecast.expected_return_pct > 0}
        />
        <MetricCard
          title="Confidence Interval"
          value={forecast.confidence_interval ? `$${forecast.confidence_interval.lower.toFixed(2)} - $${forecast.confidence_interval.upper.toFixed(2)}` : 'N/A'}
          subtitle="95% confidence range"
          info="Range where actual price is likely to fall"
        />
        <MetricCard
          title="Current Price"
          value={forecast.current_price ? `$${forecast.current_price.toFixed(2)}` : 'N/A'}
          subtitle="Latest closing price"
        />
      </div>

      {/* Stock Price Forecast Chart */}
      {(() => {
        // Combine historical and forecast data
        const historicalData = (forecast.historical || []).map(d => ({
          ds: d.ds,
          actual: d.actual,
          yhat: null,
          yhat_lower: null,
          yhat_upper: null
        }));

        const forecastData = (forecast.forecast || []).map(d => ({
          ds: d.ds,
          actual: null,
          yhat: d.yhat,
          yhat_lower: d.yhat_lower,
          yhat_upper: d.yhat_upper
        }));

        const combinedData = [...historicalData, ...forecastData];
        const todayDate = forecast.today || new Date().toISOString().split('T')[0];

        return (
          <div style={{
            background: 'white',
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            padding: '25px',
            marginBottom: '30px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '10px', color: '#2c3e50' }}>
              Stock Price Forecast
            </h3>
            <p style={{ color: '#6c757d', fontSize: '14px', marginBottom: '20px' }}>
              Historical prices (solid green) and AI predictions (blue with confidence bands)
            </p>

            <ResponsiveContainer width="100%" height={400}>
              <ComposedChart data={combinedData} margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis
                  dataKey="ds"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    return `${date.getMonth() + 1}/${date.getDate()}`;
                  }}
                />
                <YAxis
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `$${value.toFixed(0)}`}
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  formatter={(value, name) => {
                    if (value === null) return ['-', name];
                    return [`$${value.toFixed(2)}`, name];
                  }}
                  labelFormatter={(label) => new Date(label).toLocaleDateString()}
                />
                <Legend />

                {/* Today's vertical line */}
                <ReferenceLine
                  x={todayDate}
                  stroke="#e74c3c"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                  label={{
                    value: 'Today',
                    position: 'top',
                    fill: '#e74c3c',
                    fontSize: 12,
                    fontWeight: 'bold'
                  }}
                />

                {/* Confidence interval as shaded band between upper and lower */}
                <Area
                  type="monotone"
                  dataKey="yhat_upper"
                  stroke="#007bff"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  fill="#007bff"
                  fillOpacity={0.15}
                  name="Upper Bound (95%)"
                  connectNulls={false}
                />
                <Area
                  type="monotone"
                  dataKey="yhat_lower"
                  stroke="#007bff"
                  strokeWidth={1}
                  strokeDasharray="3 3"
                  fill="#ffffff"
                  fillOpacity={1}
                  name="Lower Bound (95%)"
                  connectNulls={false}
                />

                {/* Historical actual prices - solid green line */}
                <Line
                  type="monotone"
                  dataKey="actual"
                  stroke="#28a745"
                  strokeWidth={2}
                  name="Actual Price"
                  dot={false}
                  connectNulls={false}
                />

                {/* Forecast line - blue */}
                <Line
                  type="monotone"
                  dataKey="yhat"
                  stroke="#007bff"
                  strokeWidth={3}
                  name="Predicted Price"
                  dot={false}
                  connectNulls={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        );
      })()}

      {/* Financial Metrics Chart */}
      {financials && financials.timeline && financials.timeline.length > 0 && (() => {
        // Get the latest filing with BOTH revenue and subscription data
        const latestFilingWithBothMetrics = [...financials.timeline]
          .reverse()
          .find(f => f.revenue && f.subscription_revenue);

        const latestRevenue = latestFilingWithBothMetrics?.revenue || financials.latest_filing?.revenue || 0;
        const latestSubscription = latestFilingWithBothMetrics?.subscription_revenue || financials.latest_filing?.subscription_revenue || 0;
        const latestFilingDate = latestFilingWithBothMetrics?.date || financials.latest_filing?.date;
        const latestFilingType = latestFilingWithBothMetrics?.type || financials.latest_filing?.type;

        const subscriptionPercentage = latestRevenue > 0 ? (latestSubscription / latestRevenue) * 100 : 0;

        // Calculate trend direction for 4Q average
        const timelineWithAvg = financials.timeline.filter(d => d.revenue_rolling_avg);
        let trendDirection = '→';
        if (timelineWithAvg.length >= 2) {
          const latest = timelineWithAvg[timelineWithAvg.length - 1].revenue_rolling_avg;
          const previous = timelineWithAvg[timelineWithAvg.length - 2].revenue_rolling_avg;
          trendDirection = latest > previous ? '↑' : latest < previous ? '↓' : '→';
        }

        // Find when rolling averages start
        const firstAvgIndex = financials.timeline.findIndex(d => d.revenue_rolling_avg);

        return (
          <div style={{
            background: 'white',
            border: '1px solid #dee2e6',
            borderRadius: '8px',
            padding: '25px',
            marginBottom: '30px',
            boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '10px', color: '#2c3e50' }}>
              Financial Metrics from SEC Filings
            </h3>
            <p style={{ color: '#6c757d', fontSize: '14px', marginBottom: '20px' }}>
              Revenue and subscription revenue trends with 4-quarter rolling averages (in billions)
            </p>

            {/* Financial Summary Cards */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
              gap: '15px',
              marginBottom: '25px'
            }}>
              <MetricCard
                title="Latest Revenue"
                value={latestRevenue ? `$${(latestRevenue / 1e9).toFixed(2)}B` : 'N/A'}
                subtitle={`${latestFilingType} - ${latestFilingDate}`}
              />
              <MetricCard
                title="Subscription Revenue"
                value={latestSubscription ? `$${(latestSubscription / 1e9).toFixed(2)}B` : 'N/A'}
                subtitle="Same period as revenue"
              />
              <MetricCard
                title="Subscription %"
                value={subscriptionPercentage > 0 ? `${subscriptionPercentage.toFixed(1)}%` : 'N/A'}
                subtitle="Of total revenue"
                info="Higher is better for SaaS"
              />
              <MetricCard
                title="4Q Trend"
                value={trendDirection}
                subtitle="Rolling average direction"
                positive={trendDirection === '↑'}
              />
              <MetricCard
                title="4Q Revenue Avg"
                value={financials.rolling_averages?.revenue_4q_avg ? `$${(financials.rolling_averages.revenue_4q_avg / 1e9).toFixed(2)}B` : 'N/A'}
                subtitle="Rolling 4-quarter average"
              />
              <MetricCard
                title="Filings Analyzed"
                value={`${financials.filing_count}`}
                subtitle="10-K and 10-Q reports"
              />
            </div>

            {/* CrowdStrike Incident Callout (if applicable) */}
            {ticker === 'CRWD' && (
              <div style={{
                background: '#fff3cd',
                border: '1px solid #ffc107',
                borderRadius: '6px',
                padding: '12px 15px',
                marginBottom: '20px',
                fontSize: '13px',
                color: '#856404'
              }}>
                <strong>Note:</strong> Revenue dip in July 2024 reflects the impact of the global IT outage incident (CrowdStrike Falcon sensor update issue).
              </div>
            )}

            {/* Rolling Average Explanation */}
            {firstAvgIndex >= 0 && (
              <div style={{
                background: '#e7f3ff',
                border: '1px solid #b3d9ff',
                borderRadius: '6px',
                padding: '12px 15px',
                marginBottom: '20px',
                fontSize: '13px',
                color: '#004085'
              }}>
                <strong>Rolling Averages:</strong> 4-quarter rolling averages begin at filing #{firstAvgIndex + 1} ({financials.timeline[firstAvgIndex]?.date}) when sufficient historical data is available. Dashed lines represent smoothed trends.
              </div>
            )}

            <ResponsiveContainer width="100%" height={450}>
              <ComposedChart
                data={financials.timeline}
                margin={{ top: 30, right: 90, left: 80, bottom: 40 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 12 }}
                  label={{ value: 'Filing Date', position: 'insideBottom', offset: -5, style: { fontSize: 12, fill: '#666' } }}
                />
                <YAxis
                  yAxisId="left"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `$${(value / 1e9).toFixed(1)}B`}
                  label={{ value: 'Total Revenue (Billions USD)', angle: -90, position: 'insideLeft', style: { fontSize: 12, fill: '#28a745' } }}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `$${(value / 1e9).toFixed(1)}B`}
                  label={{ value: 'Subscription Revenue (Billions USD)', angle: 90, position: 'insideRight', style: { fontSize: 12, fill: '#007bff' } }}
                />
                <Tooltip
                  formatter={(value, name) => {
                    // Standardize all values to billions
                    return [`$${(value / 1e9).toFixed(2)}B`, name];
                  }}
                  labelFormatter={(label) => `Filing: ${label}`}
                />
                <Legend
                  wrapperStyle={{ paddingTop: '10px' }}
                  formatter={(value) => {
                    // Make legend clearer
                    if (value.includes('4Q Avg')) {
                      return value + ' (dashed)';
                    }
                    return value + ' (solid)';
                  }}
                />

                {/* Revenue - Solid Line */}
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="revenue"
                  stroke="#28a745"
                  strokeWidth={3}
                  name="Total Revenue"
                  dot={{ r: 5, fill: '#28a745' }}
                />

                {/* Revenue Rolling Average - Dashed Line */}
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="revenue_rolling_avg"
                  stroke="#1a7a31"
                  strokeWidth={2.5}
                  strokeDasharray="8 4"
                  name="Revenue 4Q Avg"
                  dot={false}
                  connectNulls
                />

                {/* Subscription Revenue - Solid Line */}
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="subscription_revenue"
                  stroke="#007bff"
                  strokeWidth={3}
                  name="Subscription Revenue"
                  dot={{ r: 5, fill: '#007bff' }}
                />

                {/* Subscription Revenue Rolling Average - Dashed Line */}
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="subscription_revenue_rolling_avg"
                  stroke="#0056b3"
                  strokeWidth={2.5}
                  strokeDasharray="8 4"
                  name="Subscription 4Q Avg"
                  dot={false}
                  connectNulls
                />
              </ComposedChart>
            </ResponsiveContainer>

            {/* Chart Legend Explanation */}
            <div style={{
              marginTop: '15px',
              padding: '12px',
              background: '#f8f9fa',
              borderRadius: '6px',
              fontSize: '12px',
              color: '#6c757d'
            }}>
              <strong>Chart Guide:</strong> <span style={{ color: '#28a745' }}>●</span> Solid lines show actual quarterly/annual revenue.
              <span style={{ marginLeft: '10px' }}>- - -</span> Dashed lines show 4-quarter rolling averages for trend smoothing.
            </div>
          </div>
        );
      })()}

      {/* Model Explanation */}
      <div style={{
        background: '#f8f9fa',
        border: '1px solid #dee2e6',
        borderRadius: '8px',
        padding: '20px'
      }}>
        <h4 style={{ marginTop: 0, color: '#2c3e50' }}>Model Details</h4>
        <p style={{ color: '#495057', lineHeight: '1.6', marginBottom: '10px' }}>
          This forecast uses <strong>Facebook Prophet</strong>, a time series forecasting model that captures:
        </p>
        <ul style={{ color: '#495057', lineHeight: '1.8', marginLeft: '20px' }}>
          <li><strong>Seasonality:</strong> Weekly and yearly patterns in stock prices</li>
          <li><strong>Trends:</strong> Long-term growth or decline in stock value</li>
          <li><strong>Volatility:</strong> Historical price fluctuations to estimate uncertainty</li>
          <li><strong>Sentiment Analysis:</strong> Cybersecurity risk sentiment from SEC filings and earnings transcripts</li>
        </ul>
        <p style={{ color: '#6c757d', fontSize: '13px', marginTop: '15px', marginBottom: 0 }}>
          <strong>Note:</strong> This is a statistical model for educational purposes only. Not financial advice.
        </p>
      </div>
    </div>
  );
}

// Metric Card Component
function MetricCard({ title, value, subtitle, info, positive }) {
  const valueColor = positive !== undefined ? (positive ? '#28a745' : '#dc3545') : '#2c3e50';

  return (
    <div style={{
      background: 'white',
      border: '1px solid #dee2e6',
      borderRadius: '8px',
      padding: '20px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
    }}>
      <div style={{
        fontSize: '12px',
        color: '#6c757d',
        marginBottom: '8px',
        fontWeight: '600',
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
      }}>
        {title}
      </div>
      <div style={{
        fontSize: '24px',
        fontWeight: 'bold',
        color: valueColor,
        marginBottom: '5px'
      }}>
        {value}
      </div>
      <div style={{ fontSize: '12px', color: '#7f8c8d' }}>
        {subtitle}
      </div>
      {info && (
        <div style={{
          fontSize: '11px',
          color: '#adb5bd',
          marginTop: '8px',
          fontStyle: 'italic'
        }}>
          💡 {info}
        </div>
      )}
    </div>
  );
}

export default TimeSeriesForecast;
