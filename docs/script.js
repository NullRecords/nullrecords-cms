// NullRecords - Interactive Elements

document.addEventListener('DOMContentLoaded', function() {
    // Mobile Menu Toggle
    const mobileMenuBtn = document.getElementById('mobile-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
    
    if (mobileMenuBtn && mobileMenu) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenu.classList.toggle('hidden');
        });
    }

    // Smooth Scrolling for Navigation Links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                // Close mobile menu if open
                if (mobileMenu && !mobileMenu.classList.contains('hidden')) {
                    mobileMenu.classList.add('hidden');
                }
            }
        });
    });

    // Matrix Rain Effect
    const canvas = document.getElementById('matrix-rain');
    const ctx = canvas.getContext('2d');

    // Set canvas size
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    // Matrix characters
    const matrix = "ABCDEFGHIJKLMNOPQRSTUVWXYZ123456789@#$%^&*()*&^%+-/~{[|`]}";
    const matrixArray = matrix.split("");

    const fontSize = 10;
    const columns = canvas.width / fontSize;

    const drops = [];
    for (let x = 0; x < columns; x++) {
        drops[x] = 1;
    }

    function drawMatrix() {
        ctx.fillStyle = 'rgba(0, 0, 0, 0.04)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#ff5758';
        ctx.font = fontSize + 'px monospace';

        for (let i = 0; i < drops.length; i++) {
            const text = matrixArray[Math.floor(Math.random() * matrixArray.length)];
            ctx.fillText(text, i * fontSize, drops[i] * fontSize);

            if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }
            drops[i]++;
        }
    }

    // Start matrix animation
    setInterval(drawMatrix, 35);

    // Glitch Effect for Hero Title
    const glitchElement = document.querySelector('.glitch');
    if (glitchElement) {
        setInterval(() => {
            if (Math.random() > 0.95) {
                glitchElement.style.transform = `translateX(${Math.random() * 4 - 2}px)`;
                setTimeout(() => {
                    glitchElement.style.transform = 'translateX(0)';
                }, 100);
            }
        }, 100);
    }

    // Typing Effect for Sections
    function typeWriter(element, text, speed = 50) {
        let i = 0;
        element.innerHTML = '';
        function type() {
            if (i < text.length) {
                element.innerHTML += text.charAt(i);
                i++;
                setTimeout(type, speed);
            }
        }
        type();
    }

    // Intersection Observer for Animations
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate-fade-in');
                
                // Special handling for section titles
                const title = entry.target.querySelector('h2');
                if (title && title.textContent.includes('_')) {
                    const originalText = title.textContent;
                    typeWriter(title, originalText, 100);
                }
            }
        });
    }, observerOptions);

    // Observe all sections
    document.querySelectorAll('section').forEach(section => {
        observer.observe(section);
    });

    // Console Easter Egg
    console.log(`
    ╔══════════════════════════════════════╗
    ║           NULLRECORDS.SYS            ║
    ║      System Access Granted           ║
    ║                                      ║
    ║  Welcome to the digital realm        ║
    ║  of music, art, and technology       ║
    ║                                      ║
    ║  > Looking for something special?    ║
    ║  > Check out our artists and music   ║
    ║  > info@nullrecords.com              ║
    ╚══════════════════════════════════════╝
    `);

    // Contact Form Enhancement
    const contactForm = document.getElementById('contact-form');
    if (contactForm) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault(); // Prevent default form submission
            
            const name = document.getElementById('name').value;
            const subject = document.getElementById('subject').value;
            const email = document.getElementById('email').value;
            const message = document.getElementById('message').value;

            // Create the mailto link with form data
            const mailtoLink = `mailto:info@nullrecords.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(`Name: ${name}\nEmail: ${email}\n\nMessage:\n${message}`)}`;
            
            // Open the email client
            window.location.href = mailtoLink;
        });
    }

    // Album Hover Effects
    document.querySelectorAll('.group').forEach(album => {
        const img = album.querySelector('img');
        if (img) {
            album.addEventListener('mouseenter', () => {
                img.style.filter = 'hue-rotate(90deg) saturate(1.5)';
            });
            
            album.addEventListener('mouseleave', () => {
                img.style.filter = 'none';
            });
        }
    });

    // Parallax Effect for Hero Section
    window.addEventListener('scroll', () => {
        const scrolled = window.pageYOffset;
        const heroSection = document.getElementById('home');
        if (heroSection) {
            const rate = scrolled * -0.5;
            heroSection.style.transform = `translateY(${rate}px)`;
        }
    });

    // Add fade-in animation class to CSS
    const style = document.createElement('style');
    style.textContent = `
        .animate-fade-in {
            animation: fadeIn 0.8s ease-in-out;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .image-rendering-pixelated {
            image-rendering: pixelated;
            image-rendering: -moz-crisp-edges;
            image-rendering: crisp-edges;
        }
    `;
    document.head.appendChild(style);

    // Random glitch effect on page elements
    function randomGlitch() {
        const elements = document.querySelectorAll('.retro-card');
        const randomElement = elements[Math.floor(Math.random() * elements.length)];
        
        if (randomElement && Math.random() > 0.98) {
            randomElement.style.transform = 'translateX(2px)';
            randomElement.style.filter = 'hue-rotate(180deg)';
            
            setTimeout(() => {
                randomElement.style.transform = 'translateX(0)';
                randomElement.style.filter = 'none';
            }, 150);
        }
    }

    // Run random glitch every 100ms
    setInterval(randomGlitch, 100);

    // Terminal cursor effect for input focus
    document.querySelectorAll('input, textarea').forEach(input => {
        input.addEventListener('focus', function() {
            this.style.borderColor = '#00ffff';
            this.style.boxShadow = '0 0 10px rgba(0, 255, 255, 0.5)';
        });
        
        input.addEventListener('blur', function() {
            this.style.borderColor = '#ff5758';
            this.style.boxShadow = 'none';
        });
    });
});

// Terminal-style loading message
window.addEventListener('load', () => {
    console.log('> SYSTEM INITIALIZED');
    console.log('> LOADING AUDIO STREAMS...');
    console.log('> CONNECTING TO NULLRECORDS.NET...');
    console.log('> CONNECTION ESTABLISHED');
    console.log('> WELCOME TO THE GRID');
});
