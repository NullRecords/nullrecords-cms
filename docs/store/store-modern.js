// Modern Art Book & Music Store JS
const STORE_ITEMS_URL = './store_items.json';
const MUSIC_CONTAINER = document.getElementById('music-items');
const BOOK_CONTAINER = document.getElementById('book-items');
const BOB_BOOKS_CONTAINER = document.getElementById('bob-books-items');
const TICKER_CONTAINER = document.getElementById('ticker');
const DOWNLOADS_KEY = 'nullrecords_downloads';

// Log a download event
function logDownload(itemTitle) {
  const downloads = JSON.parse(localStorage.getItem(DOWNLOADS_KEY) || '[]');
  const now = new Date();
  downloads.unshift({
    title: itemTitle,
    date: now.toLocaleDateString(),
    time: now.toLocaleTimeString(),
    timestamp: now.getTime()
  });
  // Keep only last 50 downloads
  if (downloads.length > 50) {
    downloads.pop();
  }
  localStorage.setItem(DOWNLOADS_KEY, JSON.stringify(downloads));
  updateTicker();
}

// Update the ticker display
function updateTicker() {
  const downloads = JSON.parse(localStorage.getItem(DOWNLOADS_KEY) || '[]');
  if (downloads.length === 0) {
    TICKER_CONTAINER.innerHTML = '<div style="text-align: center; color: #888; padding: 2rem;">No downloads yet. Be the first!</div>';
    return;
  }
  
  let html = '<div class="ticker">';
  downloads.forEach(download => {
    html += `<div class="ticker-item"><span class="ticker-title">${download.title}</span> <span class="ticker-meta">on ${download.date} at ${download.time}</span></div>`;
  });
  html += '</div>';
  TICKER_CONTAINER.innerHTML = html;
}

function renderStoreItem(item) {
  const div = document.createElement('div');
  div.className = item.type === 'book' ? 'card book-card' : 'card';
  
  // Add click handler for books
  if (item.type === 'book') {
    div.style.cursor = 'pointer';
    div.addEventListener('click', function(e) {
      // Don't open modal if clicking on a button
      if (e.target.tagName === 'BUTTON' || e.target.closest('button')) {
        return;
      }
      openBookModal(item);
    });
  }
  
  let actionButton = '';
    if (item.active === false) {
      actionButton = `<button class=\"donate\" disabled style=\"background:#aaa;cursor:not-allowed;opacity:0.7;\">Coming Soon</button>`;    } else if (item.suggested_donation === 0) {
      // Free preview tracks - direct download
      if (item.audio_files && item.audio_files.length > 0) {
        actionButton = `<button class="donate" onclick="event.stopPropagation(); downloadFreeTrack('${item.audio_files[0]}')">FREE PREVIEW</button>`;
      } else {
        actionButton = `<button class="donate" disabled style="background:#aaa;cursor:not-allowed;opacity:0.7;">Preview</button>`;
      }    } else if (item.type === 'book') {
      actionButton = `<button class=\"donate\" onclick=\"event.stopPropagation(); buyAndDownload('book', '${item.download_bundle}', ${item.suggested_donation}, '${item.title}')\">Buy Now - $${item.suggested_donation.toFixed(2)}</button>`;
    } else if (item.type === 'music') {
      actionButton = `<button class=\"donate\" onclick=\"buyAndDownload('album', '${item.download_bundle}', ${item.suggested_donation}, '${item.title}')\">Buy Now</button>`;
    } else {
      actionButton = `<button class=\"donate\" onclick=\"donateAndDownload('${item.id}', ${item.suggested_donation})\">Donate & Download</button>`;
    }
  
  // Add streaming links if available
  let streamingButtons = '';
  if (item.streaming_links && item.type === 'music') {
    streamingButtons = '<div class="streaming-links">';
    streamingButtons += '<div class="streaming-text">Or stream (compressed mess, data-discarded services) on:</div>';
    if (item.streaming_links.spotify) {
      streamingButtons += `<a href="${item.streaming_links.spotify}" target="_blank" rel="noopener" class="streaming-btn spotify-btn" title="Listen on Spotify"><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/></svg> Spotify</a>`;
    }
    if (item.streaming_links.apple_music) {
      streamingButtons += `<a href="${item.streaming_links.apple_music}" target="_blank" rel="noopener" class="streaming-btn apple-btn" title="Listen on Apple Music"><svg viewBox="0 0 24 24" width="20" height="20"><path fill="currentColor" d="M23.997 6.124c0-.738-.065-1.47-.24-2.19-.317-1.31-1.062-2.31-2.18-3.043C21.003.517 20.373.285 19.7.164c-.517-.093-1.038-.135-1.564-.15-.04-.003-.083-.01-.124-.013H5.988c-.152.01-.303.017-.455.026C4.786.07 4.043.15 3.34.428 2.004.958 1.04 1.88.475 3.208c-.192.448-.292.925-.363 1.408-.056.392-.088.785-.1 1.18 0 .032-.007.065-.01.097v12.223c.01.14.017.283.027.424.05.815.154 1.624.497 2.373.65 1.42 1.738 2.353 3.234 2.801.42.127.856.187 1.293.228.555.053 1.11.06 1.667.06h11.03c.525 0 1.048-.034 1.57-.1.823-.106 1.597-.35 2.296-.81a5.39 5.39 0 0 0 1.88-2.207c.186-.42.293-.87.37-1.324.113-.675.138-1.358.137-2.04-.002-3.8 0-7.595-.003-11.393zm-6.423 3.99v5.712c0 .417-.058.827-.244 1.206-.29.59-.76.962-1.388 1.14-.35.1-.706.157-1.07.173-.95.045-1.773-.6-1.943-1.536-.142-.773.227-1.624 1.038-2.022.323-.16.67-.245 1.025-.33.508-.12 1.003-.06 1.458-.2v-3.9c0-.005-.002-.012-.005-.025-.01 0-.02-.003-.03-.003-.407.09-.816.178-1.224.267-.68.15-1.357.297-2.035.446-.51.11-.764-.027-.87-.52-.012-.055-.017-.112-.02-.168V6.37c0-.41.213-.61.625-.72l3.977-.888c.63-.14 1.26-.28 1.887-.426.498-.117.77.097.77.595v4.19z"/></svg> Apple Music</a>`;
    }
    streamingButtons += '</div>';
  }
  
  // Simplified display for book cards (details shown in modal)
  if (item.type === 'book') {
    div.innerHTML = `
      <img src="./${item.cover_art}" alt="${item.title} cover" />
      <h3>${item.title}</h3>
      <div class="meta">Author: ${item.author}</div>
      <div class="meta" style="font-weight:600; color:#0fa; margin-top: 1rem;">$${item.suggested_donation.toFixed(2)}</div>
      ${actionButton}
    `;
  } else {
    div.innerHTML = `
      <img src="./${item.cover_art}" alt="${item.title} cover" />
      <h3>${item.title}</h3>
      <div class="meta">${item.type === 'music' ? 'Artist: ' + item.artist : 'Author: ' + item.author}</div>
      <div class="desc">${item.description}</div>
      <div class="meta" style="font-weight:600; color:#0fa;">$${item.suggested_donation.toFixed(2)}</div>
      ${actionButton}
      ${streamingButtons}
    `;
  }
  
  if (item.type === 'music') {
    MUSIC_CONTAINER.appendChild(div);
  } else if (item.bob_humanist) {
    BOB_BOOKS_CONTAINER.appendChild(div);
  } else {
    BOOK_CONTAINER.appendChild(div);
  }
}

