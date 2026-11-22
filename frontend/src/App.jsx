import React, { useState, useEffect } from 'react'

const API_BASE = 'http://127.0.0.1:8000/api/disagreements/'

const REASONS = [
  { value: 'ALL', label: 'All Disagreements' },
  { value: 'MISSING_IN_B', label: 'MISSING_IN_B' },
  { value: 'ORPHAN_IN_B', label: 'ORPHAN_IN_B' },
  { value: 'DUPLICATE_IN_B', label: 'DUPLICATE_IN_B' },
  { value: 'VALUE_MISMATCH', label: 'VALUE_MISMATCH' },
  { value: 'LOCATION_MISMATCH', label: 'LOCATION_MISMATCH' },
  { value: 'DATE_MISMATCH', label: 'DATE_MISMATCH' },
  { value: 'VOIDED_RECORD_ACTIVE_IN_B', label: 'VOIDED_RECORD_ACTIVE_IN_B' },
]

export default function App() {
  const [org, setOrg] = useState('ORG-A')
  const [reason, setReason] = useState('ALL')
  const [sort, setSort] = useState('') // "" -> "-value" -> "value" -> ""
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Fetch when org, reason, or sort changes
  useEffect(() => {
    fetchDisagreements()
  }, [org, reason, sort])

  const fetchDisagreements = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      params.append('org', org)

      if (reason && reason !== 'ALL') {
        params.append('reason', reason)
      }

      if (sort) {
        params.append('sort', sort)
      }

      const res = await fetch(`${API_BASE}?${params.toString()}`)
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.error || `Server responded with status ${res.status}`)
      }
      const data = await res.json()
      setItems(data)
    } catch (err) {
      setError(
        err.message === 'Failed to fetch'
          ? 'Failed to fetch from backend. Ensure the Django server is running on http://127.0.0.1:8000'
          : err.message
      )
      setItems([])
    } finally {
      setLoading(false)
    }
  }

  // Cycle sort order: "" -> "-value" -> "value" -> ""
  const handleSortCycle = () => {
    setSort(prev => {
      if (prev === '') return '-value'
      if (prev === '-value') return 'value'
      return ''
    })
  }

  // Format monetary value with 2 decimal places, or render "" if null/blank/missing
  const formatAmount = (val) => {
    if (val === null || val === undefined || val === '') return ''
    const num = Number(val)
    if (isNaN(num)) return ''
    return num.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }

  // Compute Difference as a_value - b_value only when both are present; otherwise ""
  const computeDifference = (aVal, bVal) => {
    if (
      aVal === null ||
      aVal === undefined ||
      aVal === '' ||
      bVal === null ||
      bVal === undefined ||
      bVal === ''
    ) {
      return ''
    }
    const numA = Number(aVal)
    const numB = Number(bVal)
    if (isNaN(numA) || isNaN(numB)) return ''
    const diff = numA - numB
    return diff.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  }

  const renderSortIndicator = () => {
    if (sort === '-value') return <span className="sort-indicator active">▼</span>
    if (sort === 'value') return <span className="sort-indicator active">▲</span>
    return <span className="sort-indicator">↕</span>
  }

  return (
    <div className="app-layout">
      {/* 1. Top Header Bar */}
      <header className="top-header">
        <div className="header-brand">
          <span className="brand-badge">DealerOS</span>
          <h1 className="header-title">Ledger Reconciliation Console</h1>
        </div>
        <div className="tenant-selector-group">
          <label htmlFor="tenant-select" className="tenant-label">
            Tenant:
          </label>
          <select
            id="tenant-select"
            className="tenant-select"
            value={org}
            onChange={(e) => setOrg(e.target.value)}
          >
            <option value="ORG-A">ORG-A (Locations 101–103)</option>
            <option value="ORG-B">ORG-B (Locations 201–202)</option>
          </select>
        </div>
      </header>

      <main className="main-container">
        {/* Error Banner */}
        {error && (
          <div className="error-banner" role="alert">
            <span className="error-icon">⚠️</span>
            <div className="error-content">
              <strong>Connection Error:</strong> {error}
            </div>
            <button className="error-retry-btn" onClick={fetchDisagreements}>
              Retry
            </button>
          </div>
        )}

        {/* 2. Toolbar above the table */}
        <div className="toolbar-card">
          <div className="toolbar-left">
            <h2 className="toolbar-heading">Disagreements</h2>
            <span className="pill-badge">
              {items.length} {items.length === 1 ? 'record' : 'records'}
            </span>
          </div>

          <div className="toolbar-right">
            <label htmlFor="reason-filter" className="filter-label">
              Filter by Reason:
            </label>
            <select
              id="reason-filter"
              className="reason-select"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            >
              {REASONS.map(r => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 3. Main Table Card */}
        <div className="table-card">
          {loading ? (
            <div className="table-status-message">
              <div className="spinner"></div>
              <span>Loading ledger disagreements...</span>
            </div>
          ) : items.length === 0 ? (
            <div className="empty-state">
              <div className="empty-state-icon">📋</div>
              <h3 className="empty-state-title">No disagreements found</h3>
              <p className="empty-state-desc">
                No ledger discrepancies detected for the selected tenant and reason filter.
              </p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="reconciliation-table">
                <thead>
                  <tr>
                    <th className="col-reason">Reason</th>
                    <th className="col-record">Record ID</th>
                    <th className="col-location">Location</th>
                    <th className="col-num">System A Value</th>
                    <th
                      className="col-num col-sortable"
                      onClick={handleSortCycle}
                      title="Click to cycle sort: Descending -> Ascending -> Default"
                    >
                      <span>System B Value</span>
                      {renderSortIndicator()}
                    </th>
                    <th className="col-num">Difference</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((row, idx) => {
                    const diffFormatted = computeDifference(row.a_value, row.b_value)
                    const aFormatted = formatAmount(row.a_value)
                    const bFormatted = formatAmount(row.b_value)

                    return (
                      <tr key={`${row.reason}-${row.record_id}-${idx}`}>
                        <td className="col-reason">
                          <span className={`reason-pill badge-${row.reason}`}>
                            {row.reason}
                          </span>
                        </td>
                        <td className="col-record">
                          <span className="record-id">{row.record_id}</span>
                        </td>
                        <td className="col-location">
                          <span className="location-tag">{row.location}</span>
                        </td>
                        <td className="col-num font-tabular">
                          {aFormatted}
                        </td>
                        <td className="col-num font-tabular">
                          {bFormatted}
                        </td>
                        <td className="col-num font-tabular font-semibold">
                          {diffFormatted}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
