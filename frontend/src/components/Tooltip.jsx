import { useState, useRef, useEffect } from 'react'
import { Info } from 'lucide-react'

/**
 * Tooltip
 *
 * Compact info-icon button that reveals a content panel on hover (desktop)
 * or tap (mobile). Used to show exercise/food reasoning inline on the Plan page.
 *
 * Content prop shape:
 *   <Tooltip content={<div>...</div>} label="Why this?" />
 */
export default function Tooltip({ content, label = '', position = 'top' }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  // Close when clicking outside
  useEffect(() => {
    if (!open) return
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const positions = {
    top:    'bottom-full mb-2 left-1/2 -translate-x-1/2',
    right:  'left-full ml-2 top-1/2 -translate-y-1/2',
    bottom: 'top-full mt-2 left-1/2 -translate-x-1/2',
    left:   'right-full mr-2 top-1/2 -translate-y-1/2',
  }

  return (
    <span ref={ref} className="relative inline-flex items-center">
      <button
        type="button"
        onClick={(e) => { e.stopPropagation(); setOpen(o => !o) }}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        className="inline-flex items-center justify-center w-4 h-4 rounded-full
                   text-ink-300 hover:text-clay-500 hover:bg-clay-50 transition-colors
                   focus:outline-none focus:ring-2 focus:ring-sage-500/30"
        aria-label={label || 'More info'}
      >
        <Info size={11} strokeWidth={2} />
      </button>

      {open && (
        <div
          className={`absolute z-50 ${positions[position]} w-[260px] pointer-events-none animate-fade-in`}
          role="tooltip"
        >
          <div className="bg-ink-800 text-paper-50 rounded-lg p-3 shadow-float text-[11.5px] leading-relaxed pointer-events-auto">
            {content}
            {/* Arrow */}
            {position === 'top' && (
              <div className="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0
                              border-l-[6px] border-r-[6px] border-t-[6px]
                              border-l-transparent border-r-transparent border-t-ink-800" />
            )}
            {position === 'bottom' && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 w-0 h-0
                              border-l-[6px] border-r-[6px] border-b-[6px]
                              border-l-transparent border-r-transparent border-b-ink-800" />
            )}
          </div>
        </div>
      )}
    </span>
  )
}

/**
 * Styled content helpers — keeps tooltip styling consistent.
 */
export function TooltipMeta({ label, value }) {
  return (
    <div className="flex justify-between gap-2 mb-0.5">
      <span className="text-paper-300 font-medium text-[10px] uppercase tnum" style={{ letterSpacing: '0.1em' }}>
        {label}
      </span>
      <span className="text-paper-100 text-right flex-1">{value}</span>
    </div>
  )
}

export function TooltipBody({ children }) {
  return (
    <p className="text-paper-100 mt-2 leading-relaxed">{children}</p>
  )
}
