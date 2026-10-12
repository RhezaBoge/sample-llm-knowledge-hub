import { useEffect, useState } from 'react'
import { api } from '../api'
import { CodeBlock, ConfirmButton } from '../components/Common'

const PIPELINE = [
  ['Set up fields', 'You decide which facts to collect and how to ask the AI for them'],
  ['Document', 'A report, proposal or notes (PDF, Word, text)'],
  ['AI extraction', 'A language model reads the text and answers in JSON'],
  ['Checks & map', 'Python cleans the values; places are found on OpenStreetMap'],
  ['Human review', 'A staff member checks and corrects every field'],
  ['Knowledge base', 'Saved in a SQL database as GeoJSON: map, search, download'],
]

const TYPE_LABELS = { text: 'Text', date: 'Date', number: 'Number' }

const slugify = (label) => {
  let key = label.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 40)
  if (!key || !/^[a-z]/.test(key)) key = `f_${key}`
  return key.slice(0, 40)
}

const emptyField = () => ({ label: '', key: '', prompt: '', type: 'text', multiple: false, _autoKey: true, _new: true })

export default function TemplateSetup({ template, onSaved }) {
  const [fields, setFields] = useState([])
  const [separator, setSeparator] = useState(';')
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [savedAt, setSavedAt] = useState(null)
  const [prompt, setPrompt] = useState(null)

  // Load the saved template into the editable draft
  useEffect(() => {
    if (!template) return
    setFields(template.fields.map((f) => ({ ...f, _autoKey: false })))
    setSeparator(template.separator)
    setDirty(false)
    setPrompt(null)
  }, [template])

  const change = (updater) => {
    setFields(updater)
    setDirty(true)
    setSavedAt(null)
    setPrompt(null)
  }

  const update = (index, patch) =>
    change((list) =>
      list.map((f, i) => {
        if (i !== index) return f
        const next = { ...f, ...patch }
        if ('label' in patch && f._autoKey) next.key = slugify(patch.label)
        if ('key' in patch) next._autoKey = false
        return next
      }),
    )
  const move = (index, dir) =>
    change((list) => {
      const next = [...list]
      const target = index + dir
      if (target < 0 || target >= next.length) return list
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  const remove = (index) => change((list) => list.filter((_, i) => i !== index))
  const add = () => change((list) => [...list, emptyField()])

  const payload = () => fields.map(({ _autoKey, _new, id, ...f }) => f)

  const run = async (fn) => {
    setBusy(true)
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const save = () =>
    run(async () => {
      const saved = await api.saveTemplate(payload(), separator)
      setSavedAt(new Date())
      onSaved(saved)
    })

  const reset = () =>
    run(async () => {
      onSaved(await api.resetTemplate())
    })

  const showPrompt = () =>
    run(async () => {
      setPrompt(await api.promptPreview(payload(), separator))
    })

  if (!template) return <p className="muted">Loading…</p>

  const mapKeys = template.map_keys || []
  const hasMap = mapKeys.every((k) => fields.some((f) => f.key === k))

  return (
    <div className="stack">
      <section className="card">
        <h2>How it works</h2>
        <p className="muted">
          Most NGOs hold years of knowledge inside documents. This tool shows how a small, free AI model can help turn
          those documents into <strong>one shared data format</strong>, so every project can be found, compared and mapped.
        </p>
        <ol className="pipeline">
          {PIPELINE.map(([title, text], i) => (
            <li key={title} className={i === 0 ? 'current' : ''}>
              <span className="step-number">{i + 1}</span>
              <strong>{title}</strong>
              <span className="muted small">{text}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="card">
        <div className="step-head">
          <span className="step-number">1</span>
          <div>
            <h2>Set up your fields</h2>
            <p className="muted">
              These are the facts collected from every document. Each field has its own instruction for the AI –
              change the wording and the AI changes what it looks for. Saved in the database, so the whole team uses the same template.
            </p>
          </div>
        </div>

        {template.projects > 0 && (
          <div className="notice info">
            {template.projects} project{template.projects === 1 ? '' : 's'} already saved with the current template.
            Existing values are kept; a new field stays empty for old projects until someone edits them.
          </div>
        )}

        <div className="fields-table">
          <div className="frow-header">
            <span />
            <span>Field name</span>
            <span>Key in JSON</span>
            <span>Type</span>
            <span>Values</span>
            <span />
          </div>
          {fields.map((f, i) => (
            <div key={f.id ?? `new-${i}`} className="frow">
              <div className="frow-main">
                <span className="field-index">{i + 1}</span>
                <input value={f.label} placeholder="e.g. Donor" aria-label="Field name" onChange={(e) => update(i, { label: e.target.value })} />
                <input className="mono" value={f.key} placeholder="donor" aria-label="Key" onChange={(e) => update(i, { key: e.target.value })} />
                <select value={f.type} aria-label="Type" onChange={(e) => update(i, { type: e.target.value })}>
                  {template.types.map((t) => <option key={t} value={t}>{TYPE_LABELS[t] || t}</option>)}
                </select>
                <label className="toggle" title={`Several values, separated by "${separator}"`}>
                  <input type="checkbox" checked={!!f.multiple} onChange={(e) => update(i, { multiple: e.target.checked })} />
                  Several values
                </label>
                <div className="frow-actions">
                  <button type="button" className="icon-btn" title="Move up" disabled={i === 0} onClick={() => move(i, -1)}>↑</button>
                  <button type="button" className="icon-btn" title="Move down" disabled={i === fields.length - 1} onClick={() => move(i, 1)}>↓</button>
                  <button type="button" className="icon-btn danger" title="Remove field" onClick={() => remove(i)}>✕</button>
                </div>
              </div>
              <div className="frow-prompt">
                <span />
                <span className="frow-prompt-label">AI instruction</span>
                <div className="frow-prompt-row">
                  <textarea
                    rows={1}
                    value={f.prompt}
                    placeholder="What should the AI look for? e.g. The organization that gives the money for the project."
                    onChange={(e) => update(i, { prompt: e.target.value })}
                  />
                  {mapKeys.includes(f.key) && <span className="tag" title="This field places the project on the map">map</span>}
                </div>
              </div>
            </div>
          ))}
        </div>

        <div className="toolbar">
          <button type="button" className="btn secondary small" onClick={add}>+ Add a field</button>
          <label className="separator-setting">
            <span>Separator for several values</span>
            <input className="mono" value={separator} maxLength={3} onChange={(e) => { setSeparator(e.target.value); setDirty(true); setPrompt(null) }} />
          </label>
        </div>

        {!hasMap && (
          <p className="notice warning" style={{ marginTop: 12 }}>
            The map needs fields with the keys <code>{mapKeys.join('</code> and <code>')}</code>. Without them, projects are saved but not shown on the map.
          </p>
        )}
        {error && <div className="notice error">{error}</div>}

        <div className="save-bar">
          <span className="muted small">
            {dirty ? 'You have unsaved changes.' : savedAt ? `Saved at ${savedAt.toLocaleTimeString()}.` : 'The team uses this template for every new document.'}
          </span>
          <div className="row wrap">
            <ConfirmButton
              label="Reset to default fields"
              question="Replace your fields with the 8 default ones?"
              confirmLabel="Yes, reset"
              onConfirm={reset}
              className="btn link small"
            />
            <button type="button" className="btn secondary" disabled={busy} onClick={showPrompt}>Show the AI prompt</button>
            <button type="button" className="btn primary" disabled={!dirty || busy} onClick={save}>
              {busy ? 'Saving…' : 'Save template'}
            </button>
          </div>
        </div>

        {prompt && (
          <div className="stack-small">
            <p className="muted small">
              This is the exact text the AI receives for every document (the document itself replaces the placeholder at the end).
              Your field instructions appear under "What each key means".
            </p>
            <CodeBlock text={`SYSTEM:\n${prompt.system}\n\nUSER:\n${prompt.user}`} />
          </div>
        )}
      </section>

      <section className="card">
        <h2>What is stored</h2>
        <p className="muted">
          Each project becomes one <a href="https://geojson.org" target="_blank" rel="noreferrer">GeoJSON</a> Feature: the
          fields above are its <em>properties</em>, and the places found for <code>city</code> / <code>country</code> are its{' '}
          <em>geometry</em>. GeoJSON opens in QGIS, ArcGIS, Google Earth, geojson.io and most web maps.
          Note that GeoJSON writes coordinates as <code>[longitude, latitude]</code>.
        </p>
        <CodeBlock
          data={{
            type: 'Feature',
            id: 'PRJ-0001',
            geometry: { type: 'Point', coordinates: [120.2641, -9.6567] },
            properties: Object.fromEntries([
              ['project_id', 'PRJ-0001'],
              ...fields.map((f) => [f.key || '?', f.multiple ? [`<${f.label || 'value'} 1>`, `<${f.label || 'value'} 2>`] : `<${f.label || 'value'}>`]),
              ['locations', [{ name: 'Waingapu', latitude: -9.6567, longitude: 120.2641 }]],
              ['source', { document: 'report.pdf', extraction_method: 'llm', model: 'qwen2.5:3b', reviewed_by_human: true }],
            ]),
          }}
        />
      </section>
    </div>
  )
}
