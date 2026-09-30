/**
 * Global Loading State Helper
 * Provides consistent loading overlays and error handling for all fetch calls.
 */

// Global loading state
window.FetchHelper = {
    isLoading: false,
    loadingMessage: '',
    disabledButtons: new Set(),
    
    /**
     * Fetch with loading overlay and error handling
     * @param {string} url - The URL to fetch
     * @param {object} options - Fetch options (method, headers, body, etc.)
     * @param {function} onSuccess - Success callback (data, response)
     * @param {function} onError - Error callback (error)
     * @param {string} loadingMessage - Message to show in loading overlay
     * @param {HTMLElement} buttonElement - Button to disable during request
     */
    async fetchWithLoading(url, options = {}, onSuccess, onError, loadingMessage = 'Loading...', buttonElement = null) {
        try {
            // Set loading state
            this.isLoading = true;
            this.loadingMessage = loadingMessage;
            
            // Show loading overlay
            this.showLoadingOverlay(loadingMessage);
            
            // Disable button if provided
            if (buttonElement) {
                this.disableButton(buttonElement);
            }
            
            // Perform fetch
            const response = await fetch(url, options);
            
            // Parse response
            const data = await this.parseResponse(response);
            
            // Hide loading overlay
            this.hideLoadingOverlay();
            
            // Enable button if provided
            if (buttonElement) {
                this.enableButton(buttonElement);
            }
            
            // Call success callback
            if (onSuccess) {
                onSuccess(data, response);
            }
            
            return data;
            
        } catch (error) {
            // Hide loading overlay
            this.hideLoadingOverlay();
            
            // Enable button if provided
            if (buttonElement) {
                this.enableButton(buttonElement);
            }
            
            // Show error toast
            this.showErrorToast(error.message || 'Request failed');
            
            // Call error callback
            if (onError) {
                onError(error);
            }
            
            throw error;
            
        } finally {
            // Reset loading state
            this.isLoading = false;
            this.loadingMessage = '';
        }
    },
    
    /**
     * Parse JSON response or handle error
     */
    async parseResponse(response) {
        const contentType = response.headers.get('content-type');
        
        if (contentType && contentType.includes('application/json')) {
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.detail || data.message || `HTTP error! status: ${response.status}`);
            }
            
            return data;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.text();
    },
    
    /**
     * Show loading overlay
     */
    showLoadingOverlay(message) {
        // Remove existing overlay
        this.hideLoadingOverlay();
        
        // Create overlay
        const overlay = document.createElement('div');
        overlay.id = 'loading-overlay';
        overlay.innerHTML = `
            <div class="loading-spinner">
                <div class="spinner"></div>
                <p>${this.escapeHtml(message)}</p>
            </div>
        `;
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 9999;
            backdrop-filter: blur(2px);
        `;
        
        document.body.appendChild(overlay);
        
        // Add spinner styles if not already present
        if (!document.getElementById('fetch-helper-styles')) {
            const style = document.createElement('style');
            style.id = 'fetch-helper-styles';
            style.textContent = `
                .loading-spinner {
                    background: white;
                    padding: 2rem;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }
                .spinner {
                    width: 40px;
                    height: 40px;
                    margin: 0 auto 1rem;
                    border: 4px solid #f3f3f3;
                    border-top: 4px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                .loading-spinner p {
                    margin: 0;
                    color: #333;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                }
            `;
            document.head.appendChild(style);
        }
    },
    
    /**
     * Hide loading overlay
     */
    hideLoadingOverlay() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    },
    
    /**
     * Disable button to prevent double-click
     */
    disableButton(button) {
        if (!button) return;
        
        button.disabled = true;
        button.dataset.originalText = button.textContent || button.innerHTML;
        button.dataset.wasDisabled = 'true';
        
        if (button.tagName === 'BUTTON') {
            button.textContent = 'Processing...';
        }
        
        this.disabledButtons.add(button);
    },
    
    /**
     * Enable button
     */
    enableButton(button) {
        if (!button || !this.disabledButtons.has(button)) return;
        
        button.disabled = false;
        
        if (button.dataset.originalText) {
            if (button.tagName === 'BUTTON') {
                button.textContent = button.dataset.originalText;
            } else {
                button.innerHTML = button.dataset.originalText;
            }
            delete button.dataset.originalText;
        }
        
        delete button.dataset.wasDisabled;
        this.disabledButtons.delete(button);
    },
    
    /**
     * Show error toast notification
     */
    showErrorToast(message) {
        // Remove existing toasts
        this.removeToasts();
        
        const toast = document.createElement('div');
        toast.className = 'fetch-error-toast';
        toast.textContent = this.escapeHtml(message);
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #e74c3c;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 4px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 5000);
        
        // Add toast animations if not already present
        if (!document.getElementById('fetch-toast-styles')) {
            const style = document.createElement('style');
            style.id = 'fetch-toast-styles';
            style.textContent = `
                @keyframes slideIn {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOut {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
    },
    
    /**
     * Show success toast notification
     */
    showSuccessToast(message) {
        this.removeToasts();
        
        const toast = document.createElement('div');
        toast.className = 'fetch-success-toast';
        toast.textContent = this.escapeHtml(message);
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #27ae60;
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 4px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            z-index: 10000;
            animation: slideIn 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },
    
    /**
     * Remove all toasts
     */
    removeToasts() {
        document.querySelectorAll('.fetch-error-toast, .fetch-success-toast').forEach(toast => {
            toast.remove();
        });
    },
    
    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },
    
    /**
     * Convenience method for GET requests
     */
    async get(url, onSuccess, onError, loadingMessage = 'Loading...') {
        return this.fetchWithLoading(
            url,
            { method: 'GET' },
            onSuccess,
            onError,
            loadingMessage
        );
    },
    
    /**
     * Convenience method for POST requests
     */
    async post(url, data, onSuccess, onError, loadingMessage = 'Submitting...', buttonElement = null) {
        return this.fetchWithLoading(
            url,
            {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            },
            onSuccess,
            onError,
            loadingMessage,
            buttonElement
        );
    },
    
    /**
     * Convenience method for PUT requests
     */
    async put(url, data, onSuccess, onError, loadingMessage = 'Updating...', buttonElement = null) {
        return this.fetchWithLoading(
            url,
            {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            },
            onSuccess,
            onError,
            loadingMessage,
            buttonElement
        );
    },
    
    /**
     * Convenience method for DELETE requests
     */
    async delete(url, onSuccess, onError, loadingMessage = 'Deleting...', buttonElement = null) {
        return this.fetchWithLoading(
            url,
            { method: 'DELETE' },
            onSuccess,
            onError,
            loadingMessage,
            buttonElement
        );
    }
};

// Initialize on load
document.addEventListener('DOMContentLoaded', () => {
    console.log('FetchHelper loaded successfully');
});
