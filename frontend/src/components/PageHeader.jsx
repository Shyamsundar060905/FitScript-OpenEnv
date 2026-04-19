/**
 * Consistent editorial-style page header.
 * Renders a small eyebrow (section label), large display title, optional description,
 * and an actions slot on the right. Keeps every page feeling like the same product.
 */
export default function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="flex items-start justify-between gap-6 mb-8">
      <div className="min-w-0">
        {eyebrow && (
          <div className="flex items-center gap-2 mb-2">
            <span className="w-1 h-1 bg-clay-500 rounded-full" />
            <span className="eyebrow text-clay-500">{eyebrow}</span>
          </div>
        )}
        <h1 className="font-display text-display-md text-ink-900">{title}</h1>
        {description && (
          <p className="text-[13.5px] text-ink-500 mt-1.5 max-w-2xl leading-relaxed">
            {description}
          </p>
        )}
      </div>
      {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
    </header>
  )
}
