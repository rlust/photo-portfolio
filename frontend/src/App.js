import './App.css';

import React, { useEffect, useState } from 'react';
import GalleryView from './components/GalleryView';
import AdminPanel from './components/AdminPanel';
import LightboxModal from './components/LightboxModal';
import LargeBatchUpload from './components/LargeBatchUpload';

// Constants
// Old backend that was having issues
// const PROD_API_BASE_URL = 'https://photoportfolio-backend-er4l5fctxq-uc.a.run.app';

// Use direct-simple-api for folder listings (has CORS support but no storage)
const API_BASE_URL = 'https://direct-simple-api-839093975626.us-central1.run.app';

// Use simplified-backend for uploads (has storage but track uploads locally)
const UPLOAD_API_BASE_URL = 'https://simplified-backend-839093975626.us-central1.run.app';

// Force HTTPS for all requests
console.log('Using API services: ', { 
  'Listings API': API_BASE_URL, 
  'Upload API': UPLOAD_API_BASE_URL 
});

// GLOBAL PROTOCOL ENFORCER - Force HTTPS for all communications
// This script will be executed immediately when the app loads
(function() {
  // 1. Force HTTPS for the entire site if needed
  if (window.location.protocol === 'http:' && window.location.hostname !== 'localhost') {
    window.location.href = window.location.href.replace('http:', 'https:');
  }
  
  // 2. Override XMLHttpRequest to force HTTPS
  const originalXMLHttpRequestOpen = XMLHttpRequest.prototype.open;
  XMLHttpRequest.prototype.open = function(method, url, async, user, password) {
    if (typeof url === 'string') {
      // Always ensure HTTPS for backend URLs
      if (url.includes('simplified-backend-839093975626.us-central1.run.app')) {
        url = url.replace('http://', 'https://');
        if (!url.startsWith('https://')) {
          url = 'https://' + url.replace(/^(\/\/)?/, '');
        }
        console.log('XHR using secured URL:', url);
      }
    }
    return originalXMLHttpRequestOpen.call(this, method, url, async, user, password);
  };
  
  // 3. Override fetch to force HTTPS
  const originalFetch = window.fetch;
  window.fetch = function(url, options) {
    if (typeof url === 'string') {
      // Always ensure HTTPS for backend URLs
      if (url.includes('simplified-backend-839093975626.us-central1.run.app')) {
        url = url.replace('http://', 'https://');
        if (!url.startsWith('https://')) {
          url = 'https://' + url.replace(/^(\/\/)?/, '');
        }
        console.log('Fetch using secured URL:', url);
      } else if (url.startsWith('http://')) {
        url = url.replace('http://', 'https://');
        console.log('Converted HTTP to HTTPS:', url);
      }
    }
    return originalFetch.apply(this, [url, options]);
  };
  
  console.log('🔒 Global HTTPS enforcement active');
})();

// API endpoints for different services
const API_ENDPOINT = `${API_BASE_URL}/api`;
// Set batch size to 1 to process one file at a time
const MAX_BATCH_SIZE = 1;
// Direct upload endpoint on our simplified backend
const DIRECT_UPLOAD_URL = `${UPLOAD_API_BASE_URL}/api/batch-upload`;

// API configuration
const SEMANTIC_SEARCH_API = `${API_ENDPOINT}/photos/semantic-search/`;

