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
  // Theme toggle state (local, fallback if not provided by parent)
  const [theme, setTheme] = useState('light');
  useEffect(() => {
    document.body.classList.remove('theme-dark', 'theme-light');
    document.body.classList.add('theme-' + theme);
  }, [theme]);

  // Lightbox state
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxIdx, setLightboxIdx] = useState(0);
  const [zoomed, setZoomed] = useState(false);

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
      {/* Folder Carousel */}
      <div className="folder-carousel" style={{display:'flex',overflowX:'auto',gap:'1.5rem',padding:'1rem 0 2rem 0',marginBottom:'1rem',scrollSnapType:'x mandatory'}}>
        {/* All Folders Card */}
        <div
          className={`folder-card${!selectedFolder ? ' selected' : ''}`}
          style={{minWidth:160,cursor:'pointer',scrollSnapAlign:'start',position:'relative'}}
          onClick={()=>setSelectedFolder(null)}
        >
          <div style={{
            width: '100%', height: 90, background: '#e3e7ee', borderRadius: 8,
            display:'flex',alignItems:'center',justifyContent:'center',fontSize:36,color:'#aaa',marginBottom:8
          }}>📁</div>
          <div style={{fontWeight:'bold',fontSize:'1.1rem'}}>All Folders</div>
          <div style={{color:'var(--text-muted,#888)',fontSize:'0.97em'}}>({folderNames.reduce((a,f)=>a+(folders[f]?.length||0),0)} images)</div>
        </div>
        {/* Folder Cards */}
        {folderNames.map(folder => {
          const imgs = folders[folder] || [];
          const preview = imgs[0]?.url;
          return (
            <div
              className={`folder-card${selectedFolder===folder?' selected':''}`}
              key={folder}
              style={{minWidth:160,cursor:'pointer',scrollSnapAlign:'start',position:'relative'}}
              onClick={()=>setSelectedFolder(folder)}
              tabIndex={0}
              onKeyDown={e=>{if(e.key==='Enter')setSelectedFolder(folder);}}
              onMouseEnter={e=>{
                if(window.innerWidth>700 && imgs.length>1) {
                  const pop = document.createElement('div');
                  pop.className = 'folder-popover';
                  pop.style.position = 'absolute';
                  pop.style.top = '100px';
                  pop.style.left = '0';
                  pop.style.zIndex = '2000';
                  pop.style.background = 'var(--bg-card,#fff)';
                  pop.style.border = '1px solid var(--border,#eee)';
                  pop.style.borderRadius = '8px';
                  pop.style.padding = '0.7rem';
                  pop.style.boxShadow = '0 4px 24px #0002';
                  pop.style.display = 'flex';
                  pop.style.gap = '0.4rem';
                  pop.style.pointerEvents = 'none';
                  pop.style.transition = 'opacity 0.2s';
                  imgs.slice(0,4).forEach(img => {
                    const thumb = document.createElement('img');
                    thumb.src = img.url;
                    thumb.alt = img.name;
                    thumb.style.width = '54px';
                    thumb.style.height = '54px';
                    thumb.style.objectFit = 'cover';
                    thumb.style.borderRadius = '6px';
                    thumb.style.border = '1px solid #eee';
                    pop.appendChild(thumb);
                  });
                  e.currentTarget.appendChild(pop);
                  e.currentTarget._popover = pop;
                }
              }}
              onMouseLeave={e=>{
                if(e.currentTarget._popover){
                  e.currentTarget.removeChild(e.currentTarget._popover);
                  e.currentTarget._popover = null;
                }
              }}
            >
              <div style={{
                width: '100%', height: 90, background: '#e3e7ee', borderRadius: 8,
                display:'flex',alignItems:'center',justifyContent:'center',marginBottom:8,
                overflow:'hidden',position:'relative'
              }}>
                {preview ? (
                  <img src={preview} alt={folder} style={{width:'100%',height:'100%',objectFit:'cover',borderRadius:8}} onError={e => {e.target.onerror=null; e.target.src='/notfound.png';}}/>
                ) : (
                  <span style={{fontSize:36,color:'#bbb'}}>📁</span>
                )}
              </div>
              <div style={{fontWeight:'bold',fontSize:'1.1rem',whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}} title={folder}>{folder}</div>
              <div style={{color:'var(--text-muted,#888)',fontSize:'0.97em'}}>({imgs.length} images)</div>
            </div>
          );
        })}
      </div>
      {images.length === 0 ? (
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


