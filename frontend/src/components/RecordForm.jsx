// The review form, built from the template: one input per field.
// A person checks and corrects what the AI extracted.
import { asText } from '../api'

const TYPE_HINTS = {
  date: 'YYYY-MM-DD, YYYY-MM or YYYY',
  number: 'A plain number',
  text: '',
}

export default function RecordForm({ fields, separator, record, onChange }) {
  const set = (key) => (e) => onChange({ ...record, [key]: e.target.value })

  return (
    <div className="form-grid">
      {fields.map((f, i) => {
        const value = asText(record[f.key], separator)
        const hint = [f.multiple ? `Several values: separate with "${separator}"` : '', TYPE_HINTS[f.type]].filter(Boolean).join(' · ')
        const long = f.type === 'text' && !f.multiple && i > 0
        return (
          <label key={f.key} className={`field ${long || i === 0 ? 'wide' : ''}`}>
            <span className="field-label">{f.label}</span>
            {long ? (
              <textarea rows={2} value={value} onChange={set(f.key)} />
            ) : (
              <input inputMode={f.type === 'number' ? 'decimal' : undefined} value={value} onChange={set(f.key)} />
            )}
            {hint && <span className="field-hint">{hint}</span>}
          </label>
        )
      })}
    </div>
  )
}
