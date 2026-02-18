from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
import pandas as pd
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.neighbors import NearestNeighbors
import pickle
import os
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import datetime
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'
CORS(app)

# Database setup
DATABASE = 'users.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with app.app_context():
        db = get_db()
        db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        db.execute('''
            CREATE TABLE IF NOT EXISTS user_favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                book_title TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        db.commit()

# Recommendation System
class BookRecommender:
    def __init__(self):
        self.model = None
        self.book_pivot = None
        self.books_data = None
        self.loaded = False
    
    def load_data(self):
        """Load and prepare data for recommendations"""
        try:
            # Check if CSV files exist
            if not os.path.exists('data/Books.csv'):
                print("Warning: Books.csv not found. Using dummy data.")
                self.create_dummy_data()
                return
            
            # Load data
            books = pd.read_csv('data/Books.csv', encoding='latin-1', on_bad_lines='skip')
            ratings = pd.read_csv('data/Ratings.csv', encoding='latin-1', on_bad_lines='skip')
            
            # Rename columns
            books = books[['ISBN', 'Book-Title', 'Book-Author', 'Year-Of-Publication', 'Publisher']]
            books.rename(columns={
                "Book-Title": "title",
                "Book-Author": "author",
                "Year-Of-Publication": "year",
                "Publisher": "publisher"
            }, inplace=True)
            
            ratings.rename(columns={"User-ID": "user_id", "Book-Rating": "rating"}, inplace=True)
            
            # Filter users with more than 200 ratings
            x = ratings['user_id'].value_counts() > 200
            y = x[x].index
            ratings = ratings[ratings['user_id'].isin(y)]
            
            # Merge with books and filter popular books
            rating_with_books = ratings.merge(books, on='ISBN')
            number_rating = rating_with_books.groupby('title')['rating'].count().reset_index()
            number_rating.rename(columns={'rating': 'num_of_rating'}, inplace=True)
            
            final_ratings = rating_with_books.merge(number_rating, on='title')
            final_ratings = final_ratings[final_ratings['num_of_rating'] >= 50]
            final_ratings.drop_duplicates(['user_id', 'title'], inplace=True)
            
            # Create pivot table
            self.book_pivot = final_ratings.pivot_table(
                columns='user_id',
                index='title',
                values='rating'
            ).fillna(0)
            
            # Store book metadata
            self.books_data = books.drop_duplicates('title').set_index('title')
            
            # Create and train model
            book_sparse = csr_matrix(self.book_pivot)
            self.model = NearestNeighbors(algorithm='brute', metric='cosine')
            self.model.fit(book_sparse)
            
            self.loaded = True
            print(f"Loaded {len(self.book_pivot)} books for recommendations")
            
        except Exception as e:
            print(f"Error loading data: {e}")
            self.create_dummy_data()
    
    def create_dummy_data(self):
        """Create dummy data for demonstration if real data is not available"""
        dummy_books = [
            "The Great Gatsby", "To Kill a Mockingbird", "1984", "Pride and Prejudice",
            "The Catcher in the Rye", "Animal Farm", "Lord of the Flies", "Brave New World",
            "The Hobbit", "Harry Potter and the Sorcerer's Stone", "The Da Vinci Code",
            "The Alchemist", "The Little Prince", "Charlotte's Web", "The Lion, the Witch and the Wardrobe",
            "The Lord of the Rings", "Harry Potter and the Chamber of Secrets", "The Chronicles of Narnia",
            "Fahrenheit 451", "The Hunger Games", "Divergent", "The Fault in Our Stars",
            "Gone Girl", "The Girl with the Dragon Tattoo", "The Book Thief", "Life of Pi",
            "The Kite Runner", "The Help", "The Lovely Bones", "Water for Elephants",
            "The Time Traveler's Wife", "The Secret Life of Bees", "Memoirs of a Geisha",
            "The Curious Incident of the Dog in the Night-Time", "The Perks of Being a Wallflower",
            "Looking for Alaska", "An Abundance of Katherines", "Paper Towns", "Turtles All the Way Down"
        ]
        
        # Create simple pivot with more realistic random data
        np.random.seed(42)
        self.book_pivot = pd.DataFrame(
            np.random.randint(0, 6, size=(len(dummy_books), 100)),
            index=dummy_books
        )
        
        # Create dummy book data with more variety
        authors = [
            "F. Scott Fitzgerald", "Harper Lee", "George Orwell", "Jane Austen",
            "J.D. Salinger", "George Orwell", "William Golding", "Aldous Huxley",
            "J.R.R. Tolkien", "J.K. Rowling", "Dan Brown", "Paulo Coelho",
            "Antoine de Saint-Exupéry", "E.B. White", "C.S. Lewis",
            "J.R.R. Tolkien", "J.K. Rowling", "C.S. Lewis",
            "Ray Bradbury", "Suzanne Collins", "Veronica Roth", "John Green",
            "Gillian Flynn", "Stieg Larsson", "Markus Zusak", "Yann Martel",
            "Khaled Hosseini", "Kathryn Stockett", "Alice Sebold", "Sara Gruen",
            "Audrey Niffenegger", "Sue Monk Kidd", "Arthur Golden",
            "Mark Haddon", "Stephen Chbosky",
            "John Green", "John Green", "John Green", "John Green"
        ]
        
        years = [
            '1925', '1960', '1949', '1813', '1951', '1945', '1954', '1932',
            '1937', '1997', '2003', '1988', '1943', '1952', '1950',
            '1954', '1998', '1950',
            '1953', '2008', '2011', '2012',
            '2012', '2005', '2005', '2001',
            '2003', '2009', '2002', '2006',
            '2003', '2002', '1997',
            '2003', '1999',
            '2005', '2006', '2008', '2017'
        ]
        
        self.books_data = pd.DataFrame({
            'author': authors,
            'year': years,
            'publisher': ['Various Publishers'] * len(dummy_books)
        }, index=dummy_books)
        
        # Train model on dummy data
        book_sparse = csr_matrix(self.book_pivot.values)
        self.model = NearestNeighbors(algorithm='brute', metric='cosine')
        self.model.fit(book_sparse)
        
        self.loaded = True
        print("Using dummy data for demonstration")
        print(f"Available books: {len(dummy_books)}")
    
    def recommend(self, book_name, n_recommendations=5):
        """Get book recommendations"""
        if not self.loaded:
            return []
        
        try:
            original_book_name = book_name
            
            # Exact match first
            if book_name not in self.book_pivot.index:
                # Try case-insensitive exact match
                available_books = list(self.book_pivot.index)
                exact_matches = [book for book in available_books if book.lower() == book_name.lower()]
                
                if exact_matches:
                    book_name = exact_matches[0]
                else:
                    # Find partial matches
                    partial_matches = [book for book in available_books if book_name.lower() in book.lower()]
                    
                    if partial_matches:
                        book_name = partial_matches[0]
                        print(f"Using closest match: '{book_name}' for query '{original_book_name}'")
                    else:
                        # Try reverse search (query in book title)
                        reverse_matches = [book for book in available_books if any(word.lower() in book.lower() for word in book_name.split())]
                        
                        if reverse_matches:
                            book_name = reverse_matches[0]
                            print(f"Using closest match: '{book_name}' for query '{original_book_name}'")
                        else:
                            print(f"No match found for '{original_book_name}'. Available books: {len(available_books)}")
                            return None
            
            book_id = np.where(self.book_pivot.index == book_name)[0][0]
            distances, suggestions = self.model.kneighbors(
                self.book_pivot.iloc[book_id, :].values.reshape(1, -1),
                n_neighbors=min(n_recommendations + 1, len(self.book_pivot))
            )
            
            recommended_books = []
            for i in range(1, len(suggestions[0])):
                book_title = self.book_pivot.index[suggestions[0][i]]  # Fixed: suggestions[0][i] instead of suggestions[i]
                book_info = {
                    'title': book_title,
                    'author': self.books_data.loc[book_title, 'author'] if book_title in self.books_data.index else 'Unknown',
                    'year': str(self.books_data.loc[book_title, 'year']) if book_title in self.books_data.index else 'N/A',
                    'similarity': float(max(0, 1 - distances[0][i]))  # Ensure non-negative
                }
                recommended_books.append(book_info)
            
            return recommended_books
        except Exception as e:
            print(f"Error getting recommendations for '{book_name}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_all_books(self):
        """Get list of all available books"""
        if not self.loaded:
            return []
        return list(self.book_pivot.index)
    
    def search_books(self, query):
        """Search for books by title"""
        if not self.loaded:
            return []
        
        query = query.lower()
        matches = [book for book in self.book_pivot.index if query in book.lower()]
        return matches[:20]  # Return top 20 matches

# Initialize recommender
recommender = BookRecommender()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/home')
def home():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    return render_template('home.html', username=session.get('username'))

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        # Hash password
        hashed_password = generate_password_hash(password)
        
        db = get_db()
        try:
            db.execute(
                'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                (username, email, hashed_password)
            )
            db.commit()
            return jsonify({'success': True, 'message': 'Registration successful'})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'message': 'Username or email already exists'}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        db = get_db()
        user = db.execute(
            'SELECT * FROM users WHERE username = ?',
            (username,)
        ).fetchone()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return jsonify({'success': True, 'message': 'Login successful'})
        else:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/books/search', methods=['GET'])
def search_books():
    query = request.args.get('q', '')
    if not query:
        return jsonify({'books': recommender.get_all_books()[:50]})
    
    results = recommender.search_books(query)
    return jsonify({'books': results})

@app.route('/api/books/recommend', methods=['POST'])
def get_recommendations():
    try:
        data = request.get_json()
        book_name = data.get('book_name')
        n_recommendations = data.get('n_recommendations', 5)
        
        if not book_name:
            return jsonify({'success': False, 'message': 'Book name is required'}), 400
        
        recommendations = recommender.recommend(book_name, n_recommendations)
        
        if recommendations is None or not recommendations:
            # Get list of available books for helpful error message
            available_books = recommender.get_all_books()[:10]  # Show first 10
            return jsonify({
                'success': False,
                'message': f'Book "{book_name}" not found. Try searching from the list or use Quick Picks below.',
                'suggestions': available_books
            }), 404
        
        return jsonify({
            'success': True,
            'book': book_name,
            'recommendations': recommendations
        })
    except Exception as e:
        print(f"Error in get_recommendations: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/favorites/add', methods=['POST'])
def add_favorite():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        book_title = data.get('book_title')
        
        db = get_db()
        db.execute(
            'INSERT INTO user_favorites (user_id, book_title) VALUES (?, ?)',
            (session['user_id'], book_title)
        )
        db.commit()
        
        return jsonify({'success': True, 'message': 'Added to favorites'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/favorites', methods=['GET'])
def get_favorites():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    try:
        db = get_db()
        favorites = db.execute(
            'SELECT book_title, added_at FROM user_favorites WHERE user_id = ? ORDER BY added_at DESC',
            (session['user_id'],)
        ).fetchall()
        
        return jsonify({
            'success': True,
            'favorites': [{'title': f['book_title'], 'added_at': f['added_at']} for f in favorites]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    # Initialize database
    init_db()
    
    # Load recommendation model
    print("Loading recommendation system...")
    recommender.load_data()
    
    # Run the app
    app.run(debug=True, host='0.0.0.0', port=5000)