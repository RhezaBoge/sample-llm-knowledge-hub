import { useEffect, useState } from 'react'
import { api, asText } from '../api'
import { CodeBlock, ConfirmButton, formatNumber, Tabs } from '../components/Common'
import ProjectMap from '../components/ProjectMap'

function Stat({ label, value }) {
  return (
    <div className="stat">
      <span className="stat-value">{value}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

function Detail({ project, template, onEdit, onDelete }) {
  const [tab, setTab] = useState('overview')
  const r = project.record || {}
  const method = project.extraction_method === 'llm' ? `AI model (${project.model})` : project.extraction_method

  return (
    <div className="card detail">
      <div className="detail-head">
        <span className="muted small">{project.code}</span>
        <h2>{project.title}</h2>
      </div>

      <Tabs active={tab} onChange={setTab} tabs={[['overview', 'Overview'], ['geojson', 'GeoJSON'], ['source', 'Source document']]} />

      {tab === 'overview' && (
        <dl className="facts">
          {template.fields.filter((f) => f.key !== 'title').map((f) => (
            <div key={f.key}>
              <dt>{f.label}</dt>
              <dd>{asText(r[f.key], template.separator) || '—'}</dd>
            </div>
          ))}
          <div>
            <dt>On the map</dt>
            <dd>{project.locations?.length ? project.locations.map((l) => l.name).join(', ') : '—'}</dd>
          </div>
          <div>
            <dt>Source</dt>
            <dd>{[project.source_filename, method].filter(Boolean).join(' · ') || '—'}</dd>
          </div>
        </dl>
      )}
      {tab === 'geojson' && <CodeBlock data={project.geojson} />}
      {tab === 'source' && <pre className="code document-view">{project.source_text || 'No source text stored.'}</pre>}

      <div className="row wrap">
        <a className="btn primary small" href={api.projectGeojsonUrl(project.id)}>Download GeoJSON</a>
        <button className="btn secondary small" onClick={() => onEdit(project)}>Edit</button>
        <ConfirmButton label="Delete" question="Delete this project?" confirmLabel="Yes, delete" onConfirm={() => onDelete(project)} />
      </div>
    </div>
  )
}

export default function KnowledgeBase({ template, selectedId, onSelect, onEdit, onAdd }) {
  const [filters, setFilters] = useState({ q: '', country: '' })
  const [projects, setProjects] = useState(null)
  const [stats, setStats] = useState(null)
  const [detail, setDetail] = useState(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    api.stats().then(setStats).catch(() => {})
  }, [reload])

  useEffect(() => {
    const timer = setTimeout(() => api.listProjects(filters).then(setProjects).catch(() => setProjects([])), 250)
    return () => clearTimeout(timer)
  }, [filters, reload])

  useEffect(() => {
    if (!selectedId) return setDetail(null)
    api.getProject(selectedId).then(setDetail).catch(() => setDetail(null))
  }, [selectedId, reload])

  const remove = async (project) => {
    await api.deleteProject(project.id)
    onSelect(null)
    setReload((n) => n + 1)
  }

  const setFilter = (key) => (e) => setFilters({ ...filters, [key]: e.target.value })

  // Table columns: the title plus the next three fields of the template
  const columns = (template?.fields || []).filter((f) => f.key !== 'title').slice(0, 3)
  const points = (projects || []).flatMap((p) =>
    (p.locations || []).map((l) => ({ id: p.id, lat: l.latitude, lon: l.longitude, label: p.title, sub: l.name })),
  )

  if (!template) return <p className="muted">Loading…</p>

  if (stats && stats.projects === 0) {
    return (
      <div className="card empty">
        <h2>The knowledge base is empty</h2>
        <p className="muted">Add your first project document and let the AI turn it into structured data.</p>
        <button className="btn primary" onClick={onAdd}>Add a project</button>
      </div>
    )
  }

  return (
    <div className="stack">
      {stats && (
        <div className="stats">
          <Stat label="Projects" value={formatNumber(stats.projects)} />
          <Stat label="Countries" value={formatNumber(stats.countries.length)} />
          <Stat label="Places on the map" value={formatNumber(stats.places)} />
        </div>
      )}

      <div className="card filters">
        <input type="search" placeholder="Search all fields and documents…" value={filters.q} onChange={setFilter('q')} />
        <select value={filters.country} onChange={setFilter('country')} aria-label="Country">
          <option value="">All countries</option>
          {stats?.countries.map((c) => <option key={c.name} value={c.name}>{c.name} ({c.count})</option>)}
        </select>
        <a className="btn secondary" href={api.allGeojsonUrl(filters)}>Download all as GeoJSON</a>
      </div>

      <div className="card no-pad">
        <ProjectMap points={points} height={380} onSelect={onSelect} />
      </div>

      <div className={`kb-grid ${detail ? 'with-detail' : ''}`}>
        <div className="card no-pad table-scroll">
          <table className="projects">
            <thead>
              <tr>
                <th>Project</th>
                {columns.map((c) => <th key={c.key}>{c.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {projects?.map((p) => (
                <tr key={p.id} className={p.id === selectedId ? 'selected' : ''} onClick={() => onSelect(p.id)}>
                  <td>
                    <strong>{p.title}</strong>
                    <div className="muted small">{p.code}</div>
                  </td>
                  {columns.map((c) => <td key={c.key}>{asText(p.record?.[c.key], template.separator) || '—'}</td>)}
                </tr>
              ))}
              {projects?.length === 0 && (
                <tr>
                  <td colSpan={columns.length + 1} className="muted">No projects match these filters.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {detail && <Detail key={detail.id} project={detail} template={template} onEdit={onEdit} onDelete={remove} />}
      </div>
    </div>
  )
}
