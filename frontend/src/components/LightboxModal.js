import React from "react";

export default function LightboxModal({ open, image, onClose, onPrev, onNext }) {
  if (!open || !image) return null;
  return (
    <div style={{
      position: 'fixed',
      top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.85)',
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center'
    }}>
      <button onClick={onClose} style={{position:'absolute',top:30,right:40,fontSize:32,color:'#fff',background:'none',border:'none',cursor:'pointer',fontWeight:'bold'}}>×</button>
      <button onClick={onPrev} style={{position:'absolute',left:40,top:'50%',transform:'translateY(-50%)',fontSize:40,color:'#fff',background:'none',border:'none',cursor:'pointer',fontWeight:'bold'}}>&#8592;</button>
      <img src={image.url} alt={image.name} style={{maxWidth:'90vw',maxHeight:'80vh',borderRadius:'8px',boxShadow:'0 4px 24px #000a',background:'#fff'}}/>
      <button onClick={onNext} style={{position:'absolute',right:40,top:'50%',transform:'translateY(-50%)',fontSize:40,color:'#fff',background:'none',border:'none',cursor:'pointer',fontWeight:'bold'}}>&#8594;</button>
      <div style={{position:'absolute',bottom:40,left:0,right:0,textAlign:'center',color:'#fff',fontSize:'1.2rem',fontWeight:'bold',textShadow:'0 2px 8px #000'}}>{image.name}</div>
    </div>
  );
}
