import { useEffect, useState } from 'react'
import { api } from './api'
import AddProject from './pages/AddProject'
import KnowledgeBase from './pages/KnowledgeBase'
import TemplateSetup from './pages/TemplateSetup'

function ModelStatus({ health }) {
  if (!health) return <span className="model-status">Checking AI model…</span>
  const { llm } = health
  let state = 'ok'
  let text = `AI model ready: ${llm.model}`
  if (!llm.reachable) {
    state = 'off'
    text = 'AI model offline – "Simple rules" still works'
  } else if (llm.model_available === false) {
    state = 'warn'
    text = `Model ${llm.model} is still downloading`
  }
  return (
    <span className={`model-status ${state}`} title={llm.base_url}>
      <span className="dot" />
      {text}
    </span>
  )
}

const PAGES = [
  ['setup', 'Set up your fields'],
  ['add', 'Add a project'],
  ['kb', 'Knowledge base'],
]

// The current page is kept in the URL (#setup, #add, #kb) so a refresh stays on it
const pageFromUrl = () => {
  const hash = window.location.hash.slice(1)
  return PAGES.some(([key]) => key === hash) ? hash : 'setup'
}

export default function App() {
  const [page, setPageState] = useState(pageFromUrl)
  const setPage = (key) => {
    window.location.hash = key
    setPageState(key)
  }
  const [template, setTemplate] = useState(null)
  const [health, setHealth] = useState(null)
  const [selectedId, setSelectedId] = useState(null)
  const [editing, setEditing] = useState(null)

  const loadTemplate = () => api.template().then(setTemplate).catch(() => {})

  useEffect(() => {
    loadTemplate()
    const onHash = () => setPageState(pageFromUrl())
    window.addEventListener('hashchange', onHash) // back/forward buttons and typed URLs
    const check = () => api.health().then(setHealth).catch(() => setHealth({ llm: { reachable: false } }))
    check()
    const timer = setInterval(check, 15000)
    return () => {
      clearInterval(timer)
      window.removeEventListener('hashchange', onHash)
    }
  }, [])

  return (
    <>
      <header className="header">
        <div className="container header-inner">
          <div className="brand">
            <span className="logo" aria-hidden="true" />
            <div>
              <strong>Project Knowledge Hub</strong>
              <span className="muted small">From project documents to structured, mappable data</span>
            </div>
          </div>
          <ModelStatus health={health} />
        </div>
        <nav className="container nav">
          {PAGES.map(([key, label], i) => (
            <button key={key} className={page === key ? 'active' : ''} onClick={() => setPage(key)}>
              <span className="step">{i + 1}</span>
              {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="container">
        {page === 'setup' && <TemplateSetup template={template} onSaved={setTemplate} />}
        {page === 'add' && (
          <AddProject
            template={template}
            editing={editing}
            onCancelEdit={() => setEditing(null)}
            onSaved={(project) => {
              setEditing(null)
              setSelectedId(project.id)
              loadTemplate() // the project count shown on the setup page changed
              setPage('kb')
            }}
          />
        )}
        {page === 'kb' && (
          <KnowledgeBase
            template={template}
            selectedId={selectedId}
            onSelect={setSelectedId}
            onAdd={() => setPage('add')}
            onEdit={(project) => {
              setEditing(project)
              setPage('add')
            }}
          />
        )}
      </main>

      <footer className="container footer muted small">
        Project Knowledge Hub · a sample of using a local LLM for knowledge management · Sample documents are fictional.
      </footer>
    </>
  )
}
