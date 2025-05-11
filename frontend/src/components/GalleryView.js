import React, { useState, useRef, useEffect } from "react";

export default function GalleryView({ folders }) {
  const [selectedFolder, setSelectedFolder] = useState(null);
  const scrollRef = useRef(null);
  const [scrollIndex, setScrollIndex] = useState(0);

  // Get images for selected folder (if any)
  const images = selectedFolder ? (folders[selectedFolder] || []) : [];

  // After 15 seconds, start scrolling images horizontally in a loop (only if a folder is selected)
  useEffect(() => {
    if (!selectedFolder || !images.length) return;
    let timer = setTimeout(() => {
      const interval = setInterval(() => {
        setScrollIndex(idx => (idx + 1) % images.length);
      }, 2000); // scroll every 2s
      return () => clearInterval(interval);
    }, 15000); // start after 15s
    return () => clearTimeout(timer);
  }, [selectedFolder, images.length]);

  useEffect(() => {
    if (!selectedFolder) return;
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        left: scrollIndex * 200, // image width + margin
        behavior: 'smooth'
      });
    }
  }, [scrollIndex, selectedFolder]);

  if (!folders || Object.keys(folders).length === 0) {
    return <div style={{marginTop:'2rem', color:'#666', fontSize:'1.2rem'}}>No folders or images found. Try uploading images from the Admin panel.</div>;
  }

  // If a folder is selected, show its images
  if (selectedFolder) {
    return (
      <div style={{margin:'2rem auto',maxWidth:1000}}>
        <button onClick={() => { setSelectedFolder(null); setScrollIndex(0); }} style={{marginBottom:'1rem',background:'#eee',border:'none',borderRadius:'4px',padding:'0.5rem 1.2rem',cursor:'pointer'}}>← Back to Folders</button>
        <h2 style={{marginTop:0}}>{selectedFolder}</h2>
        {images.length === 0 ? (
          <div style={{color:'#888',marginTop:'2rem'}}>No images in this folder.</div>
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
                {img.mimetype && <div style={{fontSize:'0.9em',color:'#888'}}>{img.mimetype}</div>}
                {img.uploaded_at && <div style={{fontSize:'0.85em',color:'#aaa'}}>{String(img.uploaded_at).slice(0,10)}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Show folders overview
  return (
    <div style={{margin:'2rem auto',maxWidth:1000}}>
      <h2 style={{marginTop:0}}>Folders</h2>
      <div style={{display:'flex',flexWrap:'wrap',gap:'2rem'}}>
        {Object.entries(folders).map(([folder,images]) => (
          <div key={folder} style={{border:'1px solid #ddd',borderRadius:'8px',padding:'1.5rem',background:'#fafbfc',minWidth:220,cursor:'pointer',boxShadow:'0 2px 8px #0001'}} onClick={()=>{setSelectedFolder(folder); setScrollIndex(0);}}>
            <div style={{fontWeight:'bold',fontSize:'1.2rem',marginBottom:'0.5rem'}}>{folder}</div>
            <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem'}}>
              {images.slice(0,3).map((img,idx) => (
                <img key={img.url+idx} src={img.url} alt={img.name} style={{width:60,height:60,objectFit:'cover',borderRadius:'4px',border:'1px solid #ccc'}}/>
              ))}
              {images.length > 3 && <span style={{marginLeft:'0.5rem',fontSize:'0.9em',color:'#888'}}>+{images.length-3} more</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

