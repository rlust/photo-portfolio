import React, { useState } from 'react';

export default function AdminPanel({
  folderName, setFolderName, folderImages, setFolderImages, uploadingGroup, groupUploadError, handleGroupUpload,
  uploadProgress,
  folders, loadingFolders, foldersError, handleDeleteFolder, handleDeleteImage
}) {
  const [selectedFolder, setSelectedFolder] = useState('');
  const [showFolderContent, setShowFolderContent] = useState(false);
  // Handle folder selection
  const handleFolderSelect = (folder) => {
    if (selectedFolder === folder && showFolderContent) {
      // If clicking the same folder again, toggle the view
      setShowFolderContent(false);
      setSelectedFolder('');
    } else {
      setSelectedFolder(folder);
      setShowFolderContent(true);
    }
  };

  // Function to clear selection
  const clearSelection = () => {
    setSelectedFolder('');
    setShowFolderContent(false);
  };

  return (
    <section style={{margin:'2rem auto',maxWidth:900,background:'#fff',borderRadius:'8px',boxShadow:'0 2px 8px #0001',padding:'1.5rem'}}>
      <h2>Admin Panel</h2>
      <form onSubmit={handleGroupUpload} style={{marginBottom:'2rem',background:'#f3f6fa',padding:'1rem',borderRadius:'8px',maxWidth:'500px'}}>
        <div style={{marginBottom:'0.5rem'}}>
          <input
            id="group-upload-folder"
            name="folder"
            type="text"
            value={folderName}
            onChange={e => setFolderName(e.target.value)}
            placeholder="Folder Name"
            required
          />
        </div>
        <div style={{marginBottom:'0.5rem'}}>
          <input
            id="group-upload-images"
            name="images"
            type="file"
            multiple
            onChange={e => setFolderImages([...e.target.files])}
            accept="image/*"
          />
        </div>
        <button type="submit" disabled={uploadingGroup} style={{padding:'0.5rem 1.5rem',background:'#2a5298',color:'#fff',border:'none',borderRadius:'4px',fontWeight:'bold'}}>
          {uploadingGroup ? 'Uploading...' : 'Upload Images'}
        </button>
        {uploadingGroup && (
          <div style={{marginTop:'0.5rem'}}>
            <div style={{height:'8px',background:'#eee',borderRadius:'4px',overflow:'hidden',marginBottom:'0.3rem'}}>
              <div style={{width:`${uploadProgress}%`,height:'100%',background:'#2a5298',transition:'width 0.2s'}}></div>
            </div>
            <span style={{fontSize:'0.97em',color:'#2a5298',fontWeight:'bold'}}>{uploadProgress}%</span>
          </div>
        )}
        {groupUploadError && <div style={{color:'red',marginTop:'0.5rem'}}>{groupUploadError}</div>}
      </form>
      <h3>Manage Folders & Images</h3>
      {loadingFolders && <div>Loading folders...</div>}
      {foldersError && <div style={{color:'red'}}>{foldersError}</div>}
      {!loadingFolders && !foldersError && (
        <div>
          {Object.keys(folders).length === 0 && <div>No folders found.</div>}
          
          {/* Folder Selection Section */}
          {!showFolderContent && (
            <div>
              <h4>Select a folder to manage</h4>
              <div style={{display:'flex', flexWrap:'wrap', gap:'1rem', marginBottom:'2rem'}}>
                {Object.entries(folders).map(([folder, images]) => (
                  <div 
                    key={folder} 
                    onClick={() => handleFolderSelect(folder)}
                    style={{
                      border:'1px solid #ddd',
                      borderRadius:'8px',
                      padding:'1rem',
                      minWidth:'150px',
                      background:'#fafbfc',
                      cursor:'pointer',
                      transition:'all 0.2s',
                      boxShadow:'0 2px 4px rgba(0,0,0,0.05)',
                      ':hover': { boxShadow:'0 4px 8px rgba(0,0,0,0.1)' }
                    }}
                  >
                    <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
                      <span style={{fontWeight:'bold', fontSize:'1.1rem'}}>{folder}</span>
                      <span style={{background:'#2a5298', color:'white', borderRadius:'4px', padding:'0.15rem 0.5rem', fontSize:'0.8rem'}}>
                        {images.length} image{images.length !== 1 ? 's' : ''}
                      </span>
                    </div>
                    <div style={{marginTop:'0.7rem', display:'flex', gap:'0.5rem'}}>
                      {images.slice(0, 3).map((img, idx) => (
                        <div key={idx} style={{width:'40px', height:'40px', overflow:'hidden', borderRadius:'4px'}}>
                          <img 
                            src={img.url} 
                            alt="" 
                            style={{width:'100%', height:'100%', objectFit:'cover'}}
                            onError={(e) => {
                              e.target.src = `data:image/svg+xml;base64,${btoa('<svg width="40" height="40" xmlns="http://www.w3.org/2000/svg"><rect width="40" height="40" fill="#f5f5f5"/></svg>')}`;
                            }}
                          />
                        </div>
                      ))}
                      {images.length > 3 && (
                        <div style={{width:'40px', height:'40px', background:'#eee', borderRadius:'4px', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.8rem', color:'#777'}}>+{images.length - 3}</div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Selected Folder Content */}
          {showFolderContent && selectedFolder && (
            <div style={{background:'#f9f9f9', padding:'1.5rem', borderRadius:'8px', marginBottom:'2rem'}}>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'1rem'}}>
                <div>
                  <button 
                    onClick={clearSelection}
                    style={{background:'#eee', border:'none', borderRadius:'4px', padding:'0.3rem 0.7rem', marginRight:'1rem', cursor:'pointer'}}
                  >
                    &larr; Back to Folders
                  </button>
                  <span style={{fontWeight:'bold', fontSize:'1.2rem'}}>Folder: {selectedFolder}</span>
                </div>
                <button 
                  onClick={() => {
                    if (window.confirm(`Are you sure you want to delete the entire folder "${selectedFolder}" and all its contents? This cannot be undone.`)) {
                      handleDeleteFolder(selectedFolder);
                      clearSelection();
                    }
                  }}
                  style={{background:'#f33', color:'#fff', border:'none', borderRadius:'4px', padding:'0.4rem 0.8rem', fontWeight:'bold', cursor:'pointer'}}
                >
                  Delete Entire Folder
                </button>
              </div>
              
              <div style={{marginTop:'1rem'}}>
                <h4>Images in folder ({folders[selectedFolder]?.length || 0})</h4>
                <div style={{display:'flex', flexWrap:'wrap', gap:'1rem'}}>
                  {folders[selectedFolder]?.map((img, idx) => (
                    <div key={img.name+idx} style={{position:'relative', display:'inline-block', width:'120px'}}>
                      <img
                        src={img.url}
                        alt={img.name}
                        title={img.name}
                        onError={(e) => {
                          // Special handling for TIF files which browsers can't display natively
                          const isTiffFile = img.name && (img.name.toLowerCase().endsWith('.tif') || img.name.toLowerCase().endsWith('.tiff'));
                          
                          if (isTiffFile) {
                            const imageNameShort = img.name.length > 20 ? img.name.substring(0, 17) + '...' : img.name;
                            e.target.src = `data:image/svg+xml;base64,${btoa(`<svg width="120" height="120" xmlns="http://www.w3.org/2000/svg"><rect width="120" height="120" fill="#f5f5f5"/><text x="60" y="55" text-anchor="middle" fill="#aaa" font-family="sans-serif" font-size="10px">${imageNameShort}</text><text x="60" y="75" text-anchor="middle" fill="#aaa" font-family="sans-serif" font-size="8px">TIFF FORMAT</text></svg>`)}`;
                            return;
                          }
                          
                          // Try direct GCS URL as a last resort
                          if (img.storage_path && e.target.src !== `https://storage.googleapis.com/photoportfolio-uploads/${img.storage_path}`) {
                            const directGcsUrl = `https://storage.googleapis.com/photoportfolio-uploads/${img.storage_path}`;
                            e.target.src = directGcsUrl;
                            return;
                          }
                          
                          // If primary URL fails, try the GCS fallback URL
                          if (img.gcs_url && e.target.src !== img.gcs_url) {
                            e.target.src = img.gcs_url;
                          } else {
                            // If no fallback or fallback also failed, show a placeholder with filename
                            const imageNameShort = img.name ? (img.name.length > 15 ? img.name.substring(0, 12) + '...' : img.name) : 'Unknown';
                            e.target.src = `data:image/svg+xml;base64,${btoa(`<svg width="120" height="120" xmlns="http://www.w3.org/2000/svg"><rect width="120" height="120" fill="#f5f5f5"/><text x="60" y="55" text-anchor="middle" fill="#aaa" font-family="sans-serif" font-size="9px">${imageNameShort}</text><text x="60" y="75" text-anchor="middle" fill="#aaa" font-family="sans-serif" font-size="8px">Loading failed</text></svg>`)}`;
                          }
                        }}
                        style={{width:'120px', height:'120px', objectFit:'cover', borderRadius:'4px', border:'1px solid #ddd'}}
                      />
                      <div style={{fontSize:'0.8rem', marginTop:'0.3rem', wordBreak:'break-word', maxHeight:'2.4rem', overflow:'hidden'}}>
                        {img.name || 'Untitled'}
                      </div>
                      <button
                        onClick={() => {
                          if (window.confirm(`Delete image "${img.name || 'Untitled'}"?`)) {
                            handleDeleteImage(selectedFolder, img);
                          }
                        }}
                        title="Delete image"
                        style={{position:'absolute', top:5, right:5, background:'#f33', color:'#fff', border:'none', borderRadius:'50%', width:'25px', height:'25px', fontWeight:'bold', cursor:'pointer', fontSize:'1rem', lineHeight:'23px', padding:0}}
                      >&times;</button>
                    </div>
                  ))}
                  {folders[selectedFolder]?.length === 0 && (
                    <div style={{padding:'1rem', background:'#eee', borderRadius:'4px', width:'100%'}}>
                      No images in this folder. You can upload new images using the form above.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
