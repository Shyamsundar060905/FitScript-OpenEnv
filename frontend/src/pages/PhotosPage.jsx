import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../hooks/useAuth'
import { api } from '../lib/api'
import Container from '../components/Container'
import PageHeader from '../components/PageHeader'
import { Upload, Trash2, Image as ImageIcon, AlertCircle, Calendar, Scale } from 'lucide-react'
import { format, parseISO } from 'date-fns'
import clsx from 'clsx'

export default function PhotosPage() {
  const { profile } = useAuth()
  const [photos,    setPhotos]    = useState([])
  const [loading,   setLoading]   = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error,     setError]     = useState('')
  const [dragging,  setDragging]  = useState(false)

  const today = new Date().toISOString().slice(0, 10)
  const [file,   setFile]   = useState(null)
  const [weight, setWeight] = useState(profile?.weight_kg ?? 70)
  const [note,   setNote]   = useState('')
  const [date,   setDate]   = useState(today)
  const inputRef = useRef(null)

  useEffect(() => { loadPhotos() }, [])

  async function loadPhotos() {
    setLoading(true)
    try {
      const data = await api.listPhotos()
      setPhotos(data ?? [])
    } catch (ex) { setError(ex.detail ?? 'Failed to load photos') }
    finally { setLoading(false) }
  }

  async function handleUpload(e) {
    e?.preventDefault()
    if (!file) { setError('Please select a photo first'); return }
    setError(''); setUploading(true)

    const formData = new FormData()
    formData.append('file', file)
    formData.append('date', date)
    formData.append('weight_kg', String(weight))
    formData.append('note', note)

    try {
      await api.uploadPhoto(formData)
      setFile(null); setNote('')
      if (inputRef.current) inputRef.current.value = ''
      await loadPhotos()
    } catch (ex) { setError(ex.detail ?? 'Upload failed') }
    finally { setUploading(false) }
  }

  async function handleDelete(photo_id) {
    if (!confirm('Delete this photo? This cannot be undone.')) return
    try {
      await api.deletePhoto(photo_id)
      setPhotos(prev => prev.filter(p => p.id !== photo_id))
    } catch (ex) { setError(ex.detail ?? 'Delete failed') }
  }

  function handleDrop(e) {
    e.preventDefault(); setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) setFile(f)
  }

  const token = typeof window !== 'undefined' ? localStorage.getItem('fa_token') : ''
  const fileUrl = (id) => `${api.photoFile(id)}?token=${token}`

  return (
    <Container size="lg">
      <PageHeader
        eyebrow="Visual tracking"
        title="Progress photos"
        description="Private visual record of your physique changes. Photos never leave your account."
      />

      {error && (
        <div className="flex items-start gap-2 bg-clay-50 text-clay-600 text-[13px] px-3 py-2.5 rounded-lg mb-5"
             style={{ boxShadow: 'inset 0 0 0 0.5px rgba(216, 100, 58, 0.35)' }}>
          <AlertCircle size={14} className="mt-0.5" /><span>{error}</span>
        </div>
      )}

      {/* Upload card */}
      <form onSubmit={handleUpload} className="card p-6 mb-6">
        <p className="eyebrow mb-1">Upload</p>
        <h2 className="section-title mb-5">Add a new photo</h2>

        {/* Drag-drop zone */}
        <label
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={clsx(
            'block rounded-xl p-6 mb-4 text-center cursor-pointer transition-all duration-150',
            dragging ? 'bg-sage-50' : 'bg-paper-100 hover:bg-paper-200'
          )}
          style={{
            boxShadow: dragging
              ? 'inset 0 0 0 1.5px rgba(107, 151, 55, 0.6)'
              : 'inset 0 0 0 1px dashed rgba(28, 26, 20, 0.12)',
            backgroundImage: dragging
              ? 'none'
              : 'repeating-linear-gradient(0deg, transparent, transparent 4px, rgba(28,26,20,0.02) 4px, rgba(28,26,20,0.02) 8px)'
          }}
        >
          <input
            ref={inputRef} type="file"
            accept="image/jpeg,image/png,image/webp,image/heic"
            onChange={e => setFile(e.target.files?.[0] ?? null)}
            className="hidden"
          />
          <Upload size={22} className="mx-auto text-ink-400 mb-2" strokeWidth={1.5} />
          <p className="text-[13.5px] font-medium text-ink-700">
            {file ? file.name : 'Click or drop an image here'}
          </p>
          <p className="text-[11px] text-ink-400 mt-1">
            JPG · PNG · WebP · HEIC — up to 10MB
          </p>
        </label>

        <div className="grid md:grid-cols-[1fr_1fr_2fr] gap-4 mb-5">
          <div>
            <label className="label"><Calendar size={10} className="inline mr-1" />Date</label>
            <input type="date" className="input tnum" value={date} onChange={e => setDate(e.target.value)} />
          </div>
          <div>
            <label className="label"><Scale size={10} className="inline mr-1" />Weight · kg</label>
            <input type="number" step={0.1} className="input tnum"
                   value={weight} onChange={e => setWeight(Number(e.target.value))} />
          </div>
          <div>
            <label className="label">Caption — optional</label>
            <input className="input" placeholder="e.g. Front view · 4 weeks in"
                   value={note} onChange={e => setNote(e.target.value)} />
          </div>
        </div>

        <button type="submit" disabled={uploading || !file} className="btn-primary">
          <Upload size={14} />
          {uploading ? 'Uploading…' : 'Save photo'}
        </button>
      </form>

      {/* Gallery */}
      <div className="card p-6">
        <div className="flex items-baseline justify-between mb-5">
          <div>
            <p className="eyebrow mb-1">Gallery</p>
            <h2 className="section-title">
              All photos
              {photos.length > 0 && (
                <span className="text-ink-400 font-normal ml-2 text-[12px]">· {photos.length}</span>
              )}
            </h2>
          </div>
        </div>

        {loading ? (
          <div className="h-48 flex items-center justify-center">
            <div className="w-6 h-6 rounded-full border-2 border-sage-500 border-t-transparent animate-spin" />
          </div>
        ) : photos.length === 0 ? (
          <div className="py-12 text-center flex flex-col items-center gap-3">
            <div className="w-14 h-14 rounded-xl bg-paper-200 flex items-center justify-center">
              <ImageIcon size={20} className="text-ink-300" />
            </div>
            <p className="text-[13.5px] text-ink-500">
              No photos yet. Upload one above to start your visual record.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {photos.map(photo => (
              <div key={photo.id}
                   className="rounded-xl overflow-hidden bg-white group relative"
                   style={{ boxShadow: 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)' }}>
                <div className="aspect-[3/4] bg-paper-100 overflow-hidden">
                  <img src={fileUrl(photo.id)} alt={`Progress ${photo.date}`}
                       className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
                       loading="lazy"
                       onError={e => { e.target.style.display = 'none' }} />
                </div>
                <div className="p-3 flex items-start justify-between gap-2">
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] font-semibold text-ink-800 tnum">
                      {format(parseISO(photo.date), 'MMM d, yyyy')}
                    </p>
                    {photo.weight_kg > 0 && (
                      <p className="text-[11.5px] text-ink-500 mt-0.5 tnum">{photo.weight_kg} kg</p>
                    )}
                    {photo.note && (
                      <p className="text-[11.5px] text-ink-400 mt-1 italic line-clamp-2">{photo.note}</p>
                    )}
                  </div>
                  <button onClick={() => handleDelete(photo.id)}
                          className="p-1.5 text-ink-300 hover:text-clay-500 hover:bg-clay-50 rounded-md transition-colors opacity-0 group-hover:opacity-100">
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Container>
  )
}
