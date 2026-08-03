/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Dark navy foundation with a single blue accent ramp. Deliberately
        // narrow: the interface earns trust from hierarchy and spacing,
        // not from colour variety.
        navy: {
          50: '#f4f7fb',
          100: '#e7edf6',
          200: '#cbd9ec',
          300: '#9db8da',
          400: '#6891c3',
          500: '#4571ab',
          600: '#345a90',
          700: '#2b4875',
          800: '#1c2f4d',
          900: '#132038',
          950: '#0b1424',
        },
        accent: {
          400: '#4d94ff',
          500: '#2f7bf6',
          600: '#1c60d4',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(11, 20, 36, 0.06), 0 8px 24px -12px rgba(11, 20, 36, 0.18)',
        raised: '0 2px 4px rgba(11, 20, 36, 0.08), 0 16px 40px -20px rgba(11, 20, 36, 0.35)',
      },
      backgroundImage: {
        'navy-gradient': 'linear-gradient(180deg, #132038 0%, #0b1424 100%)',
        'hero-gradient': 'linear-gradient(135deg, #1c2f4d 0%, #132038 55%, #0b1424 100%)',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
      },
      animation: { 'fade-in': 'fade-in 160ms ease-out' },
    },
  },
  plugins: [],
}
