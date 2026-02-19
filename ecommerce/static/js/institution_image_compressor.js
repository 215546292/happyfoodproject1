/**
 * Institution Image Compressor Utility
 * 
 * This utility compresses institution profile pictures before upload
 * to optimize storage and performance.
 * 
 * Usage:
 * 1. Include this script in your template
 * 2. Call InstitutionImageCompressor.initFileInput(fileInputElement) for each file input
 * 3. Or use InstitutionImageCompressor.initAll() to auto-initialize all profile picture inputs
 */

(function() {
    'use strict';

    window.InstitutionImageCompressor = {
        /**
         * Compress an image file to a target size (in KB)
         * @param {File} file - The image file to compress
         * @param {number} targetSizeKB - Target size in KB
         * @param {Function} callback - Callback function(file, error)
         */
        compressImage: function(file, targetSizeKB, callback) {
            if (!file || !file.type.match(/^image\//)) {
                callback(null, 'Invalid file type. Please select an image.');
                return;
            }

            const targetSizeBytes = targetSizeKB * 1024;
            const reader = new FileReader();

            reader.onload = function(e) {
                const img = new Image();
                img.onload = function() {
                    const canvas = document.createElement('canvas');
                    let width = img.width;
                    let height = img.height;
                    let quality = 0.9;
                    let minQuality = 0.1;
                    let maxDimension = 1200; // Start with reasonable max dimension

                    // Function to compress and check size
                    function compress() {
                        // Resize if dimension is too large
                        if (Math.max(width, height) > maxDimension) {
                            const ratio = maxDimension / Math.max(width, height);
                            width = Math.round(width * ratio);
                            height = Math.round(height * ratio);
                        }

                        canvas.width = width;
                        canvas.height = height;
                        const ctx = canvas.getContext('2d');
                        ctx.drawImage(img, 0, 0, width, height);

                        // Try to compress
                        canvas.toBlob(function(blob) {
                            if (!blob) {
                                callback(null, 'Failed to compress image');
                                return;
                            }

                            const blobSize = blob.size;

                            if (blobSize <= targetSizeBytes || quality <= minQuality) {
                                // Create a new File object with the compressed blob
                                const compressedFile = new File([blob], file.name, {
                                    type: 'image/jpeg',
                                    lastModified: Date.now()
                                });
                                callback(compressedFile, null);
                            } else {
                                // Reduce quality and try again
                                quality -= 0.1;
                                if (quality < minQuality) {
                                    // Try reducing dimensions
                                    maxDimension -= 100;
                                    quality = 0.9;
                                    if (maxDimension < 200) {
                                        // Use minimum quality
                                        canvas.toBlob(function(finalBlob) {
                                            const finalFile = new File([finalBlob], file.name, {
                                                type: 'image/jpeg',
                                                lastModified: Date.now()
                                            });
                                            callback(finalFile, null);
                                        }, 'image/jpeg', minQuality);
                                        return;
                                    }
                                }
                                compress();
                            }
                        }, 'image/jpeg', quality);
                    }

                    compress();
                };

                img.onerror = function() {
                    callback(null, 'Failed to load image');
                };

                img.src = e.target.result;
            };

            reader.onerror = function() {
                callback(null, 'Failed to read file');
            };

            reader.readAsDataURL(file);
        },

        /**
         * Get the stored compression preference
         * @returns {number|null} Target size in KB or null if not set
         */
        getPreference: function() {
            const stored = localStorage.getItem('institution_image_compression_size');
            return stored ? parseInt(stored) : null;
        },

        /**
         * Set the compression preference
         * @param {number} sizeKB - Target size in KB
         */
        setPreference: function(sizeKB) {
            localStorage.setItem('institution_image_compression_size', sizeKB.toString());
        },

        /**
         * Initialize compression for a file input
         * @param {HTMLElement} fileInput - The file input element
         */
        initFileInput: function(fileInput) {
            if (!fileInput || fileInput.tagName !== 'INPUT' || fileInput.type !== 'file') {
                console.error('Invalid file input element');
                return;
            }

            // Remove existing listener if any
            const newInput = fileInput.cloneNode(true);
            fileInput.parentNode.replaceChild(newInput, fileInput);

            newInput.addEventListener('change', function(e) {
                const file = e.target.files[0];
                if (!file) return;

                const preference = InstitutionImageCompressor.getPreference();
                if (!preference) {
                    // No preference set, use original file
                    return;
                }

                // Show compression indicator
                const originalFileName = file.name;
                let indicator = newInput.parentElement.querySelector('.compression-indicator');
                
                if (!indicator) {
                    indicator = document.createElement('div');
                    indicator.className = 'compression-indicator';
                    indicator.style.cssText = 'margin-top: 0.5rem; padding: 0.5rem; background: #d1ecf1; border-radius: 5px; font-size: 0.85rem; color: #0c5460;';
                    newInput.parentElement.appendChild(indicator);
                }

                indicator.style.display = 'block';
                indicator.style.background = '#d1ecf1';
                indicator.style.color = '#0c5460';
                indicator.innerHTML = '<i class="fas fa-compress-arrows-alt me-2"></i>Compressing image...';

                // Compress the image
                InstitutionImageCompressor.compressImage(file, preference, function(compressedFile, error) {
                    if (error) {
                        indicator.style.background = '#f8d7da';
                        indicator.style.color = '#721c24';
                        indicator.innerHTML = '<i class="fas fa-exclamation-circle me-2"></i>Compression failed: ' + error;
                        setTimeout(function() {
                            indicator.style.display = 'none';
                        }, 5000);
                        return;
                    }

                    // Replace the file in the input
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(compressedFile);
                    newInput.files = dataTransfer.files;

                    // Update indicator
                    const originalSize = (file.size / 1024).toFixed(2);
                    const compressedSize = (compressedFile.size / 1024).toFixed(2);
                    const savings = ((1 - compressedFile.size / file.size) * 100).toFixed(1);
                    
                    indicator.style.background = '#d4edda';
                    indicator.style.color = '#155724';
                    indicator.innerHTML = `<i class="fas fa-check-circle me-2"></i>Image compressed: ${originalSize}KB → ${compressedSize}KB (${savings}% reduction)`;
                    
                    // Trigger change event for form validation
                    const changeEvent = new Event('change', { bubbles: true });
                    newInput.dispatchEvent(changeEvent);
                });
            });
        },

        /**
         * Initialize compression for all institution profile picture file inputs on the page
         */
        initAll: function() {
            const selectors = [
                'input[type="file"][name*="profile_picture"]',
                'input[type="file"][id*="profile_picture"]',
                'input[type="file"][name*="institution_profile_picture"]',
                'input[type="file"][id*="institution_profile_picture"]'
            ];

            selectors.forEach(function(selector) {
                document.querySelectorAll(selector).forEach(function(input) {
                    InstitutionImageCompressor.initFileInput(input);
                });
            });
        }
    };

    // Auto-initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            InstitutionImageCompressor.initAll();
        });
    } else {
        InstitutionImageCompressor.initAll();
    }
})();

