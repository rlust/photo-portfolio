import React, { useState, useEffect } from "react";
import ReactDOM from "react-dom";
import './GlassGallery.css';

// Helper function to fix image URLs - this ensures images are properly served from GCS via our proxy
const fixImageUrl = (url) => {
  if (!url) return '/notfound.png';
  
  const BACKEND_URL = 'https://simplified-backend-839093975626.us-central1.run.app';
  const FALLBACK_URL = 'https://simplified-backend-ymcejj57ga-uc.a.run.app';
  const SECOND_FALLBACK_URL = 'https://photoportfolio-backend-er4l5fctxq-uc.a.run.app';
  
  // If URL contains the old static path pattern, convert to use our new GCS proxy
  if (url.includes('/static/') || url.includes('/uploads/')) {
    // Extract the folder and filename from the URL
    const parts = url.split('/');
    const folder = parts[parts.length - 2] === 'static' || parts[parts.length - 2] === 'uploads' 
      ? 'test' // Default folder if coming from static or uploads
      : parts[parts.length - 2];
    const filename = parts[parts.length - 1];
    
    // Use the new GCS proxy endpoint
    return `${BACKEND_URL}/gcs-proxy/${folder}/${filename}`;
  }
  
  // If it has local: prefix, convert to use GCS proxy
  if (url.startsWith('local:')) {
    const path = url.replace('local:', '');
    const parts = path.split('/');
    const filename = parts[parts.length - 1];
    const folder = parts.length > 1 ? parts[parts.length - 2] : 'test';
    
    return `${BACKEND_URL}/gcs-proxy/${folder}/${filename}`;
  }
  
  // If it's a GCS URL, convert to use our proxy for better CORS handling
  if (url.includes('storage.googleapis.com/photoportfolio-uploads')) {
    const parts = url.split('/');
    const filename = parts[parts.length - 1];
    // Try to extract folder from path or default to test
    const folderIndex = parts.indexOf('photoportfolio-uploads') + 1;
    const folder = folderIndex < parts.length - 1 ? parts[folderIndex] : 'test';
    
    return `${BACKEND_URL}/gcs-proxy/${folder}/${filename}`;
  }
  
  return url;
};

