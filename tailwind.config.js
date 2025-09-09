/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./*.html", "./static/js/*.js"],
  theme: {
    extend: {
      colors: {
        'cyber-red': '#ff5758',
        'cyber-blue': '#00ffff',
        'cyber-pink': '#ff00ff',
        'cyber-green': '#00ff41',
        'dark-bg': '#0a0a0a',
        'dark-card': '#1a1a1a',
        'dark-border': '#333333'
      },
      fontFamily: {
        'pixel': ['"Press Start 2P"', 'cursive'],
        'mono': ['JetBrains Mono', 'Consolas', 'Monaco', 'monospace']
      },
      animation: {
        'glitch': 'glitch 0.3s ease-in-out infinite alternate',
        'float': 'float 6s ease-in-out infinite',
        'matrix-fall': 'matrix-fall 20s linear infinite',
        'pulse-cyber': 'pulse-cyber 2s ease-in-out infinite alternate'
      },
      keyframes: {
        glitch: {
          '0%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-2px)' },
          '40%': { transform: 'translateX(2px)' },
          '60%': { transform: 'translateX(-1px)' },
          '80%': { transform: 'translateX(1px)' },
          '100%': { transform: 'translateX(0)' }
        },
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-20px)' }
        },
        'matrix-fall': {
          '0%': { transform: 'translateY(-100vh)' },
          '100%': { transform: 'translateY(100vh)' }
        },
        'pulse-cyber': {
          '0%': { boxShadow: '0 0 5px #ff5758, 0 0 10px #ff5758, 0 0 15px #ff5758' },
          '100%': { boxShadow: '0 0 10px #ff5758, 0 0 20px #ff5758, 0 0 30px #ff5758' }
        }
      },
      backdropBlur: {
        xs: '2px'
      }
    }
  },
  plugins: []
}
