import React, { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000/api/disagreements/'

const REASONS = [
  { value: 'ALL', label: 'All Disagreements' },
  { value: 'MISSING_IN_B', label: 'Missing in System B' },
  { value: 'ORPHAN_IN_B', label: 'Orphan in System B' },
  { value: 'DUPLICATE_IN_B', label: 'Duplicate in System B' },
  { value: 'VALUE_MISMATCH', label: 'Value Mismatch' },
  { value: 'LOCATION_MISMATCH', label: 'Location Mismatch' },
  { value: 'DATE_MISMATCH', label: 'Date Mismatch' },
  { value: 'VOIDED_RECORD_ACTIVE_IN_B', label: 'Voided in A but active in B' },
]

export default function App() {
  const [org, setOrg] = useState('ORG-A')
  const [reason, setReason] = useState('ALL')
  const [sortField, setSortField] = useState('')
  const [sortOrder, setSortOrder] = useState('asc')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchDisagreements()
  }, [org, reason, sortField, sortOrder])

  const fetchDisagreements = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      params.append('org', org)
      if (reason && reason !== 'ALL') {
        params.append('reason', reason)
      }
      if (sortField) {
        const sortParam = sortOrder === 'desc' ? `-${sortField}` : sortField
        params.append('sort', sortParam)
      }

      const res = await fetch(`${API_BASE}?${params.toString()}`)
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || `Server returned ${res.status}`)
      }
      const data = await res.json()
      setItems(data)
    } catch (err) {
      setError(err.message || 'Failed to fetch disagreements')
    } finally {
      setLoading(false)
    }
  }

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const formatCurrency = (val) => {
    if (val === null || val === undefined || val === '') {
      return <span className="cell-empty">—</span>
    }
    const num = parseFloat(val)
    if (isNaN(num)) return <span className="cell-empty">—</span>
    return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  return (
    <div className="container">
      <header>
        <h1>DealerOS Reconciliation Ledger</h1>
        <p>Tenant-isolated comparison between System A and System B ledgers</p>
      </header>

      {error && (
        <div className="error-banner">
          <strong>Error:</strong> {error}
        </div>
      )}

      <div className="controls-card">
        <div className="control-group">
          <label htmlFor="org-select">Tenant (Organization)</label>
          <select
            id="org-select"
            value={org}
            onChange={(e) => setOrg(e.target.value)}
          >
            <option value="ORG-A">ORG-A (LOC-101 .. LOC-103)</option>
            <option value="ORG-B">ORG-B (LOC-201 .. LOC-202)</option>
          </select>
        </div>

        <div className="control-group">
          <label htmlFor="reason-select">Filter by Reason</label>
          <select
            id="reason-select"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          >
            {REASONS.map(r => (
              <option key={r.value} value={r.value}>{r.label}</option>
            ))}
          </select>
        </div>

        <div className="summary-stats">
          <span className="stat-pill">
            Showing: <strong>{items.length}</strong> items
          </span>
        </div>
      </div>

      <div className="table-card">
        {loading ? (
          <div className="loading">Loading ledger entries...</div>
        ) : items.length === 0 ? (
          <div className="empty-message">
            No disagreements found for the selected tenant and filter.
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Reason</th>
                <th className="sortable" onClick={() => handleSort('record_id')}>
                  Record ID {sortField === 'record_id' ? (sortOrder === 'asc' ? '▲' : '▼') : ''}
                </th>
                <th>Location</th>
                <th className="cell-num sortable" onClick={() => handleSort('a_value')}>
                  System A Value {sortField === 'a_value' ? (sortOrder === 'asc' ? '▲' : '▼') : ''}
                </th>
                <th className="cell-num sortable" onClick={() => handleSort('b_value')}>
                  System B Value {sortField === 'b_value' ? (sortOrder === 'asc' ? '▲' : '▼') : ''}
                </th>
                <th className="cell-num sortable" onClick={() => handleSort('difference')}>
                  Difference {sortField === 'difference' ? (sortOrder === 'asc' ? '▲' : '▼') : ''}
                </th>
                <th>Audit Notes</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row, idx) => (
                <tr key={`${row.reason}-${row.record_id}-${idx}`}>
                  <td>
                    <span className={`badge badge-${row.reason}`}>
                      {row.reason}
                    </span>
                  </td>
                  <td><strong>{row.record_id}</strong></td>
                  <td>{row.location}</td>
                  <td className="cell-num">{formatCurrency(row.a_value)}</td>
                  <td className="cell-num">{formatCurrency(row.b_value)}</td>
                  <td className="cell-num">{formatCurrency(row.difference)}</td>
                  <td style={{ fontSize: '13px', color: '#475569' }}>{row.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