// Extract image tags from image metadata or filename
const extractTags = (img) => {
  let tags = [];
  
  // First priority: Use AI-generated tags if available
  if (img.tags && Array.isArray(img.tags) && img.tags.length > 0) {
    // Use AI-generated tags, but limit to 5 for cleaner UI
    return img.tags.slice(0, 5);
  }
  
  // Second priority: Use location tag if available
  if (img.location_tag) {
    tags.push(img.location_tag);
  }
  
  // Add file type as a tag
  if (img.name) {
    const extension = img.name.split('.').pop().toUpperCase();
    if (extension && extension.length < 5) tags.push(extension);
  }
  
  // Extract creation date if available
  if (img.creation_date) {
    const date = new Date(img.creation_date);
    if (!isNaN(date)) {
      tags.push(date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' }));
    }
  }
  
  // Add folder as a tag if we don't have many tags yet
  if (img.folder && tags.length < 3) {
    tags.push(img.folder);
  }
  
  // Add metadata tags if available
  if (img.metadata) {
    if (img.metadata.camera && tags.length < 4) tags.push(img.metadata.camera);
    if (img.metadata.location && tags.length < 4) tags.push(img.metadata.location);
  }
  
  // Add size tag only if we don't have many tags
  if (img.size_bytes && tags.length < 3) {
    const sizeMB = (img.size_bytes / (1024 * 1024)).toFixed(1);
    tags.push(`${sizeMB}MB`);
  }
  
  // If we still don't have enough tags, extract from filename
  if (tags.length < 2 && img.name) {
    // Extract potential tags from filename
    const nameParts = img.name.replace(/\d+/g, ' ').replace(/[^a-zA-Z ]/g, ' ').split(' ');
    const filteredParts = nameParts.filter(part => 
      part.length > 3 && 
      !['IMG', 'PHOTO', 'JPG', 'JPEG', 'PNG'].includes(part.toUpperCase())
    );
    
    // Add up to 2 tags from filename
    const filenameTagsToAdd = Math.min(2, filteredParts.length);
    if (filenameTagsToAdd > 0) {
      // Format the tags with proper capitalization
      const formattedTags = filteredParts
        .slice(0, filenameTagsToAdd)
        .map(tag => tag.charAt(0).toUpperCase() + tag.slice(1).toLowerCase());
      
      tags = [...tags, ...formattedTags];
    }
  }
  
  // Add generic tags if we still don't have enough
  if (tags.length < 2) {
    const genericTags = ['Photo', 'Image', 'Nature', 'Wildlife'];
    const tagsToAdd = Math.min(2, genericTags.length);
    tags = [...tags, ...genericTags.slice(0, tagsToAdd)];
  }
  
  // Limit to 5 tags for cleaner UI
  return tags.slice(0, 5);
};

// SVG placeholder for TIFF files (browsers can't display TIFF)
const TiffPlaceholder = () => (
  <svg width="100%" height="100%" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
    <rect width="200" height="200" fill="#f0f0f0" />
    <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle" fill="#666">
      TIFF File
    </text>
    <text x="50%" y="65%" dominantBaseline="middle" textAnchor="middle" fill="#888" fontSize="12">
      Preview Not Available
    </text>
  </svg>
);

// Lightbox component for image preview
const ImageLightbox = ({ image, onClose }) => {
  const [zoomed, setZoomed] = useState(false);
  
  useEffect(() => {
    // Add keydown listener to close on escape
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);
  
  if (!image) return null;
  
  return (
    <div className="lightbox-overlay" onClick={onClose}>
      <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
        <button className="lightbox-close" onClick={onClose}>×</button>
        <div className={`lightbox-image-container ${zoomed ? 'zoomed' : ''}`}>
          <img 
            src={fixImageUrl(image.url)} 
            alt={image.name}
            onClick={() => setZoomed(!zoomed)}
            onError={(e) => {
              if (image.name && image.name.toLowerCase().endsWith('.tiff')) {
                e.target.style.display = 'none';
                const placeholder = document.createElement('div');
                placeholder.className = 'tiff-placeholder';
                e.target.parentNode.appendChild(placeholder);
                // Use React to render the TiffPlaceholder component
                ReactDOM.render(<TiffPlaceholder />, placeholder);
              } else if (image.gcs_url) {
                // Try direct GCS URL as fallback
                e.target.src = image.gcs_url;
              }
            }}
          />
        </div>
        <div className="lightbox-details glass-container">
          <h3>{image.name}</h3>
          <div className="image-tags">
            {extractTags(image).map((tag, i) => (
              <span key={i} className="image-tag">{tag}</span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

// Main GalleryView component
export default function GalleryView({ folders, onDeleteImage, onAnnotateImage }) {
  const [selectedFolder, setSelectedFolder] = useState(null);
  const [viewMode, setViewMode] = useState('folders'); // 'folders' or 'images'
  const [selectedImage, setSelectedImage] = useState(null);
  const [isDarkMode, setIsDarkMode] = useState(false);

  const folderNames = Object.keys(folders);
  
  // Compute images to display
  const images = selectedFolder ? (folders[selectedFolder] || []) : [];
  
  // Get one preview image per folder
  const folderPreviews = {};
  folderNames.forEach(folder => {
    const folderImages = folders[folder] || [];
    if (folderImages.length > 0) {
      folderPreviews[folder] = folderImages[0];
    }
  });

  useEffect(() => {
    // Apply dark/light mode to body
    document.body.classList.toggle('dark-mode', isDarkMode);
    return () => {
      document.body.classList.remove('dark-mode');
    };
  }, [isDarkMode]);

  if (!folders || folderNames.length === 0) {
    return (
      <div className={`gallery-container ${isDarkMode ? 'dark-mode' : ''}`}>
        <div className="empty-state glass-container animate-fadeUp">
          <h3>No folders or images found</h3>
          <p>Try uploading images from the Admin panel first.</p>
        </div>
      </div>
    );
  }

  // Handlers for image and folder interactions
  const openImage = (image) => {
    setSelectedImage(image);
    // Set viewMode to 'singleImage' to show only this image
    setViewMode('singleImage');
  };
  
  const closeImage = () => {
    setSelectedImage(null);
    // Return to folder view when closing the image
    if (viewMode === 'singleImage') {
      setViewMode('images');
    }
  };

  const selectFolder = (folder) => {
    setSelectedFolder(folder);
    setViewMode('images');
  };

  const backToFolders = () => {
    setViewMode('folders');
    setSelectedFolder(null);
  };
  
  const toggleTheme = () => {
    setIsDarkMode(prev => !prev);
  };

  return (
    <div className={`gallery-container ${isDarkMode ? 'dark-mode' : ''}`}>
      <div className="gallery-header glass-container">
        <h2>Photo Gallery</h2>
        <div className="gallery-controls">
          {viewMode === 'images' && (
            <button 
              className="back-button glass-button" 
              onClick={backToFolders}
            >
              <span>←</span> Back to Folders
            </button>
          )}
          <button 
            className="theme-toggle glass-button" 
            onClick={toggleTheme}
            aria-label={isDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </div>
      
      {viewMode === 'folders' ? (
        <div className="folder-preview-grid animate-fadeUp">
          {folderNames.map(folder => {
            const previewImage = folderPreviews[folder];
            const imageCount = folders[folder]?.length || 0;
            
            return (
              <div 
                key={folder} 
                className="folder-preview-card glass-container" 
                onClick={() => selectFolder(folder)}
              >
                <div className="folder-preview-image">
                  {previewImage ? (
                    <img 
                      src={fixImageUrl(previewImage.url)} 
                      alt={`Preview of ${folder}`}
                      onError={(e) => {
                        if (previewImage.name && previewImage.name.toLowerCase().endsWith('.tiff')) {
                          // Replace with TIFF placeholder
                          e.target.style.display = 'none';
                          const placeholder = document.createElement('div');
                          placeholder.className = 'tiff-placeholder';
                          e.target.parentNode.appendChild(placeholder);
                          // Use React to render the TiffPlaceholder component
                          ReactDOM.render(<TiffPlaceholder />, placeholder);
                        } else if (previewImage.gcs_url) {
                          // Try direct GCS URL as fallback
                          e.target.src = previewImage.gcs_url;
                        }
                      }}
                    />
                  ) : (
                    <div className="empty-folder-placeholder">
                      <span>No Images</span>
                    </div>
                  )}
                </div>
                <div className="folder-preview-info">
                  <h3>{folder}</h3>
                  <span className="image-count">{imageCount} {imageCount === 1 ? 'image' : 'images'}</span>
                </div>
              </div>
            );
          })}
        </div>
      ) : viewMode === 'images' ? (
        <div className="glass-gallery-grid animate-fadeUp">
          {images.map((image, index) => (
            <div key={image.id || index} className="glass-gallery-item">
              <div 
                className="glass-image-card glass-container"
                onClick={() => openImage(image)}
              >
                <div className="glass-image-wrapper">
                  <img 
                    src={fixImageUrl(image.url)} 
                    alt={image.name || 'Image'}
                    onError={(e) => {
                      if (image.name && image.name.toLowerCase().endsWith('.tiff')) {
                        // Replace with TIFF placeholder
                        e.target.style.display = 'none';
                        const placeholder = document.createElement('div');
                        placeholder.className = 'tiff-placeholder';
                        e.target.parentNode.appendChild(placeholder);
                        // Use React to render the TiffPlaceholder component
                        ReactDOM.render(<TiffPlaceholder />, placeholder);
                      } else if (image.gcs_url) {
                        // Try direct GCS URL as fallback
                        e.target.src = image.gcs_url;
                      }
                    }}
                  />
                </div>
                <div className="glass-image-info">
                  <h4>{image.name}</h4>
                  <div className="image-tags">
                    {extractTags(image).map((tag, i) => (
                      <span key={i} className="image-tag">{tag}</span>
                    ))}
                  </div>
                  {(onDeleteImage || onAnnotateImage) && (
                    <div className="image-actions">
                      {onAnnotateImage && (
                        <button 
                          className="glass-button annotate-button" 
                          onClick={(e) => {
                            e.stopPropagation();
                            onAnnotateImage(selectedFolder, image);
                          }}
                        >
                          Edit Tags
                        </button>
                      )}
                      {onDeleteImage && (
                        <button 
                          className="glass-button delete-button" 
                          onClick={(e) => {
                            e.stopPropagation();
                            if (window.confirm(`Delete ${image.name}?`)) {
                              // Pass both folder and image to onDeleteImage
                              onDeleteImage(selectedFolder, image);
                            }
                          }}
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          
          {images.length === 0 && (
            <div className="empty-folder-message glass-container">
              <p>No images in this folder</p>
            </div>
          )}
        </div>
      ) : viewMode === 'singleImage' && selectedImage ? (
        <div className="single-image-view animate-fadeUp">
          <div className="glass-image-container glass-container">
            <div className="single-image-header">
              <button 
                className="back-button glass-button" 
                onClick={closeImage}
              >
                <span>←</span> Back to Folder
              </button>
              <h3>{selectedImage.name}</h3>
            </div>
            <div className="single-image-wrapper">
              <img 
                src={fixImageUrl(selectedImage.url)} 
                alt={selectedImage.name || 'Image'}
                onError={(e) => {
                  if (selectedImage.name && selectedImage.name.toLowerCase().endsWith('.tiff')) {
                    // Replace with TIFF placeholder
                    e.target.style.display = 'none';
                    const placeholder = document.createElement('div');
                    placeholder.className = 'tiff-placeholder';
                    e.target.parentNode.appendChild(placeholder);
                    // Use React to render the TiffPlaceholder component
                    ReactDOM.render(<TiffPlaceholder />, placeholder);
                  } else if (selectedImage.gcs_url) {
                    // Try direct GCS URL as fallback
                    e.target.src = selectedImage.gcs_url;
                  }
                }}
              />
            </div>
            <div className="single-image-info">
              <div className="image-tags">
                {extractTags(selectedImage).map((tag, i) => (
                  <span key={i} className="image-tag">{tag}</span>
                ))}
              </div>
              {(onDeleteImage || onAnnotateImage) && (
                <div className="image-actions">
                  {onAnnotateImage && (
                    <button 
                      className="glass-button annotate-button" 
                      onClick={() => onAnnotateImage(selectedFolder, selectedImage)}
                    >
                      Edit Tags
                    </button>
                  )}
                  {onDeleteImage && (
                    <button 
                      className="glass-button delete-button" 
                      onClick={() => {
                        if (window.confirm(`Delete ${selectedImage.name}?`)) {
                          // Pass both folder and image to onDeleteImage
                          onDeleteImage(selectedFolder, selectedImage);
                          closeImage();
                        }
                      }}
                    >
                      Delete
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      ) : null}
      
      {viewMode !== 'singleImage' && selectedImage && (
        <ImageLightbox 
          image={selectedImage}
          onClose={closeImage}
        />
      )}
    </div>
  );
}
