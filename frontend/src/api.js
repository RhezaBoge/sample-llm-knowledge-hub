// All calls to the FastAPI backend. Vite forwards /api/* to the backend.

async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, options)
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    const error = new Error(data?.detail || `Request failed (${res.status})`)
    error.rawOutput = data?.raw_output
    throw error
  }
  return data
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

const query = (params = {}) => {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v))
  const qs = new URLSearchParams(clean).toString()
  return qs ? `?${qs}` : ''
}

export const api = {
  health: () => request('/health'),
  samples: () => request('/samples'),
  sample: (name) => request(`/samples/${encodeURIComponent(name)}`),

  // Step 0: the template
  template: () => request('/template'),
  saveTemplate: (fields, separator) => request('/template', json('PUT', { fields, separator })),
  resetTemplate: () => request('/template/reset', { method: 'POST' }),
  promptPreview: (fields, separator) => request('/template/prompt', json('POST', { fields, separator })),

  // Steps 1-3: document -> data
  readFile: (file) => {
    const form = new FormData()
    form.append('file', file)
    return request('/read-file', { method: 'POST', body: form })
  },
  extract: (text, method, filename) => request('/extract', json('POST', { text, method, filename })),
  preview: (record) => request('/preview', json('POST', { record })),

  // The knowledge base
  listProjects: (filters) => request(`/projects${query(filters)}`),
  getProject: (id) => request(`/projects/${id}`),
  createProject: (body) => request('/projects', json('POST', body)),
  updateProject: (id, body) => request(`/projects/${id}`, json('PUT', body)),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),
  stats: () => request('/stats'),

  projectGeojsonUrl: (id) => `/api/projects/${id}/geojson`,
  allGeojsonUrl: (filters) => `/api/geojson${query(filters)}`,
}

/** Show a stored value as text: lists are joined with the separator. */
export const asText = (value, separator = ';') =>
  Array.isArray(value) ? value.join(`${separator} `) : value ?? ''
