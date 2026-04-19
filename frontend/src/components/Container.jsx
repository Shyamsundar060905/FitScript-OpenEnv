import clsx from 'clsx'

export default function Container({ children, size = 'lg', className }) {
  const max = {
    sm: 'max-w-2xl',
    md: 'max-w-4xl',
    lg: 'max-w-6xl',
    xl: 'max-w-7xl',
  }[size]

  return (
    <div className={clsx('mx-auto px-4 md:px-8 py-8 md:py-10', max, className)}>
      {children}
    </div>
  )
}
