import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import { Upload, Trash2, Image as ImageIcon, AlertCircle } from 'lucide-react'
import { format, parseISO } from 'date-fns'

export default function PhotosPage() {
  const { profile } = useAuth()
  const [photos,    setPhotos]    = useState([])
  const [loading,   setLoading]   = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error,     setError]     = useState('')

  // Upload form state
  const today = new Date().toISOString().slice(0, 10)
  const [file,       setFile]       = useState(null)
  const [weight,     setWeight]     = useState(profile?.weight_kg ?? 70)
  const [note,       setNote]       = useState('')
  const [date,       setDate]       = useState(today)

  useEffect(() => { loadPhotos() }, [])

  async function loadPhotos() {
    setLoading(true)
    try {
      const data = await api.listPhotos()
      setPhotos(data ?? [])
    } catch (ex) {
      setError(ex.detail ?? 'Failed to load photos')
    } finally {
      setLoading(false)
    }
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) { setError('Please select a photo first'); return }
    setError(''); setUploading(true)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('date', date)
    formData.append('weight_kg', String(weight))
    formData.append('note', note)

    try {
      await api.uploadPhoto(formData)
      // Reset form
      setFile(null); setNote('')
      document.getElementById('photo-input').value = ''
      await loadPhotos()
    } catch (ex) {
      setError(ex.detail ?? 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  async function handleDelete(photo_id) {
    if (!confirm('Delete this photo? This cannot be undone.')) return
    try {
      await api.deletePhoto(photo_id)
      setPhotos(prev => prev.filter(p => p.id !== photo_id))
    } catch (ex) {
      setError(ex.detail ?? 'Delete failed')
    }
  }

  // Build auth'd image URLs — token goes in query string because <img> can't send headers
  const token = localStorage.getItem('fa_token')
  const fileUrl = (id) => `${api.photoFile(id)}?token=${token}`

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-bold text-ink-900">Progress Photos</h1>
        <p className="text-sm text-ink-400 mt-1">
          Visually track your physique changes over time. Photos are stored privately.
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2.5 rounded-xl mb-5">
          <AlertCircle size={15} /><span>{error}</span>
        </div>
      )}

      {/* Upload form */}
      <form onSubmit={handleUpload} className="card p-6 mb-6">
        <h2 className="font-display font-bold text-ink-800 mb-4">Upload a new photo</h2>

        <div className="grid md:grid-cols-[2fr_1fr_1fr] gap-4 mb-4">
          <div>
            <label className="label">Photo file</label>
            <input
              id="photo-input"
              type="file"
              accept="image/jpeg,image/png,image/webp,image/heic"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-ink-600 file:mr-4 file:py-2 file:px-4
                file:rounded-xl file:border file:border-cream-400
                file:text-sm file:font-medium file:bg-white file:text-ink-700
                hover:file:bg-cream-100 file:cursor-pointer"
            />
            <p className="text-xs text-ink-400 mt-1">Max 10MB. JPG, PNG, WebP, or HEIC.</p>
          </div>
          <div>
            <label className="label">Date</label>
            <input type="date" className="input" value={date} onChange={e => setDate(e.target.value)} />
          </div>
          <div>
            <label className="label">Weight (kg)</label>
            <input
              type="number" step={0.1}
              className="input"
              value={weight}
              onChange={e => setWeight(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="mb-4">
          <label className="label">Note (optional)</label>
          <input
            className="input"
            placeholder="e.g. Front view · 4 weeks in"
            value={note}
            onChange={e => setNote(e.target.value)}
          />
        </div>

        <button
          type="submit"
          disabled={uploading || !file}
          className="btn-primary flex items-center gap-2"
        >
          <Upload size={15} />
          {uploading ? 'Uploading…' : 'Save Photo'}
        </button>
      </form>

      {/* Gallery */}
      <div className="card p-6">
        <h2 className="font-display font-bold text-ink-800 mb-4">Gallery</h2>

        {loading ? (
          <div className="h-40 flex items-center justify-center">
            <div className="w-6 h-6 rounded-full border-2 border-sage-500 border-t-transparent animate-spin" />
          </div>
        ) : photos.length === 0 ? (
          <div className="py-10 text-center flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-2xl bg-cream-200 flex items-center justify-center">
              <ImageIcon size={24} className="text-ink-300" />
            </div>
            <p className="text-sm text-ink-400">
              No photos yet. Upload one above to start tracking visually.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {photos.map(photo => (
              <div key={photo.id} className="rounded-2xl overflow-hidden border border-cream-400 bg-white">
                <div className="aspect-[3/4] bg-cream-100 overflow-hidden">
                  <img
                    src={fileUrl(photo.id)}
                    alt={`Progress ${photo.date}`}
                    className="w-full h-full object-cover"
                    loading="lazy"
                    onError={e => { e.target.style.display = 'none' }}
                  />
                </div>
                <div className="p-3">
                  <p className="text-sm font-semibold text-ink-800">
                    {format(parseISO(photo.date), 'MMM d, yyyy')}
                  </p>
                  {photo.weight_kg > 0 && (
                    <p className="text-xs text-ink-500 mt-0.5">{photo.weight_kg} kg</p>
                  )}
                  {photo.note && (
                    <p className="text-xs text-ink-400 mt-1 italic line-clamp-2">{photo.note}</p>
                  )}
                  <button
                    onClick={() => handleDelete(photo.id)}
                    className="mt-2 text-xs text-red-500 hover:text-red-700 flex items-center gap-1 transition-colors"
                  >
                    <Trash2 size={12} /> Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}