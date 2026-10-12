import { useEffect } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

// Zoom the map so every point is visible whenever the points change.
function FitToPoints({ points }) {
  const map = useMap()
  const key = points.map((p) => `${p.lat},${p.lon}`).join('|')
  useEffect(() => {
    if (points.length === 1) map.setView([points[0].lat, points[0].lon], 8)
    else if (points.length > 1) map.fitBounds(points.map((p) => [p.lat, p.lon]), { padding: [30, 30], maxZoom: 9 })
  }, [key]) // eslint-disable-line react-hooks/exhaustive-deps
  return null
}

/**
 * points: [{ lat, lon, label, sub, color, id }]
 */
export default function ProjectMap({ points, height = 360, onSelect }) {
  const valid = points.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon))

  return (
    <div className="map" style={{ height }}>
      <MapContainer center={[5, 40]} zoom={2} scrollWheelZoom={false} style={{ height: "100%" }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {valid.map((p, i) => (
          <CircleMarker
            key={`${p.id ?? ''}-${i}`}
            center={[p.lat, p.lon]}
            radius={8}
            pathOptions={{ color: '#ffffff', weight: 2, fillColor: p.color || '#0b6bcb', fillOpacity: 0.9 }}
            eventHandlers={onSelect && p.id ? { click: () => onSelect(p.id) } : {}}
          >
            <Popup>
              <strong>{p.label}</strong>
              {p.sub && <div>{p.sub}</div>}
            </Popup>
          </CircleMarker>
        ))}
        <FitToPoints points={valid} />
      </MapContainer>
      {!valid.length && <div className="map-empty">No coordinates to show yet</div>}
    </div>
  )
}
