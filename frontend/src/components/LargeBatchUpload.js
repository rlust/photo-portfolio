import React, { useState } from "react";

// Define backend URLs as constants at module level
const UPLOAD_BACKEND_URL = 'https://simplified-backend-839093975626.us-central1.run.app';
const UPLOAD_ENDPOINT = `${UPLOAD_BACKEND_URL}/api/batch-upload`;

// Use the simplified-backend directly for image loading
const IMAGE_SERVING_URL = 'https://simplified-backend-839093975626.us-central1.run.app';

export default function LargeBatchUpload({ onUploaded, onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const [progress, setProgress] = useState({});
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [folder, setFolder] = useState("");

  // Log that this component is being rendered
  console.log('LargeBatchUpload component rendered');
  
  // Function to save upload metadata to localStorage with robust duplicate prevention
  const saveToLocalStorage = (folder, fileMetadata) => {
    // Get existing uploads
    const localStorageKey = 'photoPortfolioUploads';
    let uploads = JSON.parse(localStorage.getItem(localStorageKey) || '{}');
    
    // Initialize folder if needed
    if (!uploads[folder]) {
      uploads[folder] = [];
    }
    
    // Extract identifying information for duplicate detection
    let baseFilename = '';
    let originalFilename = '';
    
    if (fileMetadata.storage_path) {
      baseFilename = fileMetadata.storage_path.split('/').pop();
    }
    
    if (fileMetadata.original_filename) {
      originalFilename = fileMetadata.original_filename;
    }
    
    if (!baseFilename && !originalFilename) {
      console.error('No identifiable information for uploaded file, cannot save properly');
      return; // Don't add files without any identifying information
    }
    
    // Use a multi-factor approach to check for duplicates
    const isDuplicate = uploads[folder].some(existingFile => {
      // Check storage path match
      if (baseFilename && existingFile.storage_path) {
        const existingFilename = existingFile.storage_path.split('/').pop();
        if (existingFilename === baseFilename) {
          console.log(`Found duplicate by storage_path: ${existingFilename}`);
          return true;
        }
      }
      
      // Check original filename match
      if (originalFilename && existingFile.original_filename) {
        if (existingFile.original_filename === originalFilename) {
          console.log(`Found duplicate by original_filename: ${originalFilename}`);
          return true;
        }
      }
      
      // Check URL match (excluding query parameters)
      if (fileMetadata.url && existingFile.url) {
        // Extract base URL without query parameters
        const getBaseUrl = (url) => url.split('?')[0];
        const baseNewUrl = getBaseUrl(fileMetadata.url);
        const baseExistingUrl = getBaseUrl(existingFile.url);
        
        if (baseNewUrl === baseExistingUrl) {
          console.log(`Found duplicate by URL: ${baseNewUrl}`);
          return true;
        }
      }
      
      return false;
    });
    
    if (isDuplicate) {
      console.log(`⚠️ Skipping duplicate save for ${fileMetadata.original_filename || baseFilename} in folder ${folder}`);
      return; // Don't add duplicates
    }
    
    // Add the upload metadata with timestamp
    fileMetadata.added_at = new Date().toISOString();
    uploads[folder].push(fileMetadata);
    
    // Save back to localStorage
    localStorage.setItem(localStorageKey, JSON.stringify(uploads));
    console.log(`✅ Saved ${fileMetadata.original_filename || baseFilename} to localStorage in folder ${folder}`);
    
    // Notify parent component if callback provided
    if (onUploadSuccess) {
      onUploadSuccess(folder, fileMetadata);
    }
  };

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
    setProgress({});
    setError(null);
  };

  const handleFolderChange = (e) => {
    setFolder(e.target.value);
  };

  const directUpload = async (file, folder) => {
    console.log(`DIRECT UPLOAD: Starting upload for ${file.name} to folder ${folder}`);
    
    // Using the module-level constants for backend URLs
    console.log(`DIRECT UPLOAD: Using endpoint ${UPLOAD_ENDPOINT}`);
    
    // Create a FormData object for this specific file
    const formData = new FormData();
    formData.append('folder', folder);
    formData.append('images', file);
    
    try {
      // Upload directly to our simplified backend
      const response = await fetch(UPLOAD_ENDPOINT, {
        method: 'POST',
        body: formData,
      });
      
      console.log(`DIRECT UPLOAD: Response status for ${file.name}: ${response.status}`);
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`DIRECT UPLOAD: Failed upload for ${file.name}: ${errorText}`);
        throw new Error(`Upload failed: ${errorText}`);
      }
      
      const result = await response.json();
      console.log(`DIRECT UPLOAD: Success result for ${file.name}:`, result);
      
      // Save the upload metadata to localStorage for display in gallery
      if (result.uploaded_files && result.uploaded_files.length > 0) {
        const uploadedFile = result.uploaded_files[0];
        
        // Log the URL for debugging
        console.log('UPLOAD URL SAVED ORIGINAL:', uploadedFile.url);
        console.log('STORAGE PATH:', uploadedFile.storage_path);
        
        // Always explicitly construct the URL from the storage path
        // regardless of what the backend returns
        if (uploadedFile.storage_path) {
          const filename = uploadedFile.storage_path.split('/').pop();
          
          // Use our image proxy URL from the direct-simple-api service
          // This service will proxy requests to the simplified-backend
          uploadedFile.url = `${IMAGE_SERVING_URL}/uploads/${filename}`;
          console.log('CONSTRUCTED PROXIED IMAGE URL:', uploadedFile.url);
          
          // Also add a timestamp parameter to prevent caching
          uploadedFile.url = `${uploadedFile.url}?t=${new Date().getTime()}`;
          console.log('FINAL IMAGE URL WITH CACHE BUSTING:', uploadedFile.url);
        }
        
        // Add proper image name from the original filename
        if (uploadedFile.original_filename) {
          // Use the original filename without the extension as the image name
          const nameParts = uploadedFile.original_filename.split('.');
          if (nameParts.length > 1) {
            nameParts.pop(); // Remove extension
          }
          const cleanName = nameParts.join('.').replace(/_/g, ' ');
          uploadedFile.name = cleanName || 'Unnamed Image';
          
          // Add status field to avoid showing 'Annotating...'
          uploadedFile.status = 'Uploaded';
          
          console.log('Added metadata to image:', { 
            name: uploadedFile.name, 
            status: uploadedFile.status 
          });
        }
        
        saveToLocalStorage(folder, uploadedFile);
      }
      
      return result;
    } catch (err) {
      console.error(`DIRECT UPLOAD: Error for ${file.name}:`, err);
      throw err;
    }
  };

  const handleUpload = async () => {
    console.log(`BATCH UPLOAD: Starting batch upload of ${files.length} files to folder ${folder}`);
    
    setUploading(true);
    setError(null);
    let newProgress = {};
    
    // Process each file one by one
    for (const file of files) {
      try {
        // Update progress to show we're starting
        newProgress[file.name] = 0;
        setProgress({ ...newProgress });
        
        // Upload the file directly
        await directUpload(file, folder);
        
        // Update progress to show completion
        newProgress[file.name] = 100;
        setProgress({ ...newProgress });
        
        console.log(`BATCH UPLOAD: Successfully processed ${file.name}`);
      } catch (err) {
        console.error(`BATCH UPLOAD: Error processing ${file.name}:`, err);
        newProgress[file.name] = -1;
        setProgress({ ...newProgress });
        setError(`Failed to upload ${file.name}: ${err.message}`);
      }
    }
    
    console.log('BATCH UPLOAD: Completed all uploads');
    setUploading(false);
    if (onUploaded) onUploaded();
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>Large Batch Upload (Direct to Cloud)</h2>
      <label>
        Folder name:
        <input
          type="text"
          value={folder}
          onChange={handleFolderChange}
          disabled={uploading}
          style={{ marginLeft: 8 }}
        />
      </label>
      <br />
      <input
        type="file"
        multiple
        onChange={handleFileChange}
        disabled={uploading}
        style={{ margin: "10px 0" }}
      />
      <button
        onClick={handleUpload}
        disabled={uploading || !folder || !files.length}
        style={{
          display: "block",
          margin: "10px 0",
          padding: "8px 16px",
          backgroundColor: "#007bff",
          color: "white",
          border: "none",
          borderRadius: 4,
          cursor: uploading ? "not-allowed" : "pointer",
        }}
      >
        {uploading ? "Uploading..." : "Upload All"}
      </button>

      {error && <div style={{ color: "red", marginTop: 8 }}>{error}</div>}

      {files.length > 0 && (
        <div style={{ marginTop: 16 }}>
          {files.map((file) => (
            <div key={file.name} style={{ marginBottom: 8 }}>
              <div style={{ display: "flex", alignItems: "center" }}>
                <span>{file.name}</span>
                <div
                  style={{
                    marginLeft: 8,
                    width: 100,
                    height: 10,
                    backgroundColor: "#eee",
                    borderRadius: 5,
                  }}
                >
                  {progress[file.name] > 0 && (
                    <div
                      style={{
                        width: `${progress[file.name]}%`,
                        height: "100%",
                        backgroundColor:
                          progress[file.name] === -1 ? "red" : "#4caf50",
                        borderRadius: 5,
                      }}
                    />
                  )}
                </div>
                {progress[file.name] === -1 && (
                  <span style={{ color: "red", marginLeft: 8 }}>Failed</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
