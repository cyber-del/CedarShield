/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#FAFAF8',
        surface: '#FFFFFF',
        'surface-subtle': '#F4F4F0',
        ink: {
          900: '#111318',
          800: '#1F2937',
          700: '#374151',
          600: '#4B5563',
          500: '#6B7280',
          400: '#9CA3AF',
          300: '#D1D5DB',
          200: '#E5E7EB',
          100: '#F3F4F6'
        },
        muted: {
          red: '#B3261E',
          'red-light': '#FDF2F2',
          'red-border': '#F87171',
          green: '#2F6B4F',
          'green-light': '#F2F9F5',
          'green-border': '#86EFAC',
          amber: '#B45309',
          'amber-light': '#FFFBEB',
          'amber-border': '#FCD34D'
        }
      },
      fontFamily: {
        serif: ['Lora', 'Newsreader', 'Georgia', 'serif'],
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace']
      }
    },
  },
  plugins: [],
}
