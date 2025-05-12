import React, { useState, useEffect } from "react";

export default function GalleryView({ folders }) {
  // All hooks must be at the top
  const [selectedFolder, setSelectedFolder] = useState(null);

  const [theme, setTheme] = useState('light');
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIdx, setLightboxIdx] = useState(0);
  const [zoomed, setZoomed] = useState(false);

  const folderNames = Object.keys(folders);

  // Compute images to display
  // Only show images from the selected folder
  const images = selectedFolder ? (folders[selectedFolder] || []) : [];


  useEffect(() => {
    document.body.classList.remove('theme-dark', 'theme-light');
    document.body.classList.add('theme-' + theme);
  }, [theme]);

  if (!folders || folderNames.length === 0) {
    return <div style={{marginTop:'2rem', color:'#666', fontSize:'1.2rem'}}>No folders or images found. Try uploading images from the Admin panel.</div>;
  }

  const openLightbox = idx => {
    setLightboxIdx(idx);
    setLightboxOpen(true);
    setZoomed(false);
  };
  const closeLightbox = () => {
    setLightboxOpen(false);
    setZoomed(false);
  };
  const showPrev = () => {
    setLightboxIdx(idx => (idx - 1 + images.length) % images.length);
    setZoomed(false);
  };
  const showNext = () => {
    setLightboxIdx(idx => (idx + 1) % images.length);
    setZoomed(false);
  };

  return (
    <div style={{margin:'2rem auto',maxWidth:1000,position:'relative'}}>
      <button
        className="theme-toggle"
        aria-label="Toggle theme"
        onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        title={theme === 'dark' ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
      >{theme === 'dark' ? '🌙' : '☀️'}</button>
      {/* Folder Dropdown Selector Only */}
      <div style={{display:'flex',justifyContent:'center',alignItems:'center',margin:'2rem 0 2.5rem 0'}}>
        <label htmlFor="folder-select" style={{marginRight:14,fontWeight:'bold',fontSize:'1.1rem',color:'var(--text-main,#222)'}}>Select Folder:</label>
        <select
          id="folder-select"
          value={selectedFolder || ''}
          onChange={e => setSelectedFolder(e.target.value || null)}
          style={{padding:'0.7rem 1.2rem',fontSize:'1.13rem',borderRadius:9,border:'1.5px solid #bbb',background:'#f7f8fa',color:'#222',fontWeight:'bold',boxShadow:'0 2px 8px #0001'}}
          aria-label="Select folder to view"
        >
          <option value="" disabled>Choose a folder...</option>
          {folderNames.map(folder => (
            <option key={folder} value={folder}>{folder} ({folders[folder]?.length || 0} images)</option>
          ))}
        </select>
      </div>
      {selectedFolder === null ? (
        <div style={{color:'var(--text-muted, #888)',marginTop:'2.5rem',fontSize:'1.18rem',textAlign:'center'}}>Please select a folder to view its images.</div>
      ) : images.length === 0 ? (
        <div style={{color:'var(--text-muted, #888)',marginTop:'2rem'}}>No images found in the selected folder.</div>
      ) : (
        <div className="gallery-grid">
          {images.map((img,idx) => (
            <div className="gallery-card" key={img.url+idx}>
              {img.url ? (
                <img
                  src={img.url}
                  alt={img.name || 'Image'}
                  title={img.name || ''}
                  className="gallery-img"
                  onClick={() => openLightbox(idx)}
                  onError={e => {e.target.onerror=null; e.target.src='/notfound.png';}}
                />
              ) : (
                <div style={{width:160,height:160,background:'#eee',display:'flex',alignItems:'center',justifyContent:'center',borderRadius:'6px',border:'1px solid #ddd'}}>No image</div>
              )}
              <div className="gallery-info">{img.name || 'Untitled'}</div>
              <div className="gallery-folder">{img.folder || selectedFolder}</div>
              {img.mimetype && <div style={{fontSize:'0.9em',color:'var(--text-muted, #888)'}}>{img.mimetype}</div>}
              {img.uploaded_at && <div style={{fontSize:'0.85em',color:'var(--text-muted, #aaa)'}}>{String(img.uploaded_at).slice(0,10)}</div>}
            </div>
          ))}
        </div>
      )}
      {/* Lightbox Modal with zoom and transitions */}
      {lightboxOpen && images[lightboxIdx] && (
        <div
          className="lightbox-fade"
          style={{
            position: 'fixed', top:0, left:0, right:0, bottom:0,
            background: 'rgba(0,0,0,0.85)', zIndex: 1000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            animation: 'lightbox-fadein 0.35s',
          }}
          tabIndex={-1}
          onKeyDown={e => {
            if (e.key === 'Escape') closeLightbox();
            if (e.key === 'ArrowLeft') showPrev();
            if (e.key === 'ArrowRight') showNext();
          }}
        >
          <button onClick={closeLightbox} style={{position:'absolute',top:30,right:40,fontSize:32,color:'#fff',background:'none',border:'none',cursor:'pointer',fontWeight:'bold'}}>×</button>
          <button onClick={showPrev} style={{position:'absolute',left:40,top:'50%',transform:'translateY(-50%)',fontSize:40,color:'#fff',background:'none',border:'none',cursor:'pointer',fontWeight:'bold'}}>&#8592;</button>
          <img
            src={images[lightboxIdx].url}
            alt={images[lightboxIdx].name}
            className={zoomed ? 'lightbox-img zoomed' : 'lightbox-img'}
            onClick={() => setZoomed(z => !z)}
            style={{transition:'transform 0.3s'}}
          />
          <button onClick={showNext} style={{position:'absolute',right:40,top:'50%',transform:'translateY(-50%)',fontSize:40,color:'#fff',background:'none',border:'none',cursor:'pointer',fontWeight:'bold'}}>&#8594;</button>
          <div style={{position:'absolute',bottom:40,left:0,right:0,textAlign:'center',color:'#fff',fontSize:'1.2rem',fontWeight:'bold',textShadow:'0 2px 8px #000'}}>{images[lightboxIdx].name}</div>
        </div>
      )}
    </div>
  );
}


