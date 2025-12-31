// Modern Art Book & Music Store JS
const STORE_ITEMS_URL = './store_items.json';
const MUSIC_CONTAINER = document.getElementById('music-items');
const BOOK_CONTAINER = document.getElementById('book-items');
const BOB_BOOKS_CONTAINER = document.getElementById('bob-books-items');

function renderStoreItem(item) {
  const div = document.createElement('div');
  div.className = 'card';
  let actionButton = '';
    if (item.active === false) {
      actionButton = `<button class=\"donate\" disabled style=\"background:#aaa;cursor:not-allowed;opacity:0.7;\">Coming Soon</button>`;
    } else if (item.type === 'book') {
      actionButton = `<button class=\"donate\" onclick=\"buyAndDownload('book', '${item.download_bundle}', ${item.suggested_donation})\">Buy Now</button>`;
    } else if (item.type === 'music') {
      actionButton = `<button class=\"donate\" onclick=\"buyAndDownload('album', '${item.download_bundle}', ${item.suggested_donation})\">Buy Now</button>`;
    } else {
      actionButton = `<button class=\"donate\" onclick=\"donateAndDownload('${item.id}', ${item.suggested_donation})\">Donate & Download</button>`;
    }
  div.innerHTML = `
    <img src="./${item.cover_art}" alt="${item.title} cover" />
    <h3>${item.title}</h3>
    <div class="meta">${item.type === 'music' ? 'Artist: ' + item.artist : 'Author: ' + item.author}</div>
    <div class="desc">${item.description}</div>
    <div class="meta" style="font-weight:600; color:#0fa;">$${item.suggested_donation.toFixed(2)}</div>
    ${actionButton}
  `;
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

window.onload = loadStoreItems;

function donateAndDownload(itemId, amount) {
  alert(`Thank you for your donation! Your download will start now.`);
  window.location.href = `/store/download/${itemId}`;
}
  function buyAndDownload(type, bundle, amount) {
    let paypalLink = type === 'book'
      ? 'https://www.paypal.com/ncp/payment/K2HDM5GXG8JHW'
      : 'https://www.paypal.com/ncp/payment/AW65SSP6N7L2G';
    alert('Your download will start now. Please also pay the suggested donation at the payment provider you are being redirected to.');
    // Use remote link directly if bundle is a full URL
    let downloadUrl = (bundle.startsWith('http://') || bundle.startsWith('https://')) ? bundle : `/store/${bundle}`;
    window.location.href = downloadUrl;
    // After navigation, open PayPal in the same window
    setTimeout(function() {
      window.location.href = paypalLink;
    }, 500);
  }