function loadStoreItems() {
  fetch(STORE_ITEMS_URL)
    .then(res => res.json())
    .then(items => {
      MUSIC_CONTAINER.innerHTML = '';
      BOOK_CONTAINER.innerHTML = '';
      if (BOB_BOOKS_CONTAINER) BOB_BOOKS_CONTAINER.innerHTML = '';
      items.forEach(renderStoreItem);
    });
}

window.onload = function() {
  loadStoreItems();
  updateTicker();
};

function downloadFreeTrack(audioFile) {
  // Direct download for free preview tracks
  const downloadUrl = `/store/${audioFile}`;
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = audioFile.split('/').pop();
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  // Log the download
  const fileName = audioFile.split('/').pop();
  logDownload(`Free Preview: ${fileName}`);
}

function donateAndDownload(itemId, amount) {
  logDownload(itemId);
  alert(`Thank you for your donation! Your download will start now.`);
  window.location.href = `/store/download/${itemId}`;
}
  function buyAndDownload(type, bundle, amount, title) {
    let paypalLink = type === 'book'
      ? 'https://www.paypal.com/ncp/payment/K2HDM5GXG8JHW'
      : 'https://www.paypal.com/ncp/payment/AW65SSP6N7L2G';
    
    // Log the download
    const itemName = title || bundle.split('/').pop();
    logDownload(`${type === 'book' ? 'Book' : 'Album'}: ${itemName}`);
    
    // Check for Proton Drive link
    if (bundle.startsWith('https://drive.proton.me/')) {
      alert('You will be taken to Proton Drive to download your album. Please click the Download button on the Proton Drive page. Also, please pay the suggested donation at the payment provider you are being redirected to.');
      window.open(bundle, '_blank');
      window.location.href = paypalLink;
      return;
    }
    alert('Your download will start now. Please also pay the suggested donation at the payment provider you are being redirected to.');
    let downloadUrl = (bundle.startsWith('http://') || bundle.startsWith('https://')) ? bundle : `/store/${bundle}`;
    window.location.href = downloadUrl;
    setTimeout(function() {
      window.location.href = paypalLink;
    }, 500);
  }

