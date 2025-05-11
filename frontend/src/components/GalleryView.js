import React, { useState, useRef, useEffect } from "react";

export default function GalleryView({ folders }) {
  // null means "All Folders"
  const [selectedFolder, setSelectedFolder] = useState(null);
  const scrollRef = useRef(null);
  const [scrollIndex, setScrollIndex] = useState(0);

  const folderNames = Object.keys(folders);

  // Compute images to display
  const images = selectedFolder && selectedFolder !== '__ALL__'
    ? (folders[selectedFolder] || [])
    : folderNames.flatMap(folder => (folders[folder] || []).map(img => ({...img, folder})));

  // After 15 seconds, start scrolling images horizontally in a loop (only if there are images)
  useEffect(() => {
    if (!images.length) return;
    let timer = setTimeout(() => {
      const interval = setInterval(() => {
        setScrollIndex(idx => (idx + 1) % images.length);
      }, 2000); // scroll every 2s
      return () => clearInterval(interval);
    }, 15000); // start after 15s
    return () => clearTimeout(timer);
  }, [images.length]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        left: scrollIndex * 200, // image width + margin
        behavior: 'smooth'
      });
    }
  }, [scrollIndex, images.length]);

  if (!folders || folderNames.length === 0) {
    return <div style={{marginTop:'2rem', color:'#666', fontSize:'1.2rem'}}>No folders or images found. Try uploading images from the Admin panel.</div>;
  }

  // Gallery UI with folder selector
  return (
    <div style={{margin:'2rem auto',maxWidth:1000}}>
      <div style={{display:'flex',alignItems:'center',gap:'1rem',marginBottom:'2rem'}}>
        <label htmlFor="gallery-folder-select" style={{fontWeight:'bold'}}>Select Folder:</label>
        <select
          id="gallery-folder-select"
          value={selectedFolder || '__ALL__'}
          onChange={e => { setSelectedFolder(e.target.value === '__ALL__' ? null : e.target.value); setScrollIndex(0); }}
          style={{padding:'0.5rem 1rem',fontSize:'1.1rem',borderRadius:'4px',border:'1px solid #ccc'}}
        >
          <option value="__ALL__">All Folders</option>
          {folderNames.map(folder => (
            <option key={folder} value={folder}>{folder}</option>
          ))}
        </select>
      </div>
      {images.length === 0 ? (
        <div style={{color:'#888',marginTop:'2rem'}}>No images found in the selected folder.</div>
      ) : (
        <div ref={scrollRef} style={{display:'flex',overflowX:'auto',gap:'1.5rem',scrollBehavior:'smooth',paddingBottom:'1rem'}}>
          {images.map((img,idx) => (
            <div key={img.url+idx} style={{background:'#fafbfc',borderRadius:'8px',padding:'1rem',boxShadow:'0 2px 8px #0001',minWidth:180}}>
              {img.url ? (
                <img
                  src={img.url}
                  alt={img.name || 'Image'}
                  title={img.name || ''}
                  style={{width:160,height:160,objectFit:'cover',borderRadius:'6px',border:'1px solid #ddd'}}
                  onError={e => {e.target.onerror=null; e.target.src='https://via.placeholder.com/160x160?text=Image+not+found';}}
                />
              ) : (
                <div style={{width:160,height:160,background:'#eee',display:'flex',alignItems:'center',justifyContent:'center',borderRadius:'6px',border:'1px solid #ddd'}}>No image</div>
              )}
              <div style={{fontWeight:'bold',marginTop:'0.5rem'}}>{img.name || 'Untitled'}</div>
              <div style={{fontSize:'0.95em',color:'#888'}}>{img.folder || selectedFolder}</div>
              {img.mimetype && <div style={{fontSize:'0.9em',color:'#888'}}>{img.mimetype}</div>}
              {img.uploaded_at && <div style={{fontSize:'0.85em',color:'#aaa'}}>{String(img.uploaded_at).slice(0,10)}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}


