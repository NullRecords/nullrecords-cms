// NullRecords Store JS
// Loads store items and handles payment via Stripe (simple integration)

const STORE_ITEMS_URL = '/store/store_items.json';
const MUSIC_CONTAINER = document.getElementById('music-items');
const BOOK_CONTAINER = document.getElementById('book-items');

// Stripe publishable key (replace with your own)
const STRIPE_PUBLIC_KEY = 'pk_test_XXXXXXXXXXXXXXXXXXXXXXXX';

function renderStoreItem(item) {
  const div = document.createElement('div');
  div.className = 'bg-white/90 rounded-2xl shadow-lg p-6 flex flex-col items-center text-center border border-gray-200 hover:shadow-2xl hover:-translate-y-1 transition-all duration-300';
  div.innerHTML = `
    <div class="w-full flex justify-center mb-4">
      <img src="/store/${item.cover_art}" alt="${item.title} cover" class="w-full max-w-[180px] h-60 object-cover rounded-lg shadow-md border border-gray-100" />
    </div>
    <h3 class="text-xl font-bold text-gray-900 mb-1" style="font-family: 'Playfair Display', serif;">${item.title}</h3>
    <p class="text-sm text-gray-700 mb-1 italic">${item.type === 'music' ? 'Artist: ' + item.artist : 'Author: ' + item.author}</p>
    <p class="text-xs text-gray-500 mb-3">${item.description}</p>
    <p class="font-semibold text-cyber-blue mb-3">Suggested Donation: $${item.suggested_donation.toFixed(2)}</p>
    <button onclick="donateAndDownload('${item.id}', ${item.suggested_donation})" class="mt-auto px-5 py-2 bg-cyber-blue text-white rounded-full hover:bg-cyber-red transition-all font-semibold shadow">Donate & Download</button>
  `;
  if (item.type === 'music') {
    MUSIC_CONTAINER.appendChild(div);
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
      items.forEach(renderStoreItem);
    });
}

window.onload = loadStoreItems;
// Add grid styling for 3 per row
const style = document.createElement('style');
style.innerHTML = `
.store-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2em 1.5em;
  margin-bottom: 2em;
}
.store-item {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 2px 8px #0001;
  padding: 1.2em 1em 1.5em 1em;
  text-align: center;
  min-width: 0;
}
`;
document.head.appendChild(style);

// Stripe payment logic (simple checkout)
function donateAndDownload(itemId, amount) {
  // For demo: just alert and simulate download
  alert(`Thank you for your donation! Your download will start now.`);
  // In production, redirect to Stripe Checkout or Paypal
  // window.location.href = `/store/download/${itemId}`;
}

// TODO: Integrate Stripe Checkout or Paypal for real payments