// Modal and Carousel Functions
let currentSlide = 0;
let currentBookData = null;

window.openBookModal = function(book) {
  currentBookData = book;
  const modal = document.getElementById('bookModal');
  
  // Set book info
  document.getElementById('modalCoverImg').src = './' + book.cover_art;
  document.getElementById('modalCoverImg').alt = book.title;
  document.getElementById('modalTitle').textContent = book.title;
  document.getElementById('modalAuthor').textContent = 'Author: ' + book.author;
  document.getElementById('modalDescription').innerHTML = book.description;
  document.getElementById('modalPrice').textContent = '$' + book.suggested_donation.toFixed(2);
  
  // Set action button
  let actionButtonHTML = '';
  if (book.active === false) {
    actionButtonHTML = `<button class="donate" disabled style="background:#aaa;cursor:not-allowed;opacity:0.7;">Coming Soon</button>`;
  } else {
    actionButtonHTML = `<button class="donate" onclick="buyAndDownload('book', '${book.download_bundle}', ${book.suggested_donation}, '${book.title}')">Buy Now - $${book.suggested_donation.toFixed(2)}</button>`;
  }
  document.getElementById('modalActionButton').innerHTML = actionButtonHTML;
  
  // Setup carousel with screenshots
  setupCarousel(book);
  
  modal.classList.add('active');
  document.body.style.overflow = 'hidden';
}

window.closeBookModal = function(event) {
  if (event && event.target !== event.currentTarget && !event.target.classList.contains('modal-close')) {
    return;
  }
  const modal = document.getElementById('bookModal');
  modal.classList.remove('active');
  document.body.style.overflow = 'auto';
  currentSlide = 0;
}

window.setupCarousel = function(book) {
  // Define screenshots for each book
  const bookScreenshots = {
    'book001': [
      { src: './assets/book-screenshots/screenshot-1.png', alt: 'Bob\'s Commentary Example' },
      { src: './assets/book-screenshots/screenshot-2.png', alt: 'Humanist Note Example' },
    ],
    'book002': [
      { src: './assets/book-screenshots/screenshot-1.png', alt: 'Bob\'s Commentary Example' },
      { src: './assets/book-screenshots/screenshot-2.png', alt: 'Humanist Note Example' },
    ]
  };
  
  const screenshots = bookScreenshots[book.id] || [];
  
  if (screenshots.length === 0) {
    document.querySelector('.modal-carousel').style.display = 'none';
    return;
  }
  
  document.querySelector('.modal-carousel').style.display = 'block';
  
  const slidesContainer = document.getElementById('carouselSlides');
  const dotsContainer = document.getElementById('carouselDots');
  
  slidesContainer.innerHTML = '';
  dotsContainer.innerHTML = '';
  
  screenshots.forEach((screenshot, index) => {
    // Create slide
    const slide = document.createElement('div');
    slide.className = 'carousel-slide' + (index === 0 ? ' active' : '');
    slide.innerHTML = `<img src="${screenshot.src}" alt="${screenshot.alt}" />`;
    slidesContainer.appendChild(slide);
    
    // Create dot
    const dot = document.createElement('span');
    dot.className = 'carousel-dot' + (index === 0 ? ' active' : '');
    dot.onclick = () => goToSlide(index);
    dotsContainer.appendChild(dot);
  });
  
  currentSlide = 0;
}

window.changeSlide = function(direction) {
  const slides = document.querySelectorAll('.carousel-slide');
  const dots = document.querySelectorAll('.carousel-dot');
  
  if (slides.length === 0) return;
  
  slides[currentSlide].classList.remove('active');
  dots[currentSlide].classList.remove('active');
  
  currentSlide += direction;
  
  if (currentSlide >= slides.length) {
    currentSlide = 0;
  } else if (currentSlide < 0) {
    currentSlide = slides.length - 1;
  }
  
  slides[currentSlide].classList.add('active');
  dots[currentSlide].classList.add('active');
}

window.goToSlide = function(index) {
  const slides = document.querySelectorAll('.carousel-slide');
  const dots = document.querySelectorAll('.carousel-dot');
  
  slides[currentSlide].classList.remove('active');
  dots[currentSlide].classList.remove('active');
  
  currentSlide = index;
  
  slides[currentSlide].classList.add('active');
  dots[currentSlide].classList.add('active');
}

// Keyboard navigation for modal
document.addEventListener('keydown', function(e) {
  const modal = document.getElementById('bookModal');
  if (!modal.classList.contains('active')) return;
  
  if (e.key === 'Escape') {
    closeBookModal();
  } else if (e.key === 'ArrowLeft') {
    changeSlide(-1);
  } else if (e.key === 'ArrowRight') {
    changeSlide(1);
  }
});
