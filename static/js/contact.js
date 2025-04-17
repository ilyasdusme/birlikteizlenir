document.addEventListener('DOMContentLoaded', function() {
    // Bildirim banner'ını kapatma fonksiyonu
    window.closeNotification = function() {
        const banner = document.getElementById('notificationBanner');
        banner.style.display = 'none';
    };

    // İletişim formu gönderme işlemi
    document.getElementById('contactForm').addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('email').value;
        const subject = document.getElementById('subject').value;
        const message = document.getElementById('message').value;
        
        try {
            const response = await fetch('/submit_contact', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: email,
                    subject: subject,
                    message: message
                })
            });
            
            const data = await response.json();
            
            // Bildirim banner'ını göster
            const banner = document.getElementById('notificationBanner');
            const messageSpan = banner.querySelector('.notification-message');
            
            messageSpan.textContent = data.message;
            banner.style.display = 'block';
            
            if (data.success) {
                banner.className = 'notification-banner';
                this.reset();
            } else {
                banner.className = 'notification-banner error';
            }
            
            // 5 saniye sonra bildirimi otomatik kapat
            setTimeout(() => {
                banner.style.display = 'none';
            }, 5000);
            
        } catch (error) {
            console.error('Form gönderilirken hata oluştu:', error);
            const banner = document.getElementById('notificationBanner');
            const messageSpan = banner.querySelector('.notification-message');
            
            messageSpan.textContent = 'Bir hata oluştu. Lütfen tekrar deneyin.';
            banner.className = 'notification-banner error';
            banner.style.display = 'block';
            
            setTimeout(() => {
                banner.style.display = 'none';
            }, 5000);
        }
    });
}); 