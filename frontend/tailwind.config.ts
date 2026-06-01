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
        border: 'rgba(203, 229, 229, 0.8)', // soft mint
        input: 'rgba(203, 229, 229, 0.6)',
        ring: '#002da9', // electric blue
        background: '#fffefc', // warm cream
        foreground: '#045656', // deep teal
        surface: 'rgba(255, 255, 255, 0.65)',
        'surface-foreground': '#045656',
        'accent-soft': 'rgba(0, 45, 169, 0.05)',
        primary: {
          DEFAULT: '#045656',
          foreground: '#fffefc',
        },
        secondary: {
          DEFAULT: 'rgba(203, 229, 229, 0.4)', // mint-soft
          foreground: '#045656',
        },
        destructive: {
          DEFAULT: '#f93d1b', // brand-orange/red
          foreground: '#FFFFFF',
        },
        muted: {
          DEFAULT: 'rgba(4, 86, 86, 0.05)',
          foreground: 'rgba(4, 86, 86, 0.6)',
        },
        accent: {
          DEFAULT: '#002da9', // electric blue
          secondary: '#045656',
          foreground: '#fffefc',
        },
        popover: {
          DEFAULT: 'rgba(255, 255, 255, 0.8)',
          foreground: '#045656',
        },
        card: {
          DEFAULT: 'rgba(255, 255, 255, 0.6)',
          foreground: '#045656',
        },
        brand: {
          cream: '#fffefc',
          mint: '#cbe5e5',
          teal: '#045656',
          blue: '#002da9',
          orange: '#f93d1b',
          yellow: '#f2d561',
        }
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        display: ['var(--font-calistoga)', 'Georgia', 'serif'],
        mono: ['var(--font-jetbrains)', 'monospace'],
      },
      borderRadius: {
        lg: '12px',
        md: '10px',
        sm: '8px',
      },
      boxShadow: {
        'soft': '0 10px 32px rgba(4, 86, 86, 0.04)',
        'accent': '0 4px 14px rgba(0, 45, 169, 0.15)',
        'accent-lg': '0 8px 24px rgba(0, 45, 169, 0.25)',
      },
      backgroundImage: {
        'gradient-accent': 'linear-gradient(135deg, #002da9, #045656)',
        'gradient-accent-horizontal': 'linear-gradient(to right, #002da9, #045656)',
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
