import React, { useEffect } from 'react';

// This component loads sample images if none are found in the database
const SampleImagesLoader = ({ onImagesLoaded }) => {
  useEffect(() => {
    const loadSampleImages = async () => {
      console.log('Loading sample images as fallback');
      
      // Sample image data - these are public domain/CC0 image URLs
      const sampleImages = {
        'Landscapes': [
          {
            name: 'mountain_sunset.jpg',
            url: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=800&auto=format',
            description: 'Beautiful mountain sunset landscape',
            size: 245000,
            mimetype: 'image/jpeg',
            uploaded_at: '2025-06-01'
          },
          {
            name: 'ocean_waves.jpg',
            url: 'https://images.unsplash.com/photo-1518837695005-2083093ee35b?w=800&auto=format',
            description: 'Ocean waves at sunset',
            size: 320000,
            mimetype: 'image/jpeg',
            uploaded_at: '2025-06-01'
          }
        ],
        'Nature': [
          {
            name: 'forest_path.jpg',
            url: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&auto=format',
            description: 'Sunlight through forest trees',
            size: 280000,
            mimetype: 'image/jpeg',
            uploaded_at: '2025-06-01'
          },
          {
            name: 'waterfall.jpg',
            url: 'https://images.unsplash.com/photo-1546182990-dffeafbe841d?w=800&auto=format',
            description: 'Majestic waterfall in the forest',
            size: 310000,
            mimetype: 'image/jpeg',
            uploaded_at: '2025-06-01'
          }
        ],
        'Portraits': [
          {
            name: 'portrait1.jpg',
            url: 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800&auto=format',
            description: 'Portrait of a person with natural light',
            size: 195000,
            mimetype: 'image/jpeg',
            uploaded_at: '2025-06-01'
          }
        ]
      };
      
      // Store sample images in localStorage
      localStorage.setItem('photoPortfolioUploads', JSON.stringify(sampleImages));
      localStorage.setItem('photoPortfolioImagesCache', JSON.stringify(sampleImages));
      
      // Notify parent component
      if (onImagesLoaded) {
        onImagesLoaded(sampleImages);
      }
    };
    
    // Check if images already exist in localStorage
    const existingImages = localStorage.getItem('photoPortfolioUploads');
    const hasImages = existingImages && Object.keys(JSON.parse(existingImages)).length > 0;
    
    if (!hasImages) {
      // Only load sample images if none exist
      loadSampleImages();
    }
  }, [onImagesLoaded]);
  
  // This component doesn't render anything visible
  return null;
};

export default SampleImagesLoader;
