import './App.css';

import React, { useEffect, useState } from 'react';
import GalleryView from './components/GalleryView';
import AdminPanel from './components/AdminPanel';
import LightboxModal from './components/LightboxModal';

function App() {

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

  // Helper: batch files so each batch is <= 32MB
  function batchFiles(files, maxBatchSizeMB = 32) {
    const batches = [];
    let currentBatch = [];
    let currentBatchSize = 0;
    for (const file of files) {
      const fileSizeMB = file.size / (1024 * 1024);
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

  // Handle group image upload with batching and progress
  const handleGroupUpload = async (e) => {
    e.preventDefault();
    setUploadingGroup(true);
    setGroupUploadError(null);
    setUploadProgress(0);
    const batches = batchFiles(folderImages, 32);
    let uploadedCount = 0;
    try {
      for (let batchIdx = 0; batchIdx < batches.length; batchIdx++) {
        const batch = batches[batchIdx];
        const formData = new FormData();
        formData.append('folder', folderName);
        batch.forEach(file => formData.append('images', file));
        await new Promise((resolve, reject) => {
          const xhr = new window.XMLHttpRequest();
          xhr.open('POST', 'https://photoportfolio-backend-839093975626.us-central1.run.app/api/upload');
          xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
              // Progress: percent of all batches
              const batchProgress = (e.loaded / e.total) * 100;
              const totalProgress = Math.round(((uploadedCount + batchProgress / 100 * batch.length) / folderImages.length) * 100);
              setUploadProgress(totalProgress > 100 ? 100 : totalProgress);
            }
          };
          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              uploadedCount += batch.length;
              resolve();
            } else {
              let msg = 'Failed to upload images';
              try {
                const data = JSON.parse(xhr.responseText);
                if (data && data.error) msg = data.error;
              } catch {}
              reject(new Error(msg));
            }
          };
          xhr.onerror = () => {
            reject(new Error('Upload failed: network error'));
          };
          xhr.send(formData);
        });
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

  // User/Admin view toggle
  const [adminMode, setAdminMode] = useState(false);

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
        <div style={{display:'flex',justifyContent:'center',marginBottom:'1rem'}}>
          <button onClick={()=>setAdminMode(false)} style={{marginRight:'0.5rem',padding:'0.5rem 1.2rem',borderRadius:'4px',border:'none',background:!adminMode?'#222':'#eee',color:!adminMode?'#fff':'#444',fontWeight:'bold',cursor:'pointer',fontSize:'1.1rem'}}>Gallery</button>
          <button onClick={()=>setAdminMode(true)} style={{padding:'0.5rem 1.2rem',borderRadius:'4px',border:'none',background:adminMode?'#222':'#eee',color:adminMode?'#fff':'#444',fontWeight:'bold',cursor:'pointer',fontSize:'1.1rem'}}>Admin</button>
        </div>
      </header>

      {/* Full-size scrollable image carousel with lightbox and autoplay */}
      {!adminMode && allImages.length > 0 && (
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

      {/* Main content: Gallery or Admin */}
      {!adminMode ? (
        <GalleryView folders={folders} />
      ) : (
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
    </div>
  );
}

export default App;
