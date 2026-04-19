/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Paper — warm off-whites used for app background, sidebars, cards
        paper: {
          50:  '#FEFDF9',
          100: '#FAF7EE',
          200: '#F4F0E2',
          300: '#EBE5D2',
          400: '#DCD3BA',
          500: '#C5B995',
        },
        // Sage — primary / verified / success
        sage: {
          50:  '#F4F7EC',
          100: '#E7EED6',
          200: '#CFDDAE',
          400: '#8FB650',
          500: '#6B9737',
          600: '#557A2C',
          700: '#425E22',
          800: '#2F4319',
        },
        // Clay — secondary accent: data emphasis, agent branding, warnings
        clay: {
          50:  '#FDF3EC',
          100: '#FAE2D1',
          200: '#F2BF98',
          400: '#D8643A',
          500: '#B94A1E',
          600: '#963A17',
          700: '#732C12',
        },
        // Ink — text + structural neutrals
        ink: {
          50:  '#F7F5F0',
          100: '#EDEAE0',
          200: '#D8D3C4',
          300: '#B3AC99',
          400: '#857E6C',
          500: '#5E5749',
          600: '#423D32',
          700: '#2D2921',
          800: '#1C1A14',
          900: '#0F0E0A',
        },
      },
      fontFamily: {
        sans:    ['"DM Sans"', 'system-ui', 'sans-serif'],
        display: ['"Syne"', 'system-ui', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        'display-xl': ['3.5rem',   { lineHeight: '1.02', letterSpacing: '-0.035em', fontWeight: '700' }],
        'display-lg': ['2.5rem',   { lineHeight: '1.05', letterSpacing: '-0.03em',  fontWeight: '700' }],
        'display-md': ['1.875rem', { lineHeight: '1.1',  letterSpacing: '-0.025em', fontWeight: '700' }],
        'display-sm': ['1.375rem', { lineHeight: '1.2',  letterSpacing: '-0.02em',  fontWeight: '600' }],
      },
      borderRadius: {
        'xs':  '4px',
        'sm':  '6px',
        'md':  '8px',
        'lg':  '12px',
        'xl':  '14px',
        '2xl': '18px',
        '3xl': '24px',
      },
      boxShadow: {
        'hair':  '0 0 0 0.5px rgba(28, 26, 20, 0.08)',
        'card':  '0 1px 2px rgba(28, 26, 20, 0.04), 0 0 0 0.5px rgba(28, 26, 20, 0.06)',
        'lift':  '0 4px 12px -2px rgba(28, 26, 20, 0.08), 0 0 0 0.5px rgba(28, 26, 20, 0.06)',
        'float': '0 12px 32px -8px rgba(28, 26, 20, 0.12), 0 0 0 0.5px rgba(28, 26, 20, 0.06)',
        'inset-hair': 'inset 0 0 0 0.5px rgba(28, 26, 20, 0.08)',
      },
      animation: {
        'fade-in':    'fadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'slide-up':   'slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'pulse-soft': 'pulseSoft 2s ease-in-out infinite',
        'shimmer':    'shimmer 2.5s linear infinite',
        'spin-slow':  'spin 3s linear infinite',
      },
      keyframes: {
        fadeIn:    { from: { opacity: 0 }, to: { opacity: 1 } },
        slideUp:   { from: { opacity: 0, transform: 'translateY(8px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        pulseSoft: { '0%,100%': { opacity: 1 }, '50%': { opacity: 0.55 } },
        shimmer:   { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
      backgroundImage: {
        'grain':      "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0.11 0 0 0 0 0.1 0 0 0 0 0.08 0 0 0 0.035 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
}
