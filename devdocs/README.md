# NullRecords - Static Website

A modern, retro-cyber themed website for NullRecords built with HTML, CSS, JavaScript, and Tailwind CSS.

## 🎵 About NullRecords

NullRecords helps independent artists connect with fans and sponsors like never before. The collective power of a label organized as a collective of visual and musical artists managing their own channels and their own destiny.

## 🚀 Features

- **Retro-Cyber Aesthetic**: 80's video game inspired design with modern UI/UX
- **Responsive Design**: Works perfectly on desktop, tablet, and mobile devices
- **Interactive Elements**: 
  - Matrix rain background effect
  - Glitch text animations
  - Smooth scrolling navigation
  - Hover effects and transitions
- **Modern Tech Stack**: Built with Tailwind CSS and vanilla JavaScript
- **GitHub Pages Ready**: Optimized for static hosting
- **Automated Operations**: Daily outreach, analytics reporting, and news monitoring
- **Music Industry Integration**: Contact discovery, email campaigns, and release tracking

## 📁 Project Structure

```
ob-cms/
├── devdocs/                 # Development documentation
├── scripts/                 # Automation and utility scripts  
├── .github/prompts/        # Development guides and AI prompts
├── assets/                 # Source assets (CSS, JS, images)
├── news/                   # Generated news content
├── static/                 # Compiled static files
├── home/                   # Django home app
├── mysite/                 # Django project settings
└── src/                    # Additional source code
```

### Key Directories
- **`devdocs/`** - Comprehensive documentation for all systems
- **`scripts/`** - Python and shell scripts for automation
- **`.github/prompts/`** - Development guides and setup instructions

## 🎨 Design Elements

- **Color Palette**: 
  - Cyber Red: #ff5758
  - Cyber Blue: #00ffff  
  - Cyber Green: #00ff41
  - Dark Background: #0a0a0a
- **Typography**: Press Start 2P (pixel font) for headers, JetBrains Mono for body text
- **Effects**: Neon glows, scanning lines, floating animations, matrix background

## 📁 File Structure

```
/
├── index.html          # Main homepage
├── artists.html        # Artists showcase page
├── script.js          # Interactive JavaScript
├── README.md          # This file
└── static/            # Static assets (images, etc.)
    ├── img/           # Album covers and images
    └── assets/        # Logos and icons
```

## 🛠 Development

This is a static website that can be opened directly in a browser or served through any web server.

### Local Development
1. Clone the repository
2. Set up environment: `cp .env.template .env` and configure credentials
3. Install dependencies: `pip install -r requirements.txt && npm install`
4. Validate setup: `python3 scripts/validate_env.py`
5. Open `index.html` in your browser or run: `python -m http.server 8000`

### Automated Operations
Set up daily automation:
```bash
# Install automated daily operations
./scripts/setup_cron.sh install

# Monitor system status
./scripts/monitor_cron.sh

# Manual operations
python3 scripts/music_outreach.py --daily --limit 5
./scripts/daily_report_system.sh email
./scripts/news_system.sh collect
```

### Deployment
- **GitHub Pages**: Automatic deployment from main branch
- **Daily Updates**: Automated content updates at 8:30 AM
- **Manual Deploy**: Push to main branch triggers deployment

## 🎵 Artists Featured

- **My Evil Robot Army**: Experimental electronic jazz fusion
- **MERA**: Ambient lo-fi and tone poems

## � Documentation

For comprehensive development information:
- **[Development Guide](.github/prompts/development-guide.md)** - Complete setup and workflow guide
- **[Scripts Documentation](scripts/README.md)** - Automation scripts and usage
- **[DevDocs](devdocs/README.md)** - Detailed technical documentation

## �🔗 Links

- [Spotify](https://open.spotify.com/artist/nullrecords)
- [YouTube](https://www.youtube.com/nullrecords)
- [SoundCloud](https://www.soundcloud.com/nullrecords)
- [Twitter](https://www.twitter.com/nullrecords1)
- [Instagram](https://www.instagram.com/nullrecords.1)
- [Facebook](https://www.facebook.com/nullrecords.1)

## 📧 Contact

Email: info@nullrecords.com

## 🎮 Easter Eggs

Check the browser console for hidden messages! The site includes various retro computing references and interactive elements.

---

**© 2025 NullRecords - The Intersection of Music, Art and Technology**
