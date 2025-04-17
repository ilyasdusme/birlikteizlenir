from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import requests
import os
from dotenv import load_dotenv
import json
from datetime import datetime, timedelta
import sqlite3
import random
from functools import wraps

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)  # Güvenli bir secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
TMDB_API_KEY = os.getenv('TMDB_API_KEY')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

# Veritabanı bağlantısı
def get_db():
    db = sqlite3.connect('site.db')
    db.row_factory = sqlite3.Row
    return db

# Veritabanı tablolarını oluştur
def init_db():
    conn = sqlite3.connect('site.db')
    cursor = conn.cursor()
    
    # Film girişleri tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS movie_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_movie TEXT,
            user2_movie TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # İletişim mesajları tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Ziyaretçi sayacı tablosu
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS visitors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

# Veritabanını başlat
init_db()

def get_movie_details(movie_title):
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'query': movie_title,
        'language': 'tr-TR'
    }
    response = requests.get(search_url, params=params)
    if response.status_code == 200:
        results = response.json()['results']
        if results:
            movie = results[0]
            movie_id = movie.get('id')
            
            # Film detaylarını al
            details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
            details_response = requests.get(details_url, params={
                'api_key': TMDB_API_KEY,
                'language': 'tr-TR',
                'append_to_response': 'credits,similar'
            })
            
            if details_response.status_code == 200:
                details = details_response.json()
                return {
                    'id': movie_id,
                    'title': movie.get('title'),
                    'overview': movie.get('overview'),
                    'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                    'vote_average': movie.get('vote_average'),
                    'genres': movie.get('genre_ids', []),
                    'release_date': movie.get('release_date', ''),
                    'cast': [cast['id'] for cast in details.get('credits', {}).get('cast', [])[:5]],
                    'director': [crew['id'] for crew in details.get('credits', {}).get('crew', []) if crew['job'] == 'Director'],
                    'similar_movies': [m['id'] for m in details.get('similar', {}).get('results', [])[:5]]
                }
    return None

@app.route('/search_movie', methods=['GET'])
def search_movie():
    query = request.args.get('query', '')
    if not query:
        return jsonify([])
    
    try:
        # TMDB API'sini kullanarak film araması yap
        search_url = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': query,
            'language': 'tr-TR',
            'include_adult': False
        }
        
        response = requests.get(search_url, params=params)
        response.raise_for_status()
        data = response.json()
        
        # Sonuçları işle ve zenginleştir
        results = []
        for movie in data.get('results', [])[:5]:  # İlk 5 sonucu al
            # Film detaylarını al
            movie_id = movie['id']
            details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
            details_params = {
                'api_key': TMDB_API_KEY,
                'language': 'tr-TR',
                'append_to_response': 'credits,videos'  # Oyuncular ve fragmanlar için
            }
            
            details_response = requests.get(details_url, params=details_params)
            details_response.raise_for_status()
            movie_details = details_response.json()
            
            # Türkçe başlık ve özet kontrolü
            title = movie_details.get('title', '')
            overview = movie_details.get('overview', '')
            
            # Eğer Türkçe başlık veya özet yoksa, orijinalini kullan
            if not title:
                title = movie_details.get('original_title', '')
            if not overview:
                overview = movie_details.get('original_overview', '')
            
            # Oyuncuları al
            cast = []
            if 'credits' in movie_details and 'cast' in movie_details['credits']:
                cast = [actor['name'] for actor in movie_details['credits']['cast'][:5]]  # İlk 5 oyuncu
            
            # Fragman kontrolü
            trailer = None
            if 'videos' in movie_details and 'results' in movie_details['videos']:
                for video in movie_details['videos']['results']:
                    if video['type'] == 'Trailer' and video['site'] == 'YouTube':
                        trailer = f"https://www.youtube.com/watch?v={video['key']}"
                        break
            
            result = {
                'id': movie_id,
                'title': title,
                'original_title': movie_details.get('original_title', ''),
                'overview': overview,
                'poster_path': movie_details.get('poster_path'),
                'release_date': movie_details.get('release_date', ''),
                'vote_average': movie_details.get('vote_average', 0),
                'genres': [genre['name'] for genre in movie_details.get('genres', [])],
                'cast': cast,
                'trailer': trailer,
                'popularity': movie_details.get('popularity', 0),
                'runtime': movie_details.get('runtime', 0)
            }
            results.append(result)
        
        # Sonuçları popülerliğe ve oy ortalamasına göre sırala
        results.sort(key=lambda x: (x['popularity'], x['vote_average']), reverse=True)
        
        return jsonify(results)
        
    except requests.exceptions.RequestException as e:
        print(f"Error searching for movie: {e}")
        return jsonify([])

