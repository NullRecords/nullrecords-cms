/**
 * Site Configuration
 * Auto-generated from site-config.json
 * This file is loaded by all pages to provide navigation and social media links
 */

const SITE_CONFIG = {
    siteName: "NullRecords",
    siteUrl: "https://nullrecords.github.io/nullrecords-website",
    description: "NullRecords Art, Music, Publishing and more.",
    navigation: [
    {
        "title": "Home",
        "url": "/"
    },
    {
        "title": "News",
        "url": "/news/"
    },
    {
        "title": "Artists",
        "url": "/artists.html"
    },
    {
        "title": "Store",
        "url": "/store/index.html"
    },
    {
        "title": "Unsubscribe",
        "url": "/unsubscribe.html"
    }
],
    social: {
    "twitter": "",
    "linkedin": "",
    "facebook": "",
    "github": ""
},
    currentYear: new Date().getFullYear()
};

/**
 * Initialize navigation on page load
 */
function initNavigation() {
    const currentPage = window.location.pathname.split('/').pop() || 'index.html';
    
    // Update active state in navigation
    SITE_CONFIG.navigation.forEach(item => {
        item.active = item.url === currentPage;
    });
}

/**
 * Toggle mobile menu
 */
function toggleMobileMenu() {
    const menu = document.getElementById('mobile-menu');
    if (menu) {
        menu.classList.toggle('hidden');
    }
}

/**
 * Initialize page
 */
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    
    // Update copyright year if element exists
    const yearElement = document.getElementById('current-year');
    if (yearElement) {
        yearElement.textContent = SITE_CONFIG.currentYear;
    }
});
