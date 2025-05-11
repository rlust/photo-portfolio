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

  // Handle group image upload
  const handleGroupUpload = (e) => {
    e.preventDefault();
    setUploadingGroup(true);
    setGroupUploadError(null);
    const formData = new FormData();
    formData.append('folder', folderName);
    for (let i = 0; i < folderImages.length; i++) {
      formData.append('images', folderImages[i]);
    }
    fetch('https://photoportfolio-backend-839093975626.us-central1.run.app/api/upload', {
      method: 'POST',
      body: formData
    })
      .then(async res => {
        if (!res.ok) {
          let msg = 'Failed to upload images';
          try {
            const data = await res.json();
            if (data && data.error) msg = data.error;
          } catch {}
          throw new Error(msg);
        }
        return res.json();
      })
      .then(() => {
        setFolderName("");
        setFolderImages([]);
        setUploadingGroup(false);
        fetchFolders();
      })
      .catch(err => {
        setGroupUploadError(err.message);
        setUploadingGroup(false);
      });
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
