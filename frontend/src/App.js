import './App.css';

import React, { useEffect, useState } from 'react';

function App() {
  const [users, setUsers] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [loadingPhotos, setLoadingPhotos] = useState(true);
  const [userError, setUserError] = useState(null);
  const [photoError, setPhotoError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [photoName, setPhotoName] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");

  // Fetch users
  useEffect(() => {
    fetch('https://photoportfolio-backend-839093975626.us-central1.run.app/api/users')
      .then(res => {
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
      })
      .then(data => {
        setUsers(data.users || data || []);
        setLoadingUsers(false);
      })
      .catch(err => {
        setUserError(err.message);
        setLoadingUsers(false);
      });
  }, []);

  // Fetch photos
  useEffect(() => {
    fetch('https://photoportfolio-backend-839093975626.us-central1.run.app/api/photos')
      .then(res => {
        if (!res.ok) throw new Error('Network response was not ok');
        return res.json();
      })
      .then(data => {
        setPhotos(data.photos || data || []);
        setLoadingPhotos(false);
      })
      .catch(err => {
        setPhotoError(err.message);
        setLoadingPhotos(false);
      });
  }, []);

  // Upload photo handler
  const handlePhotoUpload = (e) => {
    e.preventDefault();
    setUploading(true);
    setUploadError(null);
    fetch('https://photoportfolio-backend-839093975626.us-central1.run.app/api/photos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: photoName, url: photoUrl })
    })
      .then(res => {
        if (!res.ok) throw new Error('Failed to upload photo');
        return res.json();
      })
      .then(newPhoto => {
        setPhotos([...photos, newPhoto]);
        setPhotoName("");
        setPhotoUrl("");
        setUploading(false);
      })
      .catch(err => {
        setUploadError(err.message);
        setUploading(false);
      });
  };

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
      .then(res => {
        if (!res.ok) throw new Error('Failed to upload images');
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

  return (
    <div className="App">
      <header className="App-header" style={{padding: '2rem', background: 'linear-gradient(90deg,#1e3c72 0%,#2a5298 100%)', color: '#fff'}}>
        <h1 style={{fontSize: '2.5rem', marginBottom: '1rem'}}>PhotoPortfolio</h1>
        <p style={{fontSize: '1.25rem', maxWidth: 600, margin: '0 auto 1.5rem'}}>
          A modern web application inspired by Zenfolio, built for photographers and visual artists to showcase, organize, and deliver images online. Fast, secure, and beautiful.
        </p>
        <a
          className="App-link"
          href="https://github.com/rlust/photo-portfolio"
          target="_blank"
          rel="noopener noreferrer"
          style={{color: '#fff', background: '#2a5298', padding: '0.75rem 1.5rem', borderRadius: '2rem', textDecoration: 'none', fontWeight: 'bold', boxShadow: '0 4px 20px rgba(30,60,114,0.1)'}}
        >
          View on GitHub
        </a>
      </header>
      <section style={{padding: '2rem'}}>
        <h2>Users from Backend API</h2>
        {loadingUsers && <p>Loading users...</p>}
        {userError && <p style={{color: 'red'}}>Error: {userError}</p>}
        {!loadingUsers && !userError && (
          <ul style={{listStyle: 'none', padding: 0}}>
            {users.length === 0 && <li>No users found.</li>}
            {users.map((user, idx) => (
              <li key={user.id || idx} style={{marginBottom: '0.5rem'}}>
                <strong>{user.name}</strong> ({user.email})
              </li>
            ))}
          </ul>
        )}
      </section>
      <section style={{padding: '2rem', borderTop: '1px solid #eee'}}>
        <h2>Upload a Group of Images to a Folder</h2>
        <form onSubmit={handleGroupUpload} style={{marginBottom:'2rem', background:'#f3f6fa', padding:'1rem', borderRadius:'8px', maxWidth:'500px'}}>
          <div style={{marginBottom:'0.5rem'}}>
            <input
              type="text"
              placeholder="Folder Name"
              value={folderName}
              required
              onChange={e => setFolderName(e.target.value)}
              style={{width:'100%', padding:'0.5rem'}}
            />
          </div>
          <div style={{marginBottom:'0.5rem'}}>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={e => setFolderImages([...e.target.files])}
              style={{width:'100%'}}
            />
          </div>
          <button type="submit" disabled={uploadingGroup} style={{padding:'0.5rem 1.5rem', background:'#2a5298', color:'#fff', border:'none', borderRadius:'4px', fontWeight:'bold'}}>
            {uploadingGroup ? 'Uploading...' : 'Upload Images'}
          </button>
          {groupUploadError && <div style={{color:'red', marginTop:'0.5rem'}}>{groupUploadError}</div>}
        </form>
        <h2>Folders & Images</h2>
        {loadingFolders && <p>Loading folders...</p>}
        {foldersError && <p style={{color:'red'}}>Error: {foldersError}</p>}
        {!loadingFolders && !foldersError && (
          <div style={{display:'flex', flexWrap:'wrap', gap:'2rem'}}>
            {Object.keys(folders).length === 0 && <div>No folders found.</div>}
            {Object.entries(folders).map(([folder, images]) => (
              <div key={folder} style={{border:'1px solid #ddd', borderRadius:'8px', padding:'1rem', minWidth:'220px', background:'#fafbfc'}}>
                <div style={{fontWeight:'bold', marginBottom:'0.5rem', fontSize:'1.1rem'}}>{folder}</div>
                <div style={{display:'flex', flexWrap:'wrap', gap:'0.5rem'}}>
                  {images.map((img, idx) => (
                    <img
                      key={img.name+idx}
                      src={`https://photoportfolio-backend-839093975626.us-central1.run.app/api/folder/${encodeURIComponent(folder)}/${encodeURIComponent(img.name)}`}
                      alt={img.name}
                      title={img.name}
                      style={{width:'80px', height:'80px', objectFit:'cover', borderRadius:'4px', border:'1px solid #ccc'}}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export default App;
