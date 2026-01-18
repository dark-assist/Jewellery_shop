// Main JavaScript for Jewellery Shop

document.addEventListener('DOMContentLoaded', function() {
    // Auto-update gold rates every hour
    updateGoldRates();
    setInterval(updateGoldRates, 3600000); // Update every hour
    
    // Handle image zoom for mobile
    setupImageZoom();
    
    // Initialize admin functionality if on admin page
    if (window.location.pathname.includes('/admin')) {
        initializeAdmin();
    }
});

function updateGoldRates() {
    fetch('/api/rates')
        .then(response => response.json())
        .then(data => {
            // Update rates on homepage if elements exist
            const goldRateElement = document.querySelector('.rate-item:first-child .price');
            const silverRateElement = document.querySelector('.rate-item:nth-child(2) .price');
            const timeElement = document.querySelector('.rate-item:last-child .time');
            
            if (goldRateElement) {
                goldRateElement.textContent = `₹${data.gold_22k.toFixed(2)} / গ্রাম`;
            }
            
            if (silverRateElement) {
                silverRateElement.textContent = `₹${data.silver.toFixed(2)} / গ্রাম`;
            }
            
            if (timeElement) {
                timeElement.textContent = data.updated_at;
            }
        })
        .catch(error => console.error('Error fetching rates:', error));
}

function setupImageZoom() {
    const images = document.querySelectorAll('.product-image img');
    images.forEach(img => {
        img.addEventListener('click', function() {
            if (window.innerWidth < 768) {
                // Toggle zoom class
                this.classList.toggle('zoomed');
                
                // Add overlay for better viewing
                if (this.classList.contains('zoomed')) {
                    const overlay = document.createElement('div');
                    overlay.className = 'image-overlay';
                    overlay.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        right: 0;
                        bottom: 0;
                        background: rgba(0,0,0,0.8);
                        z-index: 999;
                    `;
                    overlay.addEventListener('click', function() {
                        img.classList.remove('zoomed');
                        document.body.removeChild(this);
                    });
                    document.body.appendChild(overlay);
                }
            }
        });
    });
}

function calculatePrice(weight, makingCharge) {
    // This function would be called from product page
    // The actual calculation is done server-side
    return 0;
}

// Admin functionality
function initializeAdmin() {
    // Scope JS to admin container only to avoid interfering with non-admin forms
    const adminRoot = document.querySelector('.admin-container');
    if (!adminRoot) return;

    // Handle form submissions only inside admin container
    const forms = adminRoot.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            // Client-side validation
            const requiredFields = this.querySelectorAll('[required]');
            let isValid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    isValid = false;
                    field.style.borderColor = '#f44336';
                } else {
                    field.style.borderColor = '#ddd';
                }
            });
            
            if (!isValid) {
                e.preventDefault();
                alert('দয়া করুন সব প্রয়োজনীয় তথ্য পূরণ করুন');
            }
        });
    });
    
    // Handle image preview only in admin container
    const imageInputs = adminRoot.querySelectorAll('input[type="file"]');
    imageInputs.forEach(input => {
        input.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(event) {
                    // Find or create preview container
                    let previewContainer = input.parentNode.querySelector('.image-preview');
                    if (!previewContainer) {
                        previewContainer = document.createElement('div');
                        previewContainer.className = 'image-preview';
                        previewContainer.style.cssText = `
                            margin-top: 10px;
                            max-width: 200px;
                        `;
                        input.parentNode.appendChild(previewContainer);
                    }
                    
                    previewContainer.innerHTML = `
                        <img src="${event.target.result}" 
                             style="max-width: 100%; border-radius: 5px; border: 1px solid #ddd;">
                        <p style="font-size: 12px; color: #666; margin-top: 5px;">
                            নির্বাচিত ছবি: ${file.name}
                        </p>
                    `;
                };
                reader.readAsDataURL(file);
            }
        });
    });
    
    // Confirm delete actions inside admin
    const deleteButtons = adminRoot.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            if (!confirm('আপনি কি নিশ্চিত যে আপনি এই আইটেমটি মুছে ফেলতে চান?')) {
                e.preventDefault();
            }
        });
    });
}

// Utility function to format currency
function formatCurrency(amount) {
    return '₹' + amount.toLocaleString('en-IN');
}

// Share product via WhatsApp
function shareViaWhatsApp(productName, price) {
    const text = `আমি ${productName} সম্পর্কে জানতে চাই - আনুমানিক দাম: ${formatCurrency(price)}`;
    const url = `https://wa.me/${window.shopWhatsApp || '919876543210'}?text=${encodeURIComponent(text)}`;
    window.open(url, '_blank');
}

// Call shop
function callShop() {
    window.location.href = `tel:${window.shopPhone || '+919876543210'}`;
}

// Set global variables if needed
window.shopPhone = document.querySelector('meta[name="shop-phone"]')?.content;
window.shopWhatsApp = document.querySelector('meta[name="shop-whatsapp"]')?.content;