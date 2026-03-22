/**
 * ForgeWeb Site JavaScript
 * Global functions and navigation for static site
 * This file is included on all pages and updates automatically
 */

// Configuration - loaded from site-config.json at build time
const SITE_CONFIG = {
    siteName: 'My Website',
    navigation: [
        { title: 'Home', url: 'index.html', active: false },
        { title: 'About', url: 'about.html', active: false },
        { title: 'Contact', url: 'contact.html', active: false }
    ],
    social: {
        twitter: '',
        linkedin: '',
        facebook: '',
        github: ''
    }
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
 * Smooth scroll to anchor
 */
function smoothScroll(targetId) {
    const element = document.getElementById(targetId);
    if (element) {
        element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

/**
 * Copy text to clipboard
 */
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        return true;
    } catch (err) {
        console.error('Failed to copy:', err);
        return false;
    }
}

/**
 * Share page via Web Share API
 */
async function sharePage() {
    if (navigator.share) {
        try {
            await navigator.share({
                title: document.title,
                url: window.location.href
            });
        } catch (err) {
            console.log('Share cancelled or failed:', err);
        }
    } else {
        // Fallback: copy URL to clipboard
        const copied = await copyToClipboard(window.location.href);
        if (copied) {
            alert('Link copied to clipboard!');
        }
    }
}

/**
 * Get current year for copyright
 */
function getCurrentYear() {
    return new Date().getFullYear();
}

/**
 * Initialize page
 */
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    
    // Update copyright year if element exists
    const yearElement = document.getElementById('current-year');
    if (yearElement) {
        yearElement.textContent = getCurrentYear();
    }
    
    // Add smooth scrolling to all anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            smoothScroll(targetId);
        });
    });
});

/**
 * Lazy load images
 */
if ('IntersectionObserver' in window) {
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('img.lazy').forEach(img => {
            imageObserver.observe(img);
        });
    });
}
