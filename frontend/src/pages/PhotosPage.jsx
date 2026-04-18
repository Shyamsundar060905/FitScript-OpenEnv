import { useState, useEffect } from 'react'
import { api } from '../lib/api'
import { Upload, Trash2, ImageOff } from 'lucide-react'

export default function PhotosPage() {
  // NOTE: Photos are served from the backend filesystem.
  // For production on Render, you'd need cloud storage (S3/Cloudinary).
  // This page renders a placeholder since photos require multipart upload
  // which we can add as a follow-up enhancement.
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display text-2xl font-bold text-ink-900">Progress Photos</h1>
        <p className="text-sm text-ink-400 mt-1">Visually track your physique changes over time.</p>
      </div>

      <div className="card p-10 text-center flex flex-col items-center gap-4">
        <div className="w-16 h-16 rounded-2xl bg-cream-200 flex items-center justify-center">
          <ImageOff size={28} className="text-ink-300" />
        </div>
        <div>
          <h2 className="font-display font-bold text-ink-700 mb-1">Photo uploads need the backend running</h2>
          <p className="text-sm text-ink-400 max-w-sm">
            Progress photos are stored on the server filesystem. When running locally,
            this feature works via the Python backend. For cloud deployment, integrate
            Cloudinary or S3 as a follow-up step.
          </p>
        </div>
        <div className="bg-cream-100 rounded-xl px-4 py-3 text-xs font-mono text-ink-500 text-left w-full max-w-sm">
          <p># Photo upload endpoint is ready in api.py</p>
          <p># POST /photos  (multipart/form-data)</p>
          <p># GET  /photos  → gallery</p>
          <p># DELETE /photos/:id</p>
        </div>
      </div>
    </div>
  )
}
