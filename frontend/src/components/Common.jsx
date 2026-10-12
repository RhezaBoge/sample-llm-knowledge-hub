import { useState } from 'react'

export function Warnings({ warnings }) {
  if (!warnings) return null
  if (!warnings.length) {
    return <div className="notice success">All automatic checks passed. Still read the data once before saving.</div>
  }
  return (
    <div className="notice warning">
      <strong>Please check ({warnings.length})</strong>
      <ul>
        {warnings.map((w, i) => <li key={i}>{w}</li>)}
      </ul>
    </div>
  )
}

export function CodeBlock({ data, text }) {
  const [copied, setCopied] = useState(false)
  const content = text ?? JSON.stringify(data, null, 2)
  const copy = () => {
    navigator.clipboard?.writeText(content)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div className="code-wrap">
      <button type="button" className="btn small secondary copy" onClick={copy}>{copied ? 'Copied' : 'Copy'}</button>
      <pre className="code">{content}</pre>
    </div>
  )
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map(([key, label]) => (
        <button
          key={key}
          type="button"
          role="tab"
          aria-selected={active === key}
          className={active === key ? 'active' : ''}
          onClick={() => onChange(key)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

/** A button that asks "Are you sure?" inline instead of with a browser dialog. */
export function ConfirmButton({ label, question, confirmLabel, onConfirm, className = 'btn link danger small' }) {
  const [asking, setAsking] = useState(false)
  if (!asking) {
    return <button type="button" className={className} onClick={() => setAsking(true)}>{label}</button>
  }
  return (
    <span className="confirm">
      <span>{question}</span>
      <button type="button" className="btn small danger-solid" onClick={() => { setAsking(false); onConfirm() }}>
        {confirmLabel || 'Yes'}
      </button>
      <button type="button" className="btn small secondary" onClick={() => setAsking(false)}>Cancel</button>
    </span>
  )
}

export const formatNumber = (n) => (n === null || n === undefined || n === '' ? '—' : Number(n).toLocaleString('en-US'))
