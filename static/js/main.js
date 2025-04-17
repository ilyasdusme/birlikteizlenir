document.addEventListener('DOMContentLoaded', function() {
    const findRecommendationsBtn = document.querySelector('.find-btn');
    const randomComboBtn = document.getElementById('randomCombo');
    const recommendationsDiv = document.getElementById('recommendations');
    const user1Input = document.getElementById('user1Movies');
    const user2Input = document.getElementById('user2Movies');
    const preview1 = document.getElementById('preview1');
    const preview2 = document.getElementById('preview2');
    const suggestions1 = document.getElementById('movieSuggestions1');
    const suggestions2 = document.getElementById('movieSuggestions2');
    const movieModal = new bootstrap.Modal(document.getElementById('movieDetailModal'));

    // Örnek film listesi
    const sampleMovies = [
        'Ex Machina', 'I Am Legend', 'Deja Vu', 'Morgan', 'The Matrix',
        'Project Almanac', 'Reminiscence', 'Selfless'
    ];

    // Film detaylarını göster
    function showMovieDetails(movie) {
        const modalTitle = document.querySelector('.modal-title');
        const modalPoster = document.querySelector('.modal-poster');
        const ratingValue = document.querySelector('.rating-value');
        const starsDiv = document.querySelector('.stars');
        const genresValue = document.querySelector('.genres-value');
        const overview = document.querySelector('.movie-overview p');

        modalTitle.textContent = movie.title;
        modalPoster.src = movie.poster_path;
        modalPoster.alt = movie.title;

        // Puan ve yıldızları göster
        const rating = movie.vote_average ? movie.vote_average.toFixed(1) : 'Puan yok';
        ratingValue.textContent = rating;
        
        // Yıldızları oluştur
        const stars = Math.round(movie.vote_average / 2);
        starsDiv.innerHTML = '';
        for (let i = 0; i < 5; i++) {
            const star = document.createElement('i');
            star.className = i < stars ? 'fas fa-star' : 'far fa-star';
            starsDiv.appendChild(star);
        }

        // Türleri göster
        genresValue.textContent = movie.genres ? movie.genres.filter(Boolean).join(', ') : 'Belirtilmemiş';
        
        // Açıklamayı göster
        overview.textContent = movie.overview || 'Film hakkında açıklama bulunmuyor.';

        movieModal.show();
    }

    // Film arama ve önizleme
    async function searchMovie(input, previewElement) {
        const query = input.value.trim();
        if (!query) {
            previewElement.innerHTML = `
                <div class="movie-preview placeholder">
                    <div class="placeholder-text">NE İZLESEK?</div>
                </div>
            `;
            return;
        }

        try {
            const response = await fetch(`/search_movie?query=${encodeURIComponent(query)}`);
            const movies = await response.json();
            
            if (movies && movies.length > 0) {
                const movie = movies[0];
                const posterUrl = movie.poster_path 
                    ? `https://image.tmdb.org/t/p/w200${movie.poster_path}`
                    : 'https://via.placeholder.com/200x300?text=Poster+Bulunamadı';
                
                previewElement.innerHTML = `
                    <div class="movie-preview">
                        <img src="${posterUrl}" alt="${movie.title}">
                    </div>
                `;
            } else {
                previewElement.innerHTML = '<p class="no-results">Film bulunamadı</p>';
            }
        } catch (error) {
            console.error('Arama hatası:', error);
            previewElement.innerHTML = '<p class="error">Arama sırasında bir hata oluştu</p>';
        }
    }

    // Film önerileri alma
    async function getSuggestions(input, datalist) {
        const query = input.value.trim();
        if (query.length < 3) {
            datalist.innerHTML = '';
            return;
        }

        try {
            const response = await fetch('/search_suggestions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query
                })
            });

            const suggestions = await response.json();
            
            // Önerileri datalist'e ekle
            datalist.innerHTML = suggestions
                .filter(suggestion => 
                    suggestion.toLowerCase().startsWith(query.toLowerCase())
                )
                .map(suggestion => `<option value="${suggestion}">`)
                .join('');
        } catch (error) {
            console.error('Error:', error);
        }
    }

    // Input değişikliklerini dinle
    let searchTimeout1, searchTimeout2;
    let suggestTimeout1, suggestTimeout2;
    let lastValue1 = '', lastValue2 = '';

    user1Input.addEventListener('input', function(e) {
        const currentValue = e.target.value;
        
        // Eğer değer otomatik tamamlama tarafından değiştirildiyse, geri al
        if (currentValue !== lastValue1 && currentValue.length - lastValue1.length > 1) {
            e.target.value = lastValue1;
            return;
        }
        
        lastValue1 = currentValue;
        clearTimeout(searchTimeout1);
        clearTimeout(suggestTimeout1);
        
        suggestTimeout1 = setTimeout(() => {
            getSuggestions(user1Input, suggestions1);
        }, 300);
        
        searchTimeout1 = setTimeout(() => {
            searchMovie(user1Input, preview1);
        }, 800);
    });

    user2Input.addEventListener('input', function(e) {
        const currentValue = e.target.value;
        
        // Eğer değer otomatik tamamlama tarafından değiştirildiyse, geri al
        if (currentValue !== lastValue2 && currentValue.length - lastValue2.length > 1) {
            e.target.value = lastValue2;
            return;
        }
        
        lastValue2 = currentValue;
        clearTimeout(searchTimeout2);
        clearTimeout(suggestTimeout2);
        
        suggestTimeout2 = setTimeout(() => {
            getSuggestions(user2Input, suggestions2);
        }, 300);
        
        searchTimeout2 = setTimeout(() => {
            searchMovie(user2Input, preview2);
        }, 800);
    });

    // Input seçildiğinde önizleme göster
    user1Input.addEventListener('change', function() {
        const selectedValue = this.value;
        if (selectedValue) {
            searchMovie(user1Input, preview1);
        }
    });

    user2Input.addEventListener('change', function() {
        const selectedValue = this.value;
        if (selectedValue) {
            searchMovie(user2Input, preview2);
        }
    });

    // Film input alanlarını gösterme/gizleme
    function focusInput(inputId) {
        const input = document.getElementById(inputId);
        input.focus();
    }

    // Rastgele film seçme fonksiyonu
    async function getRandomMovies() {
        try {
            const response = await fetch('/get_random_movies');
            const movies = await response.json();
            if (movies && movies.length === 2) {
                user1Input.value = movies[0];
                user2Input.value = movies[1];
                
                // Rastgele seçilen filmlerin önizlemelerini göster
                searchMovie(user1Input, preview1);
                searchMovie(user2Input, preview2);
                
                getRecommendations();
            }
        } catch (error) {
            console.error('Rastgele film seçilirken hata oluştu:', error);
        }
    }

    // Rastgele film seçme butonu
    randomComboBtn.addEventListener('click', getRandomMovies);

    // Film önerilerini getirme
    async function getRecommendations() {
        const user1Movie = user1Input.value.trim();
        const user2Movie = user2Input.value.trim();

        if (!user1Movie || !user2Movie) {
            showAlert('Lütfen her iki film alanını da doldurun!', 'warning');
            return;
        }

        showLoading();

        try {
            const response = await fetch('/get_recommendations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user1_movies: [user1Movie],
                    user2_movies: [user2Movie]
                })
            });

            const recommendations = await response.json();

            if (!recommendations || recommendations.length === 0) {
                showAlert('Üzgünüz, uygun film önerisi bulunamadı.', 'info');
                return;
            }

            showRecommendations(recommendations);
        } catch (error) {
            console.error('Error:', error);
            showAlert('Bir hata oluştu. Lütfen daha sonra tekrar deneyin.', 'danger');
        }
    }

    function showLoading() {
        recommendationsDiv.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Film önerileri hazırlanıyor...</p>
            </div>
        `;
    }

    function showAlert(message, type) {
        recommendationsDiv.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }

    // Film önerilerini göster
    function showRecommendations(recommendations) {
        let html = '';
        recommendations.forEach(movie => {
            html += `
                <div class="movie-card" onclick="showMovieDetails(${JSON.stringify(movie).replace(/"/g, '&quot;')})">
                    <div class="poster-container">
                        <img src="${movie.poster_path}" class="movie-poster" alt="${movie.title}">
                    </div>
                    <div class="movie-info">
                        <h3 class="movie-title">${movie.title}</h3>
                    </div>
                </div>
            `;
        });

        recommendationsDiv.innerHTML = html;
    }

    // Film önerilerini kaydırma fonksiyonları
    function scrollRecommendations(direction) {
        const container = document.querySelector('.recommendations-container');
        const scrollAmount = 300;
        
        if (direction === 'left') {
            container.scrollBy({
                left: -scrollAmount,
                behavior: 'smooth'
            });
        } else {
            container.scrollBy({
                left: scrollAmount,
                behavior: 'smooth'
            });
        }
    }

    // Her input değiştiğinde önerileri güncelle
    document.getElementById('user1Movies').addEventListener('change', getRecommendations);
    document.getElementById('user2Movies').addEventListener('change', getRecommendations);

    // Global fonksiyonları tanımla
    window.focusInput = focusInput;
    window.scrollRecommendations = scrollRecommendations;
    window.showMovieDetails = showMovieDetails;

    // Sayfa yüklendiğinde preview alanlarını başlangıç durumuna getir
    function initializePreviews() {
        const previewElements = document.querySelectorAll('.preview-container');
        previewElements.forEach(element => {
            element.innerHTML = `
                <div class="movie-preview placeholder">
                    <div class="placeholder-text">NE İZLESEK?</div>
                </div>
            `;
        });
    }

    // Sayfa yüklendiğinde preview'ları başlat
    initializePreviews();

    // Input temizlendiğinde placeholder'ı göster
    user1Input.addEventListener('input', function(e) {
        if (!e.target.value.trim()) {
            preview1.innerHTML = `
                <div class="movie-preview placeholder">
                    <div class="placeholder-text">NE İZLESEK?</div>
                </div>
            `;
        }
    });

    user2Input.addEventListener('input', function(e) {
        if (!e.target.value.trim()) {
            preview2.innerHTML = `
                <div class="movie-preview placeholder">
                    <div class="placeholder-text">NE İZLESEK?</div>
                </div>
            `;
        }
    });
}); 