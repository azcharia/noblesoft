import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'rgba(96, 108, 119, 0.15)',
        input: 'rgba(96, 108, 119, 0.12)',
        ring: '#0245ab', // royal blue
        background: '#f9ffff', // light cream/blue
        foreground: '#364356', // dark slate blue
        surface: 'rgba(255, 255, 255, 0.7)',
        'surface-foreground': '#364356',
        'accent-soft': 'rgba(2, 69, 171, 0.05)',
        primary: {
          DEFAULT: '#364356',
          foreground: '#f9ffff',
        },
        secondary: {
          DEFAULT: 'rgba(96, 108, 119, 0.15)',
          foreground: '#606c77',
        },
        destructive: {
          DEFAULT: '#EF4444',
          foreground: '#FFFFFF',
        },
        muted: {
          DEFAULT: 'rgba(96, 108, 119, 0.05)',
          foreground: '#606c77',
        },
        accent: {
          DEFAULT: '#0245ab',
          secondary: '#364356',
          foreground: '#f9ffff',
        },
        popover: {
          DEFAULT: 'rgba(255, 255, 255, 0.85)',
          foreground: '#364356',
        },
        card: {
          DEFAULT: 'rgba(255, 255, 255, 0.7)',
          foreground: '#364356',
        },
        brand: {
          cream: '#f9ffff',
          dark: '#364356',
          blue: '#0245ab',
          slate: '#606c77',
          orange: '#0245ab', // aligned to brand blue for semantic action button styling
          teal: '#364356',   // aligned to brand dark
        }
      },
      fontFamily: {
        sans: ['var(--font-open-sans)', 'system-ui', 'sans-serif'],
        display: ['var(--font-montserrat)', 'sans-serif'],
        ui: ['var(--font-montserrat)', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'monospace'],
      },
      borderRadius: {
        lg: '12px',
        md: '10px',
        sm: '8px',
      },
      boxShadow: {
        'soft': '0 10px 32px rgba(54, 67, 86, 0.04)',
        'accent': '0 4px 14px rgba(2, 69, 171, 0.15)',
        'accent-lg': '0 8px 24px rgba(2, 69, 171, 0.25)',
      },
      backgroundImage: {
        'gradient-accent': 'linear-gradient(135deg, #0245ab, #364356)',
        'gradient-accent-horizontal': 'linear-gradient(to right, #0245ab, #364356)',
      },
      animation: {
        'float': 'float 5s ease-in-out infinite',
        'float-delayed': 'float 4s ease-in-out infinite',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-dot': 'pulse-dot 2s ease-in-out infinite',
        'fade-up': 'fade-up 0.7s cubic-bezier(0.16, 1, 0.3, 1)',
        'rotate-slow': 'rotate 60s linear infinite',
      },
      keyframes: {
        'fade-up': {
          '0%': { opacity: '0', transform: 'translateY(28px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        'pulse-dot': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.7', transform: 'scale(1.3)' },
        },
        rotate: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
    },
  },
  plugins: [require('tailwindcss-animate'), require('@tailwindcss/typography')],
}

export default config
