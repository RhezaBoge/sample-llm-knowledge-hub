import { useEffect, useState } from 'react'
import { api } from '../api'
import { CodeBlock, Tabs, Warnings } from '../components/Common'
import ProjectMap from '../components/ProjectMap'
import RecordForm from '../components/RecordForm'

const toPoints = (locations) =>
  (locations || []).map((loc) => ({ lat: loc.latitude, lon: loc.longitude, label: loc.name, sub: loc.found }))

export default function AddProject({ template, editing, onSaved, onCancelEdit }) {
  const [text, setText] = useState('')
  const [filename, setFilename] = useState(null)
  const [method, setMethod] = useState('llm')
  const [busy, setBusy] = useState(null) // 'reading' | 'extracting' | 'saving'
  const [elapsed, setElapsed] = useState(0)
  const [error, setError] = useState(null)

  const [result, setResult] = useState(null) // what the extractor returned
  const [record, setRecord] = useState(null) // what the person is editing
  const [preview, setPreview] = useState(null) // live checks, map points and GeoJSON
  const [panel, setPanel] = useState('map')
  const [confirmed, setConfirmed] = useState(false)

  // Load an existing project when "Edit" was clicked in the knowledge base
  useEffect(() => {
    if (!editing) return
    setText(editing.source_text || '')
    setFilename(editing.source_filename)
    setRecord(editing.record)
    setResult({ method: editing.extraction_method, model: editing.model, extracted_at: editing.extracted_at })
    setConfirmed(false)
  }, [editing])

  // After the person stops typing, ask the backend to re-check the form, find the places and rebuild the GeoJSON
  useEffect(() => {
    if (!record) return
    const timer = setTimeout(() => api.preview(record).then(setPreview).catch(() => {}), 1200)
    return () => clearTimeout(timer)
  }, [record])

  // Stopwatch while the AI is working
  useEffect(() => {
    if (busy !== 'extracting') return
    setElapsed(0)
    const timer = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(timer)
  }, [busy])

  const run = async (kind, fn) => {
    setBusy(kind)
    setError(null)
    try {
      await fn()
    } catch (e) {
      setError({ message: e.message, rawOutput: e.rawOutput })
    } finally {
      setBusy(null)
    }
  }

  const uploadFile = (file) =>
    file &&
    run('reading', async () => {
      const doc = await api.readFile(file)
      setText(doc.text)
      setFilename(doc.filename)
    })

  const extract = () =>
    run('extracting', async () => {
      const res = await api.extract(text, method, filename)
      setResult(res)
      setRecord(res.record)
      setPreview({ warnings: res.warnings, geojson: res.geojson, locations: res.locations })
      setPanel('map')
      setConfirmed(false)
    })

  const save = () =>
    run('saving', async () => {
      const body = {
        record,
        source_text: text,
        source_filename: filename,
        extraction_method: result?.method || 'manual',
        model: result?.model,
        extracted_at: result?.extracted_at,
      }
      const saved = editing ? await api.updateProject(editing.id, body) : await api.createProject(body)
      reset()
      onSaved(saved)
    })

  const reset = () => {
    setText('')
    setFilename(null)
    setResult(null)
    setRecord(null)
    setPreview(null)
    setConfirmed(false)
    setError(null)
    onCancelEdit?.()
  }

  const startManually = () => {
    setResult({ method: 'manual' })
    setRecord(Object.fromEntries(template.fields.map((f) => [f.key, f.multiple ? [] : ''])))
  }

  if (!template) return <p className="muted">Loading…</p>

  return (
    <div className="stack">
      {editing && (
        <div className="notice info">
          Editing <strong>{editing.code}</strong> – {editing.title}. Saving will update the existing record.
        </div>
      )}

      {/* STEP 2 */}
      <section className="card">
        <div className="step-head">
          <span className="step-number">2</span>
          <div>
            <h2>Provide a project document</h2>
            <p className="muted">Upload a report, proposal or notes, or paste the text.</p>
          </div>
        </div>

        <div className="tip">
          <span className="tip-badge">Best choice</span>
          <div>
            <strong>Use a Markdown file (.md).</strong> It keeps headings, lists and tables as clean text, so the AI reads
            the document most accurately. PDFs often lose structure, and scanned PDFs have no text at all.
            <div className="muted small">
              Document in Google Drive? Open it in Google Docs and choose <em>File → Download → Markdown (.md)</em>.
            </div>
          </div>
        </div>

        <div className="row wrap">
          <label className="btn secondary file-btn">
            Upload file (.md, .docx, .pdf, .txt)
            <input type="file" accept=".md,.txt,.pdf,.docx" onChange={(e) => uploadFile(e.target.files[0])} hidden />
          </label>
          {filename && <span className="pill">{filename}</span>}
        </div>

        <textarea
          className="document"
          rows={10}
          placeholder="…or paste the text of a project document here."
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <p className="muted small">{text.length.toLocaleString()} characters</p>
      </section>

      {/* STEP 3 */}
      <section className="card">
        <div className="step-head">
          <span className="step-number">3</span>
          <div>
            <h2>Turn the text into structured data</h2>
            <p className="muted">
              The extractor fills in your {template.fields.length} fields: {template.fields.map((f) => f.label).join(', ')}.
            </p>
          </div>
        </div>

        <div className="method-options">
          <label className={`option ${method === 'llm' ? 'selected' : ''}`}>
            <input type="radio" name="method" checked={method === 'llm'} onChange={() => setMethod('llm')} />
            <span>
              <strong>AI language model (LLM)</strong>
              <span className="muted">Understands meaning and other languages. Can make mistakes. Slower.</span>
            </span>
          </label>
          <label className={`option ${method === 'rules' ? 'selected' : ''}`}>
            <input type="radio" name="method" checked={method === 'rules'} onChange={() => setMethod('rules')} />
            <span>
              <strong>Simple rules (no AI)</strong>
              <span className="muted">Looks for "Field name: value" lines and keywords. Fast but misses a lot. Good for comparison.</span>
            </span>
          </label>
        </div>

        <div className="row wrap">
          <button className="btn primary" disabled={!text.trim() || busy} onClick={extract}>
            {busy === 'extracting' ? `Reading the document… ${elapsed}s` : 'Extract structured data'}
          </button>
          <button className="btn link" disabled={busy} onClick={startManually}>or fill in the form manually</button>
        </div>
        {busy === 'extracting' && method === 'llm' && (
          <p className="muted small">A free model on a laptop can take 20–120 seconds. Larger models are slower but more accurate.</p>
        )}
        {error && (
          <div className="notice error">
            {error.message}
            {error.rawOutput && (
              <details>
                <summary>Show what the model answered</summary>
                <CodeBlock text={error.rawOutput} />
              </details>
            )}
          </div>
        )}
      </section>

      {/* STEP 4 */}
      {record && (
        <section className="card">
          <div className="step-head">
            <span className="step-number">4</span>
            <div>
              <h2>Review, correct and save</h2>
              <p className="muted">
                {result?.method === 'llm' && <>Extracted by <strong>{result.model}</strong>{result.seconds != null && <> in {result.seconds}s</>}. </>}
                {result?.method === 'rules' && <>Extracted with simple rules{result.seconds != null && <> in {result.seconds}s</>}. </>}
                A person is always responsible for the final data.
              </p>
            </div>
          </div>

          <Warnings warnings={preview?.warnings} />

          <div className="review-grid">
            <RecordForm fields={template.fields} separator={template.separator} record={record} onChange={setRecord} />

            <div className="review-side">
              <Tabs
                active={panel}
                onChange={setPanel}
                tabs={[
                  ['map', 'Map'],
                  ['geojson', 'GeoJSON'],
                  ['document', 'Document'],
                  ...(result?.raw_output ? [['raw', 'Raw AI answer']] : []),
                ]}
              />
              {panel === 'map' && (
                <>
                  <ProjectMap points={toPoints(preview?.locations)} height={360} />
                  <p className="muted small">Places come from the City and Country fields, located on OpenStreetMap. Edit those fields to move the points.</p>
                </>
              )}
              {panel === 'geojson' && (
                <>
                  <p className="muted small">This is exactly what will be stored. It updates as you edit the form.</p>
                  <CodeBlock data={preview?.geojson} />
                </>
              )}
              {panel === 'document' && <pre className="code document-view">{text || 'No document text.'}</pre>}
              {panel === 'raw' && (
                <>
                  <p className="muted small">The unedited answer from the extractor, before cleaning and validation.</p>
                  <CodeBlock text={result.raw_output} />
                </>
              )}
            </div>
          </div>

          <div className="save-bar">
            <label className="checkbox">
              <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
              I have checked this data against the document.
            </label>
            <div className="row">
              <button className="btn secondary" onClick={reset} disabled={busy}>Start over</button>
              <button className="btn primary" onClick={save} disabled={!confirmed || busy}>
                {busy === 'saving' ? 'Saving…' : editing ? 'Save changes' : 'Save to knowledge base'}
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  )
}
