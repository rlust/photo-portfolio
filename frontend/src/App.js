import './App.css';

import React, { useEffect, useState } from 'react';
import GalleryView from './components/GalleryView';
import AdminPanel from './components/AdminPanel';
import LightboxModal from './components/LightboxModal';
import LargeBatchUpload from './components/LargeBatchUpload';

// --- AI-Powered File Search ---
const SEMANTIC_SEARCH_API = 'https://photoportfolio-backend-839093975626.us-central1.run.app/api/photos/semantic-search';
// const WEB_SEARCH_API = 'https://photoportfolio-backend-839093975626.us-central1.run.app/api/web-search'; // (legacy)


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
  //   fetch('https://photoportfolio-backend-839093975626.us-central1.run.app/api/photos')
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

  // Fetch folders and their images
  const fetchFolders = () => {
    setLoadingFolders(true);
    fetch('https://photoportfolio-backend-839093975626.us-central1.run.app/api/folders')
      .then(res => {
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
      })
      .then(data => {
        setFolders(data || {});
        setLoadingFolders(false);
      })
      .catch(err => {
        setFoldersError(err.message);
        setLoadingFolders(false);
      });
  };

  useEffect(() => {
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
    setUploadingGroup(true);
    setGroupUploadError(null);
    setUploadProgress(0);
    let batches;
    try {
      batches = batchFiles(folderImages, 32);
    } catch (err) {
      setGroupUploadError(err.message);
      setUploadingGroup(false);
      setUploadProgress(0);
      return;
    }
    let uploadedCount = 0;
    try {
      for (let batchIdx = 0; batchIdx < batches.length; batchIdx++) {
        const batch = batches[batchIdx];
        if (!batch.length) continue;
        const batchSize = batch.reduce((a, f) => a + f.size, 0);
        console.log(`Uploading batch ${batchIdx + 1}/${batches.length} (${batch.length} files, ${(batchSize/(1024*1024)).toFixed(2)}MB):`, batch.map(f => f.name));
        const formData = new FormData();
        formData.append('folder', folderName);
        batch.forEach(file => formData.append('images', file));
        // Calculate base uploaded count for this batch
        const baseUploadedCount = uploadedCount;
        await new Promise((resolve, reject) => {
          const xhr = new window.XMLHttpRequest();
          xhr.open('POST', 'https://photoportfolio-backend-839093975626.us-central1.run.app/api/upload');
          xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
              // Progress: percent of all batches
              const batchProgress = (e.loaded / e.total) * 100;
              const totalUploaded = baseUploadedCount + (batchProgress / 100 * batch.length);
              const totalProgress = Math.round((totalUploaded / folderImages.length) * 100);
              setUploadProgress(totalProgress > 100 ? 100 : totalProgress);
            }
          };
          xhr.onload = () => {
            console.log(`Batch ${batchIdx + 1} upload complete, status:`, xhr.status, xhr.responseText);
            if (xhr.status >= 200 && xhr.status < 300) {
              resolve();
            } else {
              let msg = `Failed to upload batch ${batchIdx + 1}`;
              try {
                const data = JSON.parse(xhr.responseText);
                if (data && data.error) msg = data.error;
              } catch {}
              reject(new Error(msg));
            }
          };
          xhr.onerror = () => {
            console.error(`Network error uploading batch ${batchIdx + 1}`);
            reject(new Error(`Upload failed: network error (batch ${batchIdx + 1})`));
          };
          xhr.send(formData);
        });
        // Only increment after batch is done
        uploadedCount += batch.length;
      }
      setFolderName("");
      setFolderImages([]);
      setUploadingGroup(false);
      setUploadProgress(0);
      fetchFolders();
    } catch (err) {
      setGroupUploadError(err.message);
      setUploadingGroup(false);
      setUploadProgress(0);
      console.error('Upload error:', err);
    }
  };


  // Delete image
  const handleDeleteImage = async (folder, name) => {
    if (!window.confirm(`Delete image "${name}" from folder "${folder}"?`)) return;
    try {
      await fetch(
        `https://photoportfolio-backend-839093975626.us-central1.run.app/api/folder/${encodeURIComponent(folder)}/${encodeURIComponent(name)}`,
        { method: 'DELETE' }
      );
      fetchFolders();
    } catch (err) {
      alert('Error deleting image: ' + err.message);
    }
  };

  // Delete folder
  const handleDeleteFolder = async (folder) => {
    if (!window.confirm(`Delete folder "${folder}" and ALL images in it? This cannot be undone.`)) return;
    try {
      await fetch(
        `https://photoportfolio-backend-839093975626.us-central1.run.app/api/folder/${encodeURIComponent(folder)}`,
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
                <img src={img.url} alt={img.name} style={{width:'100%',maxWidth:500,maxHeight:300,objectFit:'contain',borderRadius:'8px',border:'1px solid #eee',background:'#fafbfc'}} onError={e => {e.target.onerror=null; e.target.src='https://via.placeholder.com/500x300?text=Image+not+found';}}/>
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
      {tab === 'gallery' && <GalleryView folders={folders} />}
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
        <LargeBatchUpload onUploaded={fetchFolders} />
      )}
    </div>
  );
}

export default App;