def get_recommendations(user1_movies, user2_movies):
    # Her iki kullanıcının filmlerinin detaylarını al
    user1_details = [get_movie_details(movie) for movie in user1_movies if movie]
    user2_details = [get_movie_details(movie) for movie in user2_movies if movie]
    
    if not user1_details or not user2_details:
        return []
    
    # Genre listesini al
    genres_url = f"{TMDB_BASE_URL}/genre/movie/list"
    genres_response = requests.get(genres_url, params={'api_key': TMDB_API_KEY, 'language': 'tr-TR'})
    genres_map = {genre['id']: genre['name'] for genre in genres_response.json()['genres']} if genres_response.status_code == 200 else {}
    
    # Her iki filmin de animasyon olup olmadığını kontrol et
    is_both_animation = True
    for movie in user1_details + user2_details:
        if movie and 'genres' in movie:
            if 16 not in movie['genres']:  # 16: Animation genre ID
                is_both_animation = False
                break
    
    # Eğer her iki film de animasyon ise, animasyon filmlerini getir
    if is_both_animation:
        discover_url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'tr-TR',
            'sort_by': 'popularity.desc',
            'vote_count.gte': 1000,
            'vote_average.gte': 7.0,
            'with_genres': 16  # Animation genre
        }
        
        response = requests.get(discover_url, params=params)
        if response.status_code == 200:
            results = response.json().get('results', [])
            recommendations = []
            for movie in results[:10]:
                recommendations.append({
                    'title': movie.get('title'),
                    'overview': movie.get('overview'),
                    'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                    'vote_average': movie.get('vote_average'),
                    'genres': [genres_map.get(g) for g in movie.get('genre_ids', [])]
                })
            return recommendations
    
    # Normal öneri algoritması
    all_movie_ids = set()
    for movie in user1_details + user2_details:
        if movie and 'similar_movies' in movie:
            all_movie_ids.update(movie['similar_movies'])
    
    recommendations = []
    for movie_id in all_movie_ids:
        details_url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        response = requests.get(details_url, params={
            'api_key': TMDB_API_KEY,
            'language': 'tr-TR'
        })
        
        if response.status_code == 200:
            movie = response.json()
            recommendations.append({
                'title': movie.get('title'),
                'overview': movie.get('overview'),
                'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                'vote_average': movie.get('vote_average'),
                'genres': [genres_map.get(g['id']) for g in movie.get('genres', [])]
            })
    
    # Eğer benzer film bulunamazsa, popüler filmleri getir
    if not recommendations:
        discover_url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'tr-TR',
            'sort_by': 'popularity.desc',
            'vote_count.gte': 1000,
            'vote_average.gte': 7.0
        }
        
        response = requests.get(discover_url, params=params)
        if response.status_code == 200:
            results = response.json().get('results', [])
            for movie in results[:10]:
                recommendations.append({
                    'title': movie.get('title'),
                    'overview': movie.get('overview'),
                    'poster_path': f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else None,
                    'vote_average': movie.get('vote_average'),
                    'genres': [genres_map.get(g) for g in movie.get('genre_ids', [])]
                })
    
    # Önerileri puana göre sırala
    recommendations.sort(key=lambda x: x.get('vote_average', 0), reverse=True)
    return recommendations[:10]