function App() {
  const [tab, setTab] = useState('gallery');
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState(null);

  // AI-powered file search handler
  const handleSemanticSearch = async (e) => {
    e.preventDefault();
    setSearchLoading(true);
    setSearchError(null);
    setSearchResults(null);
    try {
      const resp = await fetch(`${SEMANTIC_SEARCH_API}?q=${encodeURIComponent(searchQuery)}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      setSearchResults(data);
    } catch (err) {
      setSearchError(err.message);
    } finally {
      setSearchLoading(false);
    }
  };

  // Fetch photos (removed, no longer needed)
  // useEffect(() => {
  //   fetch('https://photoportfolio-backend-er4l5fctxq-uc.a.run.app/api/photos')
  //     .then(res => {
  //       if (!res.ok) throw new Error('Network response was not ok');
  //       return res.json();
  //     })
  //     .then(data => {
  //       setPhotos(data.photos || data || []);
  //     })
  //     .catch(err => {
  //       // Optionally log error, but no UI state to set
  //       console.error('Photo fetch error:', err.message);
  //     });
  // }, []);

  // Upload photo handler
  // (removed unused handlePhotoUpload function to fix CI build error)


  // Folder upload state
  const [folderName, setFolderName] = useState("");
  const [folderImages, setFolderImages] = useState([]);
  const [uploadingGroup, setUploadingGroup] = useState(false);
  const [groupUploadError, setGroupUploadError] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);


  const [folders, setFolders] = useState({});
  const [loadingFolders, setLoadingFolders] = useState(true);
  const [foldersError, setFoldersError] = useState(null);

  // Function to update uploads in local storage
  const saveUploadToLocalStorage = (folder, fileMetadata) => {
    // Get existing uploads from localStorage
    const localStorageKey = 'photoPortfolioUploads';
    let uploads = JSON.parse(localStorage.getItem(localStorageKey) || '{}');
    
    // Initialize folder if it doesn't exist
    if (!uploads[folder]) {
      uploads[folder] = [];
    }
    
    // Add the new upload
    uploads[folder].push(fileMetadata);
    
    // Save back to localStorage
    localStorage.setItem(localStorageKey, JSON.stringify(uploads));
    console.log(`Added upload to ${folder} in localStorage:`, fileMetadata);
    
    // Trigger a folder refresh
    fetchFolders();
  };

  // Clear a specific upload from localStorage
  const clearUploadFromLocalStorage = (folder, fileUrl) => {
    const localStorageKey = 'photoPortfolioUploads';
    let uploads = JSON.parse(localStorage.getItem(localStorageKey) || '{}');
    
    if (uploads[folder]) {
      uploads[folder] = uploads[folder].filter(item => item.url !== fileUrl);
      localStorage.setItem(localStorageKey, JSON.stringify(uploads));
      console.log(`Removed upload from ${folder} in localStorage:`, fileUrl);
    }
  };
  
  // Utility function to extract the base filename from a URL
  const extractBaseFilename = (url) => {
    try {
      // Handle both absolute URLs and relative paths
      let pathname;
      if (url.startsWith('http')) {
        const urlObj = new URL(url);
        pathname = urlObj.pathname;
      } else {
        pathname = url.split('?')[0]; // Remove query string
      }
      
      // Get the last part of the path which should be the filename
      const filename = pathname.split('/').pop();
      return filename || '';
    } catch (error) {
      console.error('Error extracting filename from URL:', url, error);
      return '';
    }
  };
  
  // Fetch folders and their images with aggressive duplicate prevention
  const fetchFolders = () => {
    setLoadingFolders(true);
    setFoldersError(null);
    
    // Get uploads from localStorage
    const localStorageKey = 'photoPortfolioUploads';
    let localUploads = JSON.parse(localStorage.getItem(localStorageKey) || '{}');
    console.log('Local uploads from storage:', localUploads);
    
    // Fetch from the API
    const foldersUrl = `${API_BASE_URL}/api/folders/`;
    console.log('Fetching folders from API:', foldersUrl);
    
    // Use fetch API for simplicity
    fetch(foldersUrl)
      .then(response => {
        if (!response.ok) {
          throw new Error(`Network response status: ${response.status}`);
        }
        return response.json();
      })
      .then(apiFolders => {
        console.log('API folders response:', apiFolders);
        
        // Create a fresh merged folders object
        const mergedFolders = {};
        
        // First add API folders to the merged result - these take precedence
        Object.keys(apiFolders).forEach(folderName => {
          if (!mergedFolders[folderName]) {
            mergedFolders[folderName] = [];
          }
          
          // Add all API images to the folder
          if (Array.isArray(apiFolders[folderName])) {
            mergedFolders[folderName] = [...apiFolders[folderName]];
          }
        });
        
        // Track all unique filenames across all folders to prevent any kind of duplication
        const allUniqueFilenames = new Map(); // filename -> {folder, image}
        
        // Register API filenames first since they have priority
        Object.keys(mergedFolders).forEach(folderName => {
          mergedFolders[folderName].forEach(img => {
            // Get all possible identifiers for this image
            const identifiers = [];
            
            // Get URL-based filename
            if (img.url) {
              const urlFilename = extractBaseFilename(img.url);
              if (urlFilename) identifiers.push(urlFilename);
            }
            
            // Get storage_path-based filename (usually more reliable)
            if (img.storage_path) {
              const storageFilename = img.storage_path.split('/').pop();
              if (storageFilename) identifiers.push(storageFilename);
            }
            
            // Register all unique identifiers
            identifiers.forEach(identifier => {
              allUniqueFilenames.set(identifier, { folder: folderName, image: img });
              console.log(`Registered API image: ${identifier} in folder ${folderName}`);
            });
          });
        });
        
        // Now process local uploads and only add those that don't conflict
        Object.keys(localUploads).forEach(folderName => {
          // Initialize folder if needed
          if (!mergedFolders[folderName]) {
            mergedFolders[folderName] = [];
          }
          
          // Filter local uploads to only include non-duplicates
          localUploads[folderName].forEach(localImg => {
            // Get all possible identifiers for this local image
            const localIdentifiers = [];
            
            // URL-based
            if (localImg.url) {
              const urlFilename = extractBaseFilename(localImg.url);
              if (urlFilename) localIdentifiers.push(urlFilename);
            }
            
            // Storage-path-based
            if (localImg.storage_path) {
              const storageFilename = localImg.storage_path.split('/').pop();
              if (storageFilename) localIdentifiers.push(storageFilename);
            }
            
            // Original filename
            if (localImg.original_filename) {
              localIdentifiers.push(localImg.original_filename);
            }
            
            // Check if this local image is a duplicate of ANY existing image
            const isDuplicate = localIdentifiers.some(identifier => 
              allUniqueFilenames.has(identifier)
            );
            
            if (isDuplicate) {
              console.log(`⚠️ Filtering out duplicate local image: ${localImg.name || localIdentifiers[0]}`);
            } else {
              // Not a duplicate, add to merged folders
              mergedFolders[folderName].push(localImg);
              
              // Register its identifiers to prevent future duplicates
              localIdentifiers.forEach(identifier => {
                allUniqueFilenames.set(identifier, { folder: folderName, image: localImg });
              });
              
              console.log(`✅ Added unique local image: ${localImg.name || localIdentifiers[0]}`);
            }
          });
        });
        
        // Log summary of merged folders
        console.log('Final merged folders:', Object.keys(mergedFolders).reduce((acc, folder) => {
          acc[folder] = mergedFolders[folder].length;
          return acc;
        }, {}));
        
        // Update state with merged data
        setFolders(mergedFolders);
        setLoadingFolders(false);
        console.log('Merged folders data:', mergedFolders);
      })
      .catch(error => {
        console.error('Error fetching folders:', error);
        
        // Fall back to local uploads on API error
        setFolders(localUploads);
        setFoldersError(error.message || 'Failed to fetch folders');
        setLoadingFolders(false);
      });
  };

  // Function to delete an image
  const handleDeleteImage = async (folder, image) => {
    console.log(`Deleting image: ${image.url} from folder: ${folder}`);
    
    if (!window.confirm(`Delete image "${image.name || 'Untitled'}" from folder "${folder}"?`)) {
      return false;
    }
    
    try {
      // Extract the filename from the URL or storage path
      let filename;
      if (image.storage_path) {
        filename = image.storage_path.split('/').pop();
      } else {
        filename = extractBaseFilename(image.url);
      }
      
      console.log(`Deleting file: ${filename} from folder: ${folder}`);
      
      // If the image is in local storage, remove it first
      const localStorageKey = 'photoPortfolioUploads';
      let uploads = JSON.parse(localStorage.getItem(localStorageKey) || '{}');
      
      if (uploads[folder]) {
        const beforeCount = uploads[folder].length;
        uploads[folder] = uploads[folder].filter(img => {
          // Use both URL and storage path for comparison
          let imgFilename;
          if (img.storage_path) {
            imgFilename = img.storage_path.split('/').pop();
          } else {
            imgFilename = extractBaseFilename(img.url);
          }
          return imgFilename !== filename;
        });
        
        // Save back to localStorage
        localStorage.setItem(localStorageKey, JSON.stringify(uploads));
        console.log(`Removed ${beforeCount - uploads[folder].length} image(s) from localStorage`);
      }
      
      // Delete from the backend
      const deleteUrl = `${API_BASE_URL}/api/delete-image/`;
      console.log(`Sending delete request to: ${deleteUrl}`);
      
      const response = await fetch(deleteUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          folder: folder,
          filename: filename
        })
      });
      
      const responseData = await response.text();
      console.log('Delete response:', response.status, responseData);
      
      if (response.ok) {
        console.log(`Successfully deleted image from backend`);
        alert(`Image "${image.name || 'Untitled'}" successfully deleted.`);
      } else {
        console.warn(`Backend deletion failed: ${response.status}`);
        alert(`Warning: Backend deletion may have failed, but the image was removed from the interface.`);
      }
      
      // Update the UI by refetching folders
      fetchFolders();
      
      return true;
    } catch (error) {
      console.error('Error deleting image:', error);
      alert(`Error deleting image: ${error.message}`);
      return false;
    }
  };

  useEffect(() => {
    // ALWAYS clear local storage on load to prevent any duplicates
    // This is more aggressive but will ensure no duplicates persist
    console.log('Clearing local storage to reset duplicates');
    localStorage.removeItem('photoPortfolioUploads');
    localStorage.removeItem('pendingFolders');
    
    // Set a new timestamp key to track this clear
    localStorage.setItem('lastCleared', new Date().toISOString());
    
    fetchFolders();
  }, []);

  // Helper: batch files so each batch is <= 31MB (safety margin for backend limit)
  function batchFiles(files, maxBatchSizeMB = 31) {
    const batches = [];
    let currentBatch = [];
    let currentBatchSize = 0;
    for (const file of files) {
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB > maxBatchSizeMB) {
        throw new Error(`File ${file.name} is too large (${fileSizeMB.toFixed(2)}MB). Max allowed is ${maxBatchSizeMB}MB.`);
      }
      if (currentBatch.length && (currentBatchSize + fileSizeMB > maxBatchSizeMB)) {
        batches.push(currentBatch);
        currentBatch = [];
        currentBatchSize = 0;
      }
      currentBatch.push(file);
      currentBatchSize += fileSizeMB;
    }
    if (currentBatch.length) batches.push(currentBatch);
    return batches;
  }

  // Handle group image upload with batching and progress + detailed logging
  const handleGroupUpload = async (e) => {
    e.preventDefault();
    if (!folderName || folderImages.length === 0) return;
    
    setUploadingGroup(true);
    setGroupUploadError(null);
    setUploadProgress(0);
    
    // Ensure folder name is valid
    const folderToUse = folderName.trim() || 'default';
    console.log(`Starting upload to folder: ${folderToUse} with ${folderImages.length} images`);
    
    // Handle "Storage service not available" by implementing more robust upload
    const DIRECT_UPLOAD_URL = `${API_BASE_URL}/upload/`;
    console.log(`Using direct upload endpoint: ${DIRECT_UPLOAD_URL}`);
    
    const BATCH_SIZE = 1; // Process one image at a time for maximum reliability
    const totalImages = folderImages.length;
    let uploadedCount = 0;

    try {
      // First store the folder and files in localStorage for immediate display
      // This acts as a fallback if the backend has issues
      const tempImages = Array.from(folderImages).map(file => ({
        name: file.name,
        url: URL.createObjectURL(file),
        id: `temp-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
        type: file.type,
        size: file.size,
        uploaded_at: new Date().toISOString()
      }));
      
      // Get existing stored folders or initialize
      const storedFolders = JSON.parse(localStorage.getItem('pendingFolders') || '{}');
      
      // Add the new folder or update existing one
      if (!storedFolders[folderToUse]) {
        storedFolders[folderToUse] = tempImages;
      } else {
        storedFolders[folderToUse] = [...storedFolders[folderToUse], ...tempImages];
      }
      
      // Save back to localStorage
      localStorage.setItem('pendingFolders', JSON.stringify(storedFolders));
      
      // Update state immediately to show the new folder/images
      setFolders(prev => {
        const updated = {...prev};
        if (!updated[folderToUse]) {
          updated[folderToUse] = tempImages;
        } else {
          updated[folderToUse] = [...updated[folderToUse], ...tempImages];
        }
        return updated;
      });
      
      // Upload one image at a time for reliability using the max batch size
      for (let batchIdx = 0; batchIdx < Math.ceil(totalImages / MAX_BATCH_SIZE); batchIdx++) {
        const batch = folderImages.slice(batchIdx * MAX_BATCH_SIZE, (batchIdx + 1) * MAX_BATCH_SIZE);
        console.log(`Processing batch ${batchIdx + 1} with ${batch.length} images`);
        
        const handleBatchUpload = (folderName, batch) => {
          if (batch && batch.length > 0) {
            console.log(`Handling batch upload of ${batch.length} files to ${folderName}`);
            setUploadingGroup(true);
            setUploadProgress(0);
            
            // Process files one by one instead of in a batch to avoid server issues
            const processFilesSequentially = async () => {
              const results = [];
              const failedFiles = [];
              const successfulUploads = [];
              
              // Process each file individually
              for (let i = 0; i < batch.length; i++) {
                const file = batch[i];
                try {
                  // Update progress based on files processed
                  setUploadProgress(Math.round((i / batch.length) * 100));
                  console.log(`Processing file ${i+1}/${batch.length}: ${file.name}`);
                  
                  // Use our simplified backend endpoint for uploads
                  console.log(`Uploading file ${i+1}/${batch.length} to simplified backend: ${file.name}`);
                  
                  // Create a form data object to send the file
                  const formData = new FormData();
                  formData.append('folder', folderName);
                  formData.append('images', file);
                  
                  // Send the file to our simplified backend using the API_ENDPOINT variable
                  const uploadResponse = await fetch(`${API_ENDPOINT}/batch-upload`, {
                    method: 'POST',
                    body: formData,
                  });
                  
                  if (!uploadResponse.ok) {
                    throw new Error(`Upload failed with status: ${uploadResponse.status}`);
                  }
                  
                  const uploadResult = await uploadResponse.json();
                  console.log('Upload result:', uploadResult);
                  
                  if (uploadResult.failed_files && uploadResult.failed_files.length > 0) {
                    throw new Error(`Upload failed: ${uploadResult.failed_files[0].error}`);
                  }
                  
                  // Add the uploaded file info to our list using the actual response from the server
                  if (uploadResult.uploaded_files && uploadResult.uploaded_files.length > 0) {
                    const fileInfo = uploadResult.uploaded_files[0];
                    const responseObj = {
                      success: true,
                      folder: {
                        id: folderName.replace(/[^a-zA-Z0-9]/g, '_'),
                        name: folderName,
                        description: `Folder for ${folderName}`,
                        photos: [{
                          id: fileInfo.storage_path,
                          url: fileInfo.url,
                          title: fileInfo.original_filename,
                          filename: fileInfo.original_filename,
                          mimetype: fileInfo.mimetype,
                          size: fileInfo.size
                        }]
                      }
                    };
                    
                    // Add to successful uploads
                    successfulUploads.push(responseObj);
                    
                    // Log for debugging
                    console.log(`Successfully uploaded ${fileInfo.original_filename} to ${fileInfo.url}`);
                  }
                  
                  // Add to results (already done via successfulUploads)
                  
                  // Upload was successful and response is already processed
                  console.log(`File ${i+1} processed successfully using simplified backend`);
                  // Response is already processed above
                  
                } catch (error) {
                  console.error(`Error uploading file ${file.name}:`, error);
                  failedFiles.push({ name: file.name, error: error.message });
                }
              }
              
              // All files processed - handle results
              if (results.length > 0) {
                // Get the folder info from the last successful upload
                const lastResult = results[results.length - 1];
                
                if (lastResult && lastResult.success && lastResult.folder) {
                  const newFolder = lastResult.folder;
                  
                  // Check if this folder already exists in state
                  const folderExists = folders.some(f => f.id === newFolder.id);
                  
                  // Gather all photos from all successful uploads
                  const allUploadedPhotos = results
                    .filter(r => r.success && r.folder && r.folder.photos)
                    .flatMap(r => r.folder.photos);
                  
                  if (folderExists) {
                    // Update existing folder with new photos
                    setFolders(prevFolders => {
                      return prevFolders.map(folder => {
                        if (folder.id === newFolder.id) {
                          return {
                            ...folder,
                            photos: [...folder.photos, ...allUploadedPhotos]
                          };
                        }
                        return folder;
                      });
                    });
                  } else {
                    // Add the new folder to state with all photos
                    const completeNewFolder = {
                      ...newFolder,
                      photos: allUploadedPhotos
                    };
                    
                    setFolders(prevFolders => [...prevFolders, completeNewFolder]);
                    
                    // Also store in localStorage for persistence
                    try {
                      // Get current folders from localStorage
                      const storedFolders = JSON.parse(localStorage.getItem('folders') || '[]');
                      
                      // Check if the folder exists
                      const existingFolderIndex = storedFolders.findIndex(f => f.id === newFolder.id);
                      
                      if (existingFolderIndex >= 0) {
                        // Update existing folder
                        storedFolders[existingFolderIndex] = {
                          ...storedFolders[existingFolderIndex],
                          photos: [...storedFolders[existingFolderIndex].photos, ...allUploadedPhotos]
                        };
                      } else {
                        // Add new folder
                        storedFolders.push(completeNewFolder);
                      }
                      
                      // Save back to localStorage
                      localStorage.setItem('folders', JSON.stringify(storedFolders));
                    } catch (err) {
                      console.error('Failed to update localStorage:', err);
                    }
                  }
                }
                
                // Show success message, but mention failed files if any
                if (failedFiles.length > 0) {
                  setGroupUploadError(`Successfully uploaded ${results.length} files, but ${failedFiles.length} files failed: ${failedFiles.map(f => f.name).join(', ')}`);
                } else {
                  setGroupUploadError(null);
                }
              } else {
                // All files failed
                setGroupUploadError(`All ${batch.length} files failed to upload. Please try again.`);
              }
              
              // Reset upload state
              setUploadingGroup(false);
              setUploadProgress(100); // Set to 100% to indicate completion
              setTimeout(() => setUploadProgress(0), 1000); // Reset after a second
            };
            
            // Start processing
            processFilesSequentially().catch(error => {
              console.error('Error in sequential processing:', error);
              setUploadingGroup(false);
              setUploadProgress(0);
              setGroupUploadError(`Upload process error: ${error.message}`);
            });
          }
        };
        
        handleBatchUpload(folderToUse, batch);
        
        // Only increment after batch is done
        uploadedCount += batch.length;
        console.log(`Batch ${batchIdx + 1} completed successfully, total progress: ${uploadedCount}/${totalImages}`);
      }
      
      console.log('All batches uploaded successfully!');
      setFolderName("");
      setFolderImages([]);
      setUploadingGroup(false);
      setUploadProgress(0);
      fetchFolders();
    } catch (err) {
      console.error('Upload error:', err);
      setGroupUploadError(err.message);
      setUploadingGroup(false);
      setUploadProgress(0);
    }
  };

  const uploadPhotos = async (event) => {
    event.preventDefault();
    setUploadingGroup(true);
    setGroupUploadError(null);

    const formData = new FormData();
    formData.append('folder', folderName);
    
    console.log('Starting upload to folder:', folderName);
    console.log('Files to upload:', folderImages.length);
    
    // Add each selected file to the form data
    for (const file of folderImages) {
      formData.append('images', file);
      console.log('Adding file to upload:', file.name, file.type, file.size);
    }

    try {
      console.log('Sending upload request to:', `${API_ENDPOINT}/batch-upload`);
      
      const response = await fetch(`${API_ENDPOINT}/batch-upload`, {
        method: 'POST',
        body: formData,
        headers: {
          // Don't set Content-Type with FormData - browser will set it with boundary
          'Accept': 'application/json',
        },
      });

      console.log('Upload response status:', response.status, response.statusText);
      
      // Try to parse response even if it's not 2xx to get error details
      const responseText = await response.text();
      console.log('Response text:', responseText);
      
      let data;
      try {
        data = JSON.parse(responseText);
        console.log('Parsed response data:', data);
      } catch (parseError) {
        console.error('Failed to parse response:', parseError);
        data = { message: responseText };
      }

      if (!response.ok) {
        throw new Error(`Upload failed: ${data.detail || data.message || response.statusText}`);
      }

      console.log('Upload successful:', data);
      
      // Refresh photo list after successful upload
      fetchFolders();
      
      // Clear selected files
      setFolderImages([]);
      setUploadingGroup(false);
      
      // Auto-hide success message after 3 seconds
      setTimeout(() => setUploadingGroup(false), 3000);
      
    } catch (error) {
      console.error('Upload error:', error);
      setGroupUploadError(error.message);
    } finally {
      setUploadingGroup(false);
    }
  };

  // Delete image - using our direct-simple-api endpoint
  // This is the updated version that works with our new API

  // Delete folder
  const handleDeleteFolder = async (folder) => {
    if (!window.confirm(`Delete folder "${folder}" and ALL images in it? This cannot be undone.`)) return;
    try {
      await fetch(
        `${API_ENDPOINT}/folder/${encodeURIComponent(folder)}`,
        { method: 'DELETE' }
      );
      fetchFolders();
    } catch (err) {
      alert('Error deleting folder: ' + err.message);
    }
  };

  // Lightbox and carousel state
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [carouselIndex, setCarouselIndex] = useState(0);
  const allImages = Object.entries(folders).flatMap(([folder,images]) => images.map(img => ({...img, folder})));

  // Auto-play: advance every 4s if not open
  useEffect(() => {
    if (!allImages.length || lightboxOpen) return;
    const interval = setInterval(() => {
      setCarouselIndex(idx => (idx + 1) % allImages.length);
    }, 4000);
    return () => clearInterval(interval);
  }, [allImages.length, lightboxOpen]);

  // Keyboard: Escape closes, arrows navigate
  useEffect(() => {
    if (!lightboxOpen) return;
    const onKey = e => {
      if (e.key === 'Escape') setLightboxOpen(false);
      if (e.key === 'ArrowLeft') setCarouselIndex(idx => (idx-1+allImages.length)%allImages.length);
      if (e.key === 'ArrowRight') setCarouselIndex(idx => (idx+1)%allImages.length);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [lightboxOpen, allImages.length]);

  return (
    <div className="App">
      <header style={{padding: '2.5rem 0 1.2rem 0', background: '#fff', color: '#222', boxShadow: '0 2px 8px #0001', marginBottom: 0}}>
        <h1 style={{fontSize: '2.5rem', marginBottom: '1rem', letterSpacing: '2px', fontWeight: 700, fontFamily:'serif'}}>Randy Lust Photography</h1>
        <div style={{display:'flex',justifyContent:'center',marginBottom:'1rem',gap:'0.5rem'}}>
          <button onClick={()=>setTab('gallery')} style={{padding:'0.5rem 1.2rem',borderRadius:'4px',border:'none',background:tab==='gallery'?'#222':'#eee',color:tab==='gallery'?'#fff':'#444',fontWeight:'bold',cursor:'pointer',fontSize:'1.1rem'}}>Gallery</button>
          <button onClick={()=>setTab('admin')} style={{padding:'0.5rem 1.2rem',borderRadius:'4px',border:'none',background:tab==='admin'?'#222':'#eee',color:tab==='admin'?'#fff':'#444',fontWeight:'bold',cursor:'pointer',fontSize:'1.1rem'}}>Admin</button>
          <button onClick={()=>setTab('largebatch')} style={{padding:'0.5rem 1.2rem',borderRadius:'4px',border:'none',background:tab==='largebatch'?'#222':'#eee',color:tab==='largebatch'?'#fff':'#444',fontWeight:'bold',cursor:'pointer',fontSize:'1.1rem'}}>Large Batch Upload</button>
          <button onClick={()=>setTab('search')} style={{padding:'0.5rem 1.2rem',borderRadius:'4px',border:'none',background:tab==='search'?'#222':'#eee',color:tab==='search'?'#fff':'#444',fontWeight:'bold',cursor:'pointer',fontSize:'1.1rem'}}>Search</button>
        </div>
      </header>

      {/* Search Tab Content */}
      {tab === 'search' && (
        <section style={{maxWidth:700,margin:'2rem auto',background:'#fff',borderRadius:8,boxShadow:'0 2px 8px #0001',padding:'2rem'}}>
          <h2 style={{marginBottom:24}}>AI-Powered File Search</h2>
          <form onSubmit={handleSemanticSearch} style={{display:'flex',gap:8,marginBottom:24}}>
            <input
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Describe what you're looking for..."
              style={{flex:1,padding:'0.7rem',fontSize:'1.1rem',borderRadius:6,border:'1px solid #ddd'}}
            />
            <button type="submit" style={{padding:'0.7rem 1.2rem',fontSize:'1.1rem',borderRadius:6,background:'#2a5298',color:'#fff',border:'none',fontWeight:'bold'}}>
              Search
            </button>
          </form>
          {searchLoading && <div style={{color:'#888'}}>Searching...</div>}
          {searchError && <div style={{color:'#c00',marginTop:12}}>Error: {searchError}</div>}
          {searchResults && (
            <div style={{marginTop:24}}>
              {searchResults.length === 0 ? (
                <div style={{color:'#888'}}>No matching files found.</div>
              ) : (
                <ul style={{listStyle:'none',padding:0}}>
                  {searchResults.map((item, idx) => (
                    <li key={item.url || idx} style={{marginBottom:18,padding:12,background:'#f7f7fa',borderRadius:7,boxShadow:'0 1px 4px #0001'}}>
                      <div style={{fontWeight:'bold',fontSize:'1.08rem'}}>{item.name}</div>
                      <div style={{color:'#888',fontSize:'0.96em'}}>Folder: {item.folder}</div>
                      <div style={{color:'#888',fontSize:'0.95em'}}>Type: {item.mimetype}</div>
                      <div style={{color:'#888',fontSize:'0.95em'}}>Uploaded: {item.uploaded_at}</div>
                      {item.url && <a href={item.url} target="_blank" rel="noopener noreferrer" style={{color:'#2a5298',fontWeight:'bold'}}>View File</a>}
                      {typeof item.score === 'number' && <div style={{color:'#2a5298',fontSize:'0.93em'}}>Relevance: {(item.score*100).toFixed(1)}%</div>}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
          {/* Usage Example for Testing */}
          <div style={{marginTop:32,padding:'1rem',background:'#f0f6ff',borderRadius:6}}>
            <div style={{fontWeight:'bold',marginBottom:8}}>Usage Example:</div>
            <div style={{fontSize:'0.98em',color:'#222'}}>Try searching for things like:</div>
            <ul style={{color:'#333',margin:'8px 0 0 16px',fontSize:'0.97em'}}>
              <li>"sunset at the beach"</li>
              <li>"PDF invoices from March"</li>
              <li>"family vacation 2023"</li>
              <li>"cat photos"</li>
            </ul>
          </div>
        </section>
      )}
      {/* Full-size scrollable image carousel with lightbox and autoplay */}
      {allImages.length > 0 && (
        <section style={{width:'100%',overflowX:'auto',padding:'1.5rem 0',background:'#f7f7fa',marginBottom:'2rem',boxShadow:'0 2px 8px #0001'}}>
          <div style={{display:'flex',gap:'2rem',padding:'0 2rem',alignItems:'center',minHeight:350}}>
            {allImages.map((img,idx) => (
              <div key={img.url+idx} style={{minWidth:380,maxWidth:600,background:'#fff',borderRadius:'12px',boxShadow:'0 4px 16px #0002',padding:'1.5rem',display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',cursor:'pointer',outline:carouselIndex===idx?'2px solid #2a5298':'none'}} onClick={()=>{setCarouselIndex(idx);setLightboxOpen(true);}}>
                <img src={img.url} alt={img.name} style={{width:'100%',maxWidth:500,maxHeight:300,objectFit:'contain',borderRadius:'8px',border:'1px solid #eee',background:'#fafbfc'}} onError={e => {
                  e.target.onerror = null;
                  // Use a simple data URL instead of an external service
                  e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iNTAwIiBoZWlnaHQ9IjMwMCIgZmlsbD0iI2YwZjBmMCIgLz48dGV4dCB4PSIxNTAiIHk9IjE1MCIgZm9udC1mYW1pbHk9IkFyaWFsIiBmb250LXNpemU9IjI0IiBmaWxsPSIjOTk5OTk5Ij5JbWFnZSBub3QgZm91bmQ8L3RleHQ+PC9zdmc+';                  
                }}/>
                <div style={{marginTop:'0.75rem',fontWeight:'bold',fontSize:'1.05rem'}}>{img.name}</div>
                <div style={{color:'#888',fontSize:'0.93em'}}>{img.folder}</div>
              </div>
            ))}
          </div>
          <LightboxModal
            open={lightboxOpen}
            image={allImages[carouselIndex]}
            onClose={()=>setLightboxOpen(false)}
            onPrev={()=>setCarouselIndex(idx => (idx-1+allImages.length)%allImages.length)}
            onNext={()=>setCarouselIndex(idx => (idx+1)%allImages.length)}
          />
        </section>
      )}

      {/* Main content: tabbed mode */}
      {tab === 'gallery' && <GalleryView folders={folders} onDeleteImage={handleDeleteImage} />}
      {tab === 'admin' && (
        <AdminPanel
          folderName={folderName}
          setFolderName={setFolderName}
          folderImages={folderImages}
          setFolderImages={setFolderImages}
          uploadingGroup={uploadingGroup}
          groupUploadError={groupUploadError}
          handleGroupUpload={handleGroupUpload}
          uploadProgress={uploadProgress}
          folders={folders}
          loadingFolders={loadingFolders}
          foldersError={foldersError}
          handleDeleteFolder={handleDeleteFolder}
          handleDeleteImage={handleDeleteImage}
        />
      )}
      {tab === 'largebatch' && (
        <LargeBatchUpload 
          onUploaded={fetchFolders} 
          onUploadSuccess={saveUploadToLocalStorage} 
        />
      )}
    </div>
  );
}

export default App;
