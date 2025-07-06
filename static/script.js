// Global JavaScript for Spotify Cloud Simulator

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        setTimeout(() => {
            card.classList.add('fade-in-up');
        }, index * 100);
    });

    // Initialize file upload drag and drop
    initializeFileUpload();
    
    // Initialize tooltips
    initializeTooltips();
    
    // Check server status periodically
    setInterval(checkServerStatus, 30000); // Every 30 seconds
}

function initializeFileUpload() {
    const fileInput = document.getElementById('audio-file');
    if (!fileInput) return;

    const uploadArea = fileInput.closest('.card-body');
    if (!uploadArea) return;

    // Drag and drop events
    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFileInputDisplay(files[0]);
        }
    });

    // File input change event
    fileInput.addEventListener('change', function(e) {
        if (e.target.files.length > 0) {
            updateFileInputDisplay(e.target.files[0]);
        }
    });
}

function updateFileInputDisplay(file) {
    const fileInput = document.getElementById('audio-file');
    if (!fileInput) return;

    // Create file info display
    const fileInfo = document.createElement('div');
    fileInfo.className = 'mt-2 p-2 bg-light rounded';
    fileInfo.innerHTML = `
        <i class="fas fa-file-audio text-primary me-2"></i>
        <strong>${file.name}</strong>
        <small class="text-muted ms-2">(${formatFileSize(file.size)})</small>
    `;

    // Remove existing file info
    const existingInfo = fileInput.parentNode.querySelector('.mt-2');
    if (existingInfo) {
        existingInfo.remove();
    }

    // Add new file info
    fileInput.parentNode.appendChild(fileInfo);
}

function initializeTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Utility Functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

function showNotification(type, title, message, duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 400px;
    `;
    
    notification.innerHTML = `
        <strong>${title}</strong><br>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

function showLoadingSpinner(element, text = 'Đang xử lý...') {
    element.innerHTML = `
        <div class="d-flex align-items-center justify-content-center">
            <div class="spinner-border spinner-border-sm me-2" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            ${text}
        </div>
    `;
}

function hideLoadingSpinner(element, originalContent) {
    element.innerHTML = originalContent;
}

// API Helper Functions
async function apiRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

// Security Functions
function generateSecurityReport() {
    const report = {
        timestamp: new Date().toISOString(),
        encryption: {
            algorithm: 'AES-256-GCM',
            keySize: 256,
            nonceSize: 96,
            tagSize: 128
        },
        keyExchange: {
            algorithm: 'RSA',
            keySize: 1024,
            padding: 'PKCS#1 v1.5',
            hash: 'SHA-512'
        },
        integrity: {
            hash: 'SHA-512',
            hashSize: 512
        },
        transport: {
            protocol: 'TCP Socket',
            port: 8888,
            format: 'JSON'
        }
    };
    
    return report;
}

function validateAudioFile(file) {
    const validTypes = [
        'audio/mpeg',
        'audio/wav',
        'audio/mp4',
        'audio/flac',
        'audio/ogg'
    ];
    
    const validExtensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg'];
    
    // Check file type
    if (!validTypes.includes(file.type)) {
        const extension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
        if (!validExtensions.includes(extension)) {
            return {
                valid: false,
                error: 'Định dạng file không được hỗ trợ. Vui lòng chọn file MP3, WAV, M4A, FLAC hoặc OGG.'
            };
        }
    }
    
    // Check file size (50MB limit)
    const maxSize = 50 * 1024 * 1024; // 50MB
    if (file.size > maxSize) {
        return {
            valid: false,
            error: `File quá lớn. Kích thước tối đa là ${formatFileSize(maxSize)}.`
        };
    }
    
    // Check minimum size
    const minSize = 1024; // 1KB
    if (file.size < minSize) {
        return {
            valid: false,
            error: 'File quá nhỏ. Vui lòng chọn file âm thanh hợp lệ.'
        };
    }
    
    return { valid: true };
}

// Animation Functions
function animateProgress(progressBar, targetPercent, duration = 1000) {
    const startPercent = parseInt(progressBar.style.width) || 0;
    const increment = (targetPercent - startPercent) / (duration / 16);
    let currentPercent = startPercent;
    
    const timer = setInterval(() => {
        currentPercent += increment;
        
        if (currentPercent >= targetPercent) {
            currentPercent = targetPercent;
            clearInterval(timer);
        }
        
        progressBar.style.width = currentPercent + '%';
        progressBar.textContent = Math.round(currentPercent) + '%';
    }, 16);
}

function animateCounter(element, targetValue, duration = 1000) {
    const startValue = parseInt(element.textContent) || 0;
    const increment = (targetValue - startValue) / (duration / 16);
    let currentValue = startValue;
    
    const timer = setInterval(() => {
        currentValue += increment;
        
        if (currentValue >= targetValue) {
            currentValue = targetValue;
            clearInterval(timer);
        }
        
        element.textContent = Math.round(currentValue);
    }, 16);
}

// Error Handling
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    // showNotification('danger', 'Lỗi hệ thống', 'Đã xảy ra lỗi không mong muốn. Vui lòng thử lại.');
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('Unhandled promise rejection:', e.reason);
    showNotification('warning', 'Cảnh báo', 'Có thể có vấn đề với kết nối mạng.');
});

// Export functions for use in other scripts
window.SpotifyCloudUtils = {
    formatFileSize,
    formatDate,
    showNotification,
    showLoadingSpinner,
    hideLoadingSpinner,
    apiRequest,
    generateSecurityReport,
    validateAudioFile,
    animateProgress,
    animateCounter
};