# Admin giriş kontrolü için decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin giriş sayfası
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Basit bir kontrol (gerçek uygulamada daha güvenli bir yöntem kullanılmalı)
        if username == 'admin' and password == 'admin123':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin_login.html', error='Geçersiz kullanıcı adı veya şifre')
    
    return render_template('admin_login.html')

# Admin çıkış
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

# Admin paneli ana sayfa
@app.route('/admin')
@admin_required
def admin_dashboard():
    return render_template('admin.html')

# Dashboard verileri
@app.route('/admin/dashboard')
@admin_required
def get_dashboard_data():
    db = get_db()
    cursor = db.cursor()
    
    # Toplam mesaj sayısı
    cursor.execute('SELECT COUNT(*) FROM contact_messages')
    total_messages = cursor.fetchone()[0]
    
    # Bugünkü ziyaretçi sayısı
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('SELECT COUNT(*) FROM visitors WHERE date = ?', (today,))
    today_visitors = cursor.fetchone()[0]
    
    # Toplam film seçimi sayısı
    cursor.execute('SELECT COUNT(*) FROM movie_entries')
    total_movie_choices = cursor.fetchone()[0]
    
    db.close()
    
    return jsonify({
        'total_messages': total_messages,
        'today_visitors': today_visitors,
        'total_movie_choices': total_movie_choices
    })

# Mesajlar
@app.route('/admin/messages')
@admin_required
def get_messages():
    search_query = request.args.get('search', '')
    db = get_db()
    cursor = db.cursor()
    
    if search_query:
        cursor.execute('''
            SELECT * FROM contact_messages 
            WHERE email LIKE ? OR subject LIKE ? OR message LIKE ?
            ORDER BY date DESC
        ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%'))
    else:
        cursor.execute('SELECT * FROM contact_messages ORDER BY date DESC')
    
    messages = cursor.fetchall()
    db.close()
    
    return jsonify([dict(message) for message in messages])

# Trafik verileri
@app.route('/admin/traffic')
@admin_required
def get_traffic_data():
    period = int(request.args.get('period', 7))
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period)
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT date, COUNT(*) as count 
        FROM visitors 
        WHERE date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date
    ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    
    traffic_data = cursor.fetchall()
    db.close()
    
    # Eksik günleri tamamla
    dates = []
    visitors = []
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        dates.append(date_str)
        
        # O güne ait veri var mı kontrol et
        count = 0
        for data in traffic_data:
            if data['date'] == date_str:
                count = data['count']
                break
        
        visitors.append(count)
        current_date += timedelta(days=1)
    
    return jsonify({
        'dates': dates,
        'visitors': visitors
    })

# Ana sayfa ziyaretçi sayacı
@app.route('/')
def home():
    # Ziyaretçi sayısını güncelle
    db = get_db()
    cursor = db.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor.execute('INSERT INTO visitors (date) VALUES (?)', (today,))
    db.commit()
    db.close()
    
    return render_template('index.html')

@app.route('/get_recommendations', methods=['POST'])
def recommend_movies():
    data = request.json
    user1_movies = data.get('user1_movies', [])
    user2_movies = data.get('user2_movies', [])
    
    recommendations = get_recommendations(user1_movies, user2_movies)
    return jsonify(recommendations)

@app.route('/search_suggestions', methods=['POST'])
def search_suggestions():
    data = request.json
    query = data.get('query', '')
    
    if not query or len(query) < 3:  # En az 3 karakter gerekli
        return jsonify([])
    
    search_url = f"{TMDB_BASE_URL}/search/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'query': query,
        'language': 'tr-TR'
    }
    
    try:
        response = requests.get(search_url, params=params)
        if response.status_code == 200:
            results = response.json()['results']
            # Daha kesin eşleşmeleri filtrele
            filtered_results = [
                movie['title'] for movie in results 
                if query.lower() in movie['title'].lower()
            ]
            return jsonify(filtered_results[:5])  # En fazla 5 öneri
    except:
        pass
    
    return jsonify([])

@app.route('/submit_movies', methods=['POST'])
def submit_movies():
    try:
        data = request.get_json()
        user1_movie = data.get('user1_movie')
        user2_movie = data.get('user2_movie')
        
        if not user1_movie or not user2_movie:
            return jsonify({'success': False, 'message': 'Film seçimi yapılmadı'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO movie_entries (user1_movie, user2_movie)
            VALUES (?, ?)
        ''', (user1_movie, user2_movie))
        
        db.commit()
        db.close()
        
        return jsonify({'success': True, 'message': 'Film girişleri başarıyla kaydedildi'})
    except Exception as e:
        print(f"Film girişleri kaydedilirken hata oluştu: {str(e)}")
        return jsonify({'success': False, 'message': 'Film girişleri kaydedilirken bir hata oluştu'}), 500

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    try:
        data = request.get_json()
        email = data.get('email')
        subject = data.get('subject')
        message = data.get('message')
        
        if not email or not subject or not message:
            return jsonify({
                'success': False,
                'message': 'Lütfen tüm alanları doldurun'
            }), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO contact_messages (email, subject, message)
            VALUES (?, ?, ?)
        ''', (email, subject, message))
        
        db.commit()
        db.close()
        
        return jsonify({
            'success': True,
            'message': 'Mesajınız başarıyla gönderildi!'
        })
    except Exception as e:
        print(f"Mesaj kaydedilirken hata oluştu: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Mesaj gönderilirken bir hata oluştu.'
        }), 500

@app.route('/get_random_movies', methods=['GET'])
def get_random_movies():
    try:
        # Popüler filmleri getir
        discover_url = f"{TMDB_BASE_URL}/discover/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'language': 'tr-TR',
            'sort_by': 'popularity.desc',
            'vote_count.gte': 1000,
            'vote_average.gte': 7.0,
            'page': 1
        }
        
        response = requests.get(discover_url, params=params)
        if response.status_code == 200:
            results = response.json().get('results', [])
            if not results:
                return jsonify([])
            
            # İlk filmi rastgele seç
            first_movie = random.choice(results)
            first_movie_id = first_movie['id']
            
            # İlk filmin benzer filmlerini getir
            similar_url = f"{TMDB_BASE_URL}/movie/{first_movie_id}/similar"
            similar_params = {
                'api_key': TMDB_API_KEY,
                'language': 'tr-TR'
            }
            
            similar_response = requests.get(similar_url, params=similar_params)
            if similar_response.status_code == 200:
                similar_results = similar_response.json().get('results', [])
                # Benzer filmlerden birini seç
                if similar_results:
                    second_movie = random.choice(similar_results)
                    return jsonify([first_movie['title'], second_movie['title']])
            
            # Eğer benzer film bulunamazsa, popüler filmlerden rastgele ikinci bir film seç
            second_movie = random.choice(results)
            while second_movie['id'] == first_movie_id:  # Aynı filmi seçmemek için
                second_movie = random.choice(results)
            
            return jsonify([first_movie['title'], second_movie['title']])
            
    except Exception as e:
        print(f"Rastgele film seçilirken hata oluştu: {str(e)}")
        return jsonify([])

@app.route('/admin/delete_message/<int:message_id>', methods=['DELETE'])
@admin_required
def delete_message(message_id):
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM contact_messages WHERE id = ?', (message_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Mesaj başarıyla silindi.'})
    except Exception as e:
        print(f"Mesaj silinirken hata oluştu: {str(e)}")
        return jsonify({'success': False, 'message': 'Mesaj silinirken bir hata oluştu.'}), 500

if __name__ == '__main__':
    app.run(debug=True) 