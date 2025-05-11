import React from "react";

export default function AdminPanel({
  folderName, setFolderName, folderImages, setFolderImages, uploadingGroup, groupUploadError, handleGroupUpload,
  uploadProgress,
  folders, loadingFolders, foldersError, handleDeleteFolder, handleDeleteImage
}) {
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
      <h3>Folders & Images (with Admin Controls)</h3>
      {loadingFolders && <div>Loading folders...</div>}
      {foldersError && <div style={{color:'red'}}>{foldersError}</div>}
      {!loadingFolders && !foldersError && (
        <div style={{display:'flex',flexWrap:'wrap',gap:'2rem'}}>
          {Object.keys(folders).length === 0 && <div>No folders found.</div>}
          {Object.entries(folders).map(([folder,images]) => (
            <div key={folder} style={{border:'1px solid #ddd',borderRadius:'8px',padding:'1rem',minWidth:'220px',background:'#fafbfc',position:'relative'}}>
              <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'0.5rem'}}>
                <span style={{fontWeight:'bold',fontSize:'1.1rem'}}>{folder}</span>
                <button onClick={()=>handleDeleteFolder(folder)} style={{background:'#f33',color:'#fff',border:'none',borderRadius:'4px',padding:'0.25rem 0.7rem',fontWeight:'bold',cursor:'pointer'}}>Delete Folder</button>
              </div>
              <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem'}}>
                {images.map((img,idx) => (
                  <div key={img.name+idx} style={{position:'relative',display:'inline-block'}}>
                    <img
                      src={img.url}
                      alt={img.name}
                      title={img.name}
                      style={{width:'80px',height:'80px',objectFit:'cover',borderRadius:'4px',border:'1px solid #ccc'}}
                    />
                    <button
                      onClick={()=>handleDeleteImage(folder,img.name)}
                      title="Delete image"
                      style={{position:'absolute',top:2,right:2,background:'#f33',color:'#fff',border:'none',borderRadius:'50%',width:'20px',height:'20px',fontWeight:'bold',cursor:'pointer',fontSize:'0.9rem',lineHeight:'18px',padding:0}}
                    >&times;</button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
