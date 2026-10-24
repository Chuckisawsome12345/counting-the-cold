import type { Station } from '../types'

// Mock-mode stations (VITE_USE_MOCK=1), so the map has markers without a backend.
// Real CIMIS station metadata, copied from backend/data/stations.json. Not used outside mock mode.
export const MOCK_STATIONS: Station[] = [
  { id: 6, name: 'Davis', city: 'Davis', county: 'Yolo', lat: 38.535694, lon: -121.77636, elevation_ft: 60, active: true, connect_date: '1982-07-17', disconnect_date: null, group: 'core', validation: null },
  { id: 70, name: 'Manteca', city: 'Manteca', county: 'San Joaquin', lat: 37.834822, lon: -121.22319, elevation_ft: 33, active: true, connect_date: '1987-11-12', disconnect_date: null, group: 'core', validation: null },
  { id: 71, name: 'Modesto', city: 'Modesto', county: 'Stanislaus', lat: 37.645222, lon: -121.18776, elevation_ft: 35, active: true, connect_date: '1987-06-25', disconnect_date: null, group: 'core', validation: null },
  { id: 39, name: 'Parlier', city: 'Parlier', county: 'Fresno', lat: 36.597444, lon: -119.50404, elevation_ft: 337, active: true, connect_date: '1983-05-23', disconnect_date: null, group: 'core', validation: null },
  { id: 5, name: 'Shafter', city: 'Shafter', county: 'Kern', lat: 35.532556, lon: -119.28179, elevation_ft: 360, active: true, connect_date: '1982-06-01', disconnect_date: null, group: 'core', validation: null },
  { id: 12, name: 'Durham', city: 'Chico', county: 'Butte', lat: 39.608639, lon: -121.82443, elevation_ft: 130, active: false, connect_date: '1982-10-19', disconnect_date: '2025-07-30', group: 'durham', validation: null },
  { id: 244, name: 'Biggs', city: 'Biggs', county: 'Butte', lat: 39.386632, lon: -121.835278, elevation_ft: 72, active: true, connect_date: '2015-06-18', disconnect_date: null, group: 'durham-neighbor', validation: null },
  { id: 250, name: 'Williams', city: 'Williams', county: 'Colusa', lat: 39.210667, lon: -122.168889, elevation_ft: 69, active: true, connect_date: '2016-08-09', disconnect_date: null, group: 'durham-neighbor', validation: null },
  { id: 222, name: 'Gerber South', city: 'Gerber', county: 'Tehama', lat: 40.040006, lon: -122.154539, elevation_ft: 246, active: true, connect_date: '2014-08-13', disconnect_date: null, group: 'durham-neighbor', validation: null },
]
