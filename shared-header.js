/**
 * NullRecords Shared Header System
 * ================================
 * 
 * This file provides a centralized way to inject common head elements
 * into all pages, including analytics, meta tags, and other shared resources.
 * 
 * Usage: Include this script in the <head> of any page before closing </head>
 * 
 * Author: NullRecords
 * Version: 1.0
 */

(function() {
    'use strict';
    
    // Configuration
    const NULLRECORDS_CONFIG = {
        googleAnalyticsId: 'G-2WVCJM4NKR',
        version: '1.0',
        debug: false
    };
    
    /**
     * Log debug messages if debug mode is enabled
     */
    function debug(message) {
        if (NULLRECORDS_CONFIG.debug) {
            console.log('[NullRecords Header]', message);
        }
    }
    
    /**
     * Create and inject a script element
     */
    function injectScript(src, async = false, defer = false) {
        const script = document.createElement('script');
        script.src = src;
        if (async) script.async = true;
        if (defer) script.defer = true;
        document.head.appendChild(script);
        debug(`Injected script: ${src}`);
    }
    
    /**
     * Create and inject inline script content
     */
    function injectInlineScript(content) {
        const script = document.createElement('script');
        script.textContent = content;
        document.head.appendChild(script);
        debug('Injected inline script');
    }
    
    /**
     * Create and inject a meta tag
     */
    function injectMeta(attributes) {
        const meta = document.createElement('meta');
        Object.keys(attributes).forEach(key => {
            meta.setAttribute(key, attributes[key]);
        });
        document.head.appendChild(meta);
        debug(`Injected meta: ${JSON.stringify(attributes)}`);
    }
    
    /**
     * Create and inject a link element
     */
    function injectLink(attributes) {
        const link = document.createElement('link');
        Object.keys(attributes).forEach(key => {
            link.setAttribute(key, attributes[key]);
        });
        document.head.appendChild(link);
        debug(`Injected link: ${JSON.stringify(attributes)}`);
    }
    
    /**
     * Initialize Google Analytics (gtag.js)
     */
    function initializeGoogleAnalytics() {
        const gaId = NULLRECORDS_CONFIG.googleAnalyticsId;
        
        // Inject gtag.js script
        injectScript(`https://www.googletagmanager.com/gtag/js?id=${gaId}`, true);
        
        // Inject gtag configuration
        const gtagScript = `
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', '${gaId}');
        `;
        injectInlineScript(gtagScript);
        
        debug(`Google Analytics initialized with ID: ${gaId}`);
    }
    
    /**
     * Inject common performance optimization links
     */
    function injectPerformanceOptimizations() {
        // Preconnect to external domains for performance
        const preconnects = [
            'https://fonts.googleapis.com',
            'https://fonts.gstatic.com',
            'https://www.googletagmanager.com',
            'https://www.google-analytics.com',
            'https://open.spotify.com',
            'https://www.youtube.com'
        ];
        
        preconnects.forEach(href => {
            const attributes = { rel: 'preconnect', href };
            if (href === 'https://fonts.gstatic.com') {
                attributes.crossorigin = '';
            }
            injectLink(attributes);
        });
        
        debug('Performance optimizations injected');
    }
    
    /**
     * Inject additional SEO and social meta tags
     */
    function injectSharedMetaTags() {
        // Additional meta tags that should be on every page
        const metaTags = [
            { name: 'author', content: 'NullRecords' },
            { name: 'robots', content: 'index, follow' },
            { 'http-equiv': 'X-UA-Compatible', content: 'IE=edge' },
            { name: 'theme-color', content: '#ff5758' },
            { name: 'msapplication-TileColor', content: '#ff5758' }
        ];
        
        metaTags.forEach(meta => injectMeta(meta));
        
        // Add structured data for music organization
        const structuredData = {
            "@context": "https://schema.org",
            "@type": "MusicGroup",
            "name": "NullRecords",
            "genre": ["LoFi Jazz", "Electronic", "Fusion", "Instrumental"],
            "url": "https://nullrecords.com",
            "sameAs": [
                "https://www.youtube.com/nullrecords",
                "https://www.soundcloud.com/nullrecords",
                "https://open.spotify.com/artist/nullrecords"
            ]
        };
        
        const jsonLd = document.createElement('script');
        jsonLd.type = 'application/ld+json';
        jsonLd.textContent = JSON.stringify(structuredData);
        document.head.appendChild(jsonLd);
        
        debug('Shared meta tags and structured data injected');
    }
    
    /**
     * Inject common favicons and app icons
     */
    function injectFavicons() {
        const icons = [
            { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
            { rel: 'apple-touch-icon', href: '/static/assets/img/apple-touch-icon.png' },
            { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/assets/logos/favicon.png' },
            { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/assets/logos/favicon.png' }
        ];
        
        icons.forEach(icon => injectLink(icon));
        debug('Favicons injected');
    }
    
    /**
     * Main initialization function
     */
    function initializeSharedHeader() {
        debug('Initializing NullRecords shared header system...');
        
        try {
            // Initialize Google Analytics
            initializeGoogleAnalytics();
            
            // Inject performance optimizations
            injectPerformanceOptimizations();
            
            // Inject shared meta tags and structured data
            injectSharedMetaTags();
            
            // Inject favicons
            injectFavicons();
            
            debug('Shared header initialization complete');
            
            // Dispatch custom event to signal completion
            document.dispatchEvent(new CustomEvent('nullrecords:header:loaded', {
                detail: { version: NULLRECORDS_CONFIG.version }
            }));
            
        } catch (error) {
            console.error('[NullRecords Header] Initialization failed:', error);
        }
    }
    
    /**
     * Utility function to enable debug mode
     */
    window.NullRecordsHeader = {
        enableDebug: function() {
            NULLRECORDS_CONFIG.debug = true;
            debug('Debug mode enabled');
        },
        getConfig: function() {
            return { ...NULLRECORDS_CONFIG };
        },
        getVersion: function() {
            return NULLRECORDS_CONFIG.version;
        }
    };
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeSharedHeader);
    } else {
        initializeSharedHeader();
    }
    
})();