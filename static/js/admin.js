document.addEventListener('DOMContentLoaded', function() {
    // Tab değiştirme işlemleri
    const navLinks = document.querySelectorAll('.nav-links li[data-tab]');
    const tabContents = document.querySelectorAll('.tab-content');

    navLinks.forEach(link => {
        link.addEventListener('click', function() {
            const tabId = this.getAttribute('data-tab');
            
            // Aktif tab'ı güncelle
            navLinks.forEach(l => l.classList.remove('active'));
            this.classList.add('active');
            
            // İlgili içeriği göster
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === tabId) {
                    content.classList.add('active');
                }
            });

            // Tab'a özel verileri yükle
            if (tabId === 'dashboard') {
                loadDashboardData();
            } else if (tabId === 'messages') {
                loadMessages();
            } else if (tabId === 'traffic') {
                loadTrafficData();
            }
        });
    });

    // Mesaj arama işlemi
    const messageSearch = document.getElementById('messageSearch');
    let searchTimeout;

    messageSearch.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadMessages(this.value);
        }, 300);
    });

    // Trafik periyodu seçimi
    const timeButtons = document.querySelectorAll('.time-btn');
    timeButtons.forEach(button => {
        button.addEventListener('click', function() {
            timeButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            const period = this.getAttribute('data-period');
            loadTrafficData(period);
        });
    });

    // Dashboard verilerini yükle
    async function loadDashboardData() {
        try {
            const response = await fetch('/admin/dashboard');
            const data = await response.json();
            
            document.getElementById('totalMessages').textContent = data.total_messages;
            document.getElementById('todayVisitors').textContent = data.today_visitors;
            document.getElementById('totalMovieChoices').textContent = data.total_movie_choices;
        } catch (error) {
            console.error('Dashboard verileri yüklenirken hata oluştu:', error);
        }
    }

    // Mesajları yükle
    async function loadMessages(searchQuery = '') {
        try {
            const response = await fetch(`/admin/messages${searchQuery ? `?search=${encodeURIComponent(searchQuery)}` : ''}`);
            const messages = await response.json();
            
            const messagesList = document.getElementById('messagesList');
            messagesList.innerHTML = '';
            
            messages.forEach(message => {
                const shortMessage = message.message.length > 100 
                    ? message.message.substring(0, 100) + '...' 
                    : message.message;
                
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${message.email}</td>
                    <td>${message.subject}</td>
                    <td>
                        ${shortMessage}
                        ${message.message.length > 100 ? 
                            `<button class="btn-read-more" data-id="${message.id}">Devamını Oku</button>` : 
                            ''}
                    </td>
                    <td>${new Date(message.timestamp).toLocaleString('tr-TR')}</td>
                    <td>
                        <button class="btn-delete" data-id="${message.id}">
                            <i class="fas fa-trash"></i> Sil
                        </button>
                    </td>
                `;
                messagesList.appendChild(row);
            });

            // Devamını Oku butonlarına event listener ekle
            document.querySelectorAll('.btn-read-more').forEach(button => {
                button.addEventListener('click', () => {
                    const message = messages.find(m => m.id === parseInt(button.dataset.id));
                    showMessageDetails(message);
                });
            });

            // Silme butonlarına event listener ekle
            document.querySelectorAll('.btn-delete').forEach(button => {
                button.addEventListener('click', () => {
                    const messageId = parseInt(button.dataset.id);
                    if (confirm('Bu mesajı silmek istediğinizden emin misiniz?')) {
                        deleteMessage(messageId);
                    }
                });
            });
        } catch (error) {
            console.error('Mesajlar yüklenirken hata oluştu:', error);
        }
    }

    // Mesaj silme fonksiyonu
    async function deleteMessage(messageId) {
        try {
            const response = await fetch(`/admin/delete_message/${messageId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Mesajı başarıyla sildikten sonra listeyi yenile
                loadMessages();
            } else {
                alert(data.message || 'Mesaj silinirken bir hata oluştu.');
            }
        } catch (error) {
            console.error('Mesaj silinirken hata oluştu:', error);
            alert('Mesaj silinirken bir hata oluştu.');
        }
    }

    // Mesaj detaylarını göster
    function showMessageDetails(message) {
        document.getElementById('modalEmail').textContent = message.email;
        document.getElementById('modalSubject').textContent = message.subject;
        document.getElementById('modalDate').textContent = new Date(message.date).toLocaleString('tr-TR');
        document.getElementById('modalMessage').textContent = message.message;
        
        const messageModal = new bootstrap.Modal(document.getElementById('messageModal'));
        messageModal.show();
    }

    // Trafik verilerini yükle
    let trafficChart = null;
    async function loadTrafficData(period = '7') {
        try {
            const response = await fetch(`/admin/traffic?period=${period}`);
            const data = await response.json();
            
            // Eğer önceki grafik varsa yok et
            if (trafficChart) {
                trafficChart.destroy();
            }
            
            // Yeni grafik oluştur
            const ctx = document.getElementById('trafficChart').getContext('2d');
            trafficChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Ziyaretçi Sayısı',
                        data: data.visitors,
                        borderColor: '#E31C5F',
                        backgroundColor: 'rgba(227, 28, 95, 0.1)',
                        tension: 0.4,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: 'rgba(0, 0, 0, 0.1)'
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            }
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Trafik verileri yüklenirken hata oluştu:', error);
        }
    }

    // Sayfa yüklendiğinde dashboard verilerini yükle
    loadDashboardData();
}); 