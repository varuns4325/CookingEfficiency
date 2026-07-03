// Kitchen Activity Detector - Client-side JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize file upload handlers
    initializeFileUploads();
    
    // Initialize form validation
    initializeFormValidation();
    
    // Initialize tooltips and other Bootstrap components
    initializeBootstrapComponents();

    // Attach progress handler for video form
    setupVideoProgressUI();
});

function initializeFileUploads() {
    const imageInput = document.getElementById('imageFile');
    const videoInput = document.getElementById('videoFile');
    
    if (imageInput) {
        imageInput.addEventListener('change', function(e) {
            validateFileUpload(e.target, 'image');
        });
    }
    
    if (videoInput) {
        videoInput.addEventListener('change', function(e) {
            validateFileUpload(e.target, 'video');
        });
    }
}

function validateFileUpload(input, type) {
    const file = input.files[0];
    if (!file) return;
    
    const maxSize = 100 * 1024 * 1024; // 100MB
    const allowedImageTypes = ['image/jpeg', 'image/jpg', 'image/png'];
    const allowedVideoTypes = ['video/mp4', 'video/avi', 'video/quicktime'];
    
    let isValid = true;
    let errorMessage = '';
    
    // Check file size
    if (file.size > maxSize) {
        isValid = false;
        errorMessage = 'File size must be less than 100MB';
    }
    
    // Check file type
    if (type === 'image' && !allowedImageTypes.includes(file.type)) {
        isValid = false;
        errorMessage = 'Please select a valid image file (JPG, PNG)';
    } else if (type === 'video' && !allowedVideoTypes.includes(file.type)) {
        isValid = false;
        errorMessage = 'Please select a valid video file (MP4, AVI, MOV)';
    }
    
    // Update UI based on validation
    if (isValid) {
        input.classList.remove('is-invalid');
        input.classList.add('is-valid');
        
        // Show file info
        showFileInfo(input, file);
        
        // Enable submit button
        const submitBtn = input.closest('form').querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
        }
    } else {
        input.classList.remove('is-valid');
        input.classList.add('is-invalid');
        
        // Show error message
        showFileError(input, errorMessage);
        
        // Disable submit button
        const submitBtn = input.closest('form').querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
        }
    }
}

function showFileInfo(input, file) {
    // Remove existing info/error elements
    const existingInfo = input.parentNode.querySelector('.file-info');
    const existingError = input.parentNode.querySelector('.file-error');
    if (existingInfo) existingInfo.remove();
    if (existingError) existingError.remove();
    
    // Create file info element
    const fileInfo = document.createElement('div');
    fileInfo.className = 'file-info text-success small mt-1';
    fileInfo.innerHTML = `
        <i class="fas fa-check-circle me-1"></i>
        ${file.name} (${formatFileSize(file.size)})
    `;
    
    input.parentNode.appendChild(fileInfo);
}

function showFileError(input, message) {
    // Remove existing info/error elements
    const existingInfo = input.parentNode.querySelector('.file-info');
    const existingError = input.parentNode.querySelector('.file-error');
    if (existingInfo) existingInfo.remove();
    if (existingError) existingError.remove();
    
    // Create error element
    const fileError = document.createElement('div');
    fileError.className = 'file-error text-danger small mt-1';
    fileError.innerHTML = `
        <i class="fas fa-exclamation-triangle me-1"></i>
        ${message}
    `;
    
    input.parentNode.appendChild(fileError);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function initializeFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            const fileInput = form.querySelector('input[type="file"]');
            
            if (fileInput && !fileInput.files.length) {
                e.preventDefault();
                showAlert('Please select a file to upload', 'warning');
                return;
            }
            
            // Show loading state
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2" role="status"></span>
                    Processing...
                `;
            }
        });
    });
}

function setupVideoProgressUI() {
    const form = document.getElementById('videoUploadForm');
    if (!form) return;
    const jobInput = document.getElementById('jobId');
    const modalEl = document.getElementById('progressModal');
    const progressBar = document.getElementById('progressBar');
    const progressText = document.getElementById('progressText');
    const progressPercent = document.getElementById('progressPercent');

    const modal = modalEl ? new bootstrap.Modal(modalEl, { backdrop: 'static', keyboard: false }) : null;

    form.addEventListener('submit', () => {
        // Generate a client job id to correlate; server also creates one, but we use this for UX only
        const jobId = cryptoRandomId();
        if (jobInput) jobInput.value = jobId;
        if (modal) modal.show();

        // Start polling progress
        let poller = setInterval(async () => {
            try {
                const res = await fetch(`/progress/${jobId}`, { cache: 'no-store' });
                if (!res.ok) return;
                const data = await res.json();
                const processed = data.processed || 0;
                const total = data.total || 0;
                const pct = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : Math.min(99, Math.floor(processed % 100));
                if (progressBar) progressBar.style.width = `${pct}%`;
                if (progressPercent) progressPercent.textContent = `${pct}%`;
                if (progressText) progressText.textContent = `${processed} / ${total || '?' } frames`;
                if (data.done || pct >= 99) {
                    clearInterval(poller);
                    setTimeout(() => { if (modal) modal.hide(); }, 300);
                }
            } catch (_) {
                // ignore
            }
        }, 500);
    });
}

function cryptoRandomId() {
    // 16 hex chars
    const arr = new Uint8Array(8);
    if (window.crypto && window.crypto.getRandomValues) {
        window.crypto.getRandomValues(arr);
    } else {
        for (let i = 0; i < arr.length; i++) arr[i] = Math.floor(Math.random() * 256);
    }
    return Array.from(arr).map(b => b.toString(16).padStart(2, '0')).join('');
}

function initializeBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => 
        new bootstrap.Tooltip(tooltipTriggerEl)
    );
    
    // Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
}

function showAlert(message, type = 'info') {
    const alertsContainer = document.querySelector('.container');
    if (!alertsContainer) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    alertsContainer.insertBefore(alert, alertsContainer.firstChild);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}

// Utility functions for webcam page
function formatTime(seconds) {
    if (seconds < 60) {
        return `${Math.round(seconds)}s`;
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.round(seconds % 60);
        return `${minutes}m ${remainingSeconds}s`;
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return `${hours}h ${minutes}m`;
    }
}

// Check for camera permissions
function checkCameraPermissions() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        return navigator.permissions.query({ name: 'camera' })
            .then(permissionStatus => {
                return permissionStatus.state !== 'denied';
            })
            .catch(() => true); // Assume allowed if can't check
    }
    return Promise.resolve(false);
}

// Handle page visibility changes to pause/resume camera
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Page is hidden, pause camera operations if active
        const stopBtn = document.getElementById('stopBtn');
        if (stopBtn && stopBtn.style.display !== 'none') {
            console.log('Page hidden, maintaining camera connection');
        }
    } else {
        // Page is visible again
        console.log('Page visible again');
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Escape key to stop webcam
    if (e.key === 'Escape') {
        const stopBtn = document.getElementById('stopBtn');
        if (stopBtn && stopBtn.style.display !== 'none') {
            stopBtn.click();
        }
    }
    
    // Space bar to start/stop webcam
    if (e.code === 'Space' && e.target.tagName !== 'INPUT') {
        e.preventDefault();
        const startBtn = document.getElementById('startBtn');
        const stopBtn = document.getElementById('stopBtn');
        
        if (startBtn && startBtn.style.display !== 'none') {
            startBtn.click();
        } else if (stopBtn && stopBtn.style.display !== 'none') {
            stopBtn.click();
        }
    }
});

// Performance monitoring for webcam
let performanceMetrics = {
    frameCount: 0,
    startTime: null,
    lastFrameTime: null
};

function trackPerformance() {
    const now = performance.now();
    
    if (!performanceMetrics.startTime) {
        performanceMetrics.startTime = now;
    }
    
    performanceMetrics.frameCount++;
    performanceMetrics.lastFrameTime = now;
    
    // Log performance every 30 frames
    if (performanceMetrics.frameCount % 30 === 0) {
        const elapsed = now - performanceMetrics.startTime;
        const fps = (performanceMetrics.frameCount / elapsed) * 1000;
        console.log(`Performance: ${fps.toFixed(1)} FPS over ${performanceMetrics.frameCount} frames`);
    }
}

// Export functions for use in other scripts
window.KitchenActivityDetector = {
    formatTime,
    checkCameraPermissions,
    trackPerformance,
    showAlert
};
