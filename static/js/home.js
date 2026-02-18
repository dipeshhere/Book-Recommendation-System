// State management
let searchTimeout;
let allBooks = [];

// DOM elements
const bookSearch = document.getElementById('bookSearch');
const searchResults = document.getElementById('searchResults');
const searchBtn = document.getElementById('searchBtn');
const recommendationsSection = document.getElementById('recommendationsSection');
const recommendationsGrid = document.getElementById('recommendationsGrid');
const selectedBookEl = document.getElementById('selectedBook');
const favoritesGrid = document.getElementById('favoritesGrid');
const logoutBtn = document.getElementById('logoutBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const refreshFavoritesBtn = document.getElementById('refreshFavorites');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadFavorites();
    setupEventListeners();
});

function setupEventListeners() {
    // Search functionality
    bookSearch.addEventListener('input', handleSearch);
    searchBtn.addEventListener('click', () => {
        if (bookSearch.value.trim()) {
            selectBook(bookSearch.value.trim());
        }
    });
    
    // Quick picks
    document.querySelectorAll('.quick-pick-card').forEach(card => {
        card.addEventListener('click', () => {
            const bookName = card.getAttribute('data-book');
            selectBook(bookName);
        });
    });
    
    // Logout
    logoutBtn.addEventListener('click', handleLogout);
    
    // Refresh favorites
    refreshFavoritesBtn.addEventListener('click', loadFavorites);
    
    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-container')) {
            searchResults.classList.remove('active');
        }
    });
}

async function handleSearch(e) {
    const query = e.target.value.trim();
    
    clearTimeout(searchTimeout);
    
    if (query.length < 2) {
        searchResults.classList.remove('active');
        return;
    }
    
    searchTimeout = setTimeout(async () => {
        try {
            const response = await fetch(`/api/books/search?q=${encodeURIComponent(query)}`);
            const data = await response.json();
            
            if (data.books && data.books.length > 0) {
                displaySearchResults(data.books);
            } else {
                searchResults.innerHTML = '<div class="search-result-item">No books found</div>';
                searchResults.classList.add('active');
            }
        } catch (error) {
            console.error('Search error:', error);
        }
    }, 300);
}

function displaySearchResults(books) {
    searchResults.innerHTML = books.map(book => 
        `<div class="search-result-item" onclick="selectBook('${book.replace(/'/g, "\\'")}')">${book}</div>`
    ).join('');
    searchResults.classList.add('active');
}

async function selectBook(bookName) {
    searchResults.classList.remove('active');
    bookSearch.value = bookName;
    
    loadingOverlay.classList.add('active');
    
    try {
        const response = await fetch('/api/books/recommend', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
                book_name: bookName,
                n_recommendations: 6
            }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayRecommendations(data.book, data.recommendations);
        } else {
            alert(data.message || 'Failed to get recommendations');
        }
    } catch (error) {
        console.error('Recommendation error:', error);
        alert('An error occurred while fetching recommendations');
    } finally {
        loadingOverlay.classList.remove('active');
    }
}

function displayRecommendations(sourceBook, recommendations) {
    selectedBookEl.textContent = `"${sourceBook}"`;
    recommendationsSection.style.display = 'block';
    
    recommendationsGrid.innerHTML = recommendations.map(book => `
        <div class="book-card" onclick="searchBookOnGoogle('${book.title.replace(/'/g, "\\'")}', '${book.author.replace(/'/g, "\\'")}')">
            <button class="btn-favorite" onclick="event.stopPropagation(); addToFavorites('${book.title.replace(/'/g, "\\'")}')">
                ❤️
            </button>
            <h3>${book.title}</h3>
            <p class="author">by ${book.author}</p>
            <p class="year">Published: ${book.year}</p>
        </div>
    `).join('');
    
    // Smooth scroll to recommendations
    recommendationsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function searchBookOnGoogle(title, author) {
    const searchQuery = `${title} ${author}`;
    const googleSearchUrl = `https://www.google.com/search?q=${encodeURIComponent(searchQuery)}`;
    window.open(googleSearchUrl, '_blank');
}

async function addToFavorites(bookTitle) {
    try {
        const response = await fetch('/api/favorites/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ book_title: bookTitle }),
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Added to favorites! ❤️');
            loadFavorites();
        } else {
            showNotification(data.message, 'error');
        }
    } catch (error) {
        console.error('Add favorite error:', error);
        showNotification('Failed to add to favorites', 'error');
    }
}

async function loadFavorites() {
    try {
        const response = await fetch('/api/favorites');
        const data = await response.json();
        
        if (data.success && data.favorites.length > 0) {
            favoritesGrid.innerHTML = data.favorites.map(fav => `
                <div class="book-card" onclick="selectBook('${fav.title.replace(/'/g, "\\'")}')">
                    <h3>${fav.title}</h3>
                    <p class="author" style="font-size: 0.9rem; color: var(--text-muted);">
                        Added ${new Date(fav.added_at).toLocaleDateString()}
                    </p>
                </div>
            `).join('');
        } else {
            favoritesGrid.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon">📖</div>
                    <p>No favorites yet. Start exploring!</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Load favorites error:', error);
    }
}

async function handleLogout() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
        });
        
        if (response.ok) {
            window.location.href = '/';
        }
    } catch (error) {
        console.error('Logout error:', error);
    }
}

function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        background: ${type === 'success' ? 'var(--secondary)' : '#f44336'};
        color: white;
        padding: 1rem 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        z-index: 1000;
        animation: slideInRight 0.3s ease;
        font-weight: 600;
    `;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOutRight {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);
