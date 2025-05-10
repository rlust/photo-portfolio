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
          style={{ color: '#fff', background: '#2a5298', padding: '0.75rem 1.5rem', borderRadius: '2rem', textDecoration: 'none', fontWeight: 'bold', boxShadow: '0 4px 20px rgba(30,60,114,0.1)' }}
        >
          View on GitHub
        </a>
      </header>

      {/* SEARCH UI */}
      <section style={{ margin: '2rem auto', maxWidth: 900, background: '#fff', borderRadius: '8px', boxShadow: '0 2px 8px #0001', padding: '1.5rem' }}>
        <h2 style={{ marginTop: 0 }}>Search Images</h2>
        <form onSubmit={handleSearchSubmit} style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem', alignItems: 'center' }}>
          <input name="name" type="text" placeholder="Image name contains..." value={search.name} onChange={handleSearchChange} />
          <input name="folder" type="text" placeholder="Folder name..." value={search.folder} onChange={handleSearchChange} />
          <input name="mimetype" type="text" placeholder="Mimetype (e.g. image/jpeg)" value={search.mimetype} onChange={handleSearchChange} />
          <input name="date_from" type="date" value={search.date_from} onChange={handleSearchChange} />
          <input name="date_to" type="date" value={search.date_to} onChange={handleSearchChange} />
          <button type="submit" disabled={searching}>{searching ? 'Searching...' : 'Search'}</button>
          {searchResults && <button type="button" onClick={handleClearSearch}>Clear</button>}
        </form>
        {searchError && <div style={{ color: 'red', marginTop: '0.5rem' }}>{searchError}</div>}
        {searchResults && (
          <div style={{ marginTop: '1rem' }}>
            <h3>Search Results ({searchResults.length})</h3>
            {searchResults.length === 0 && <div>No images found.</div>}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1rem' }}>
              {searchResults.map((img, idx) => (
                <div key={img.url + idx} style={{ border: '1px solid #eee', borderRadius: '6px', padding: '0.5rem', minWidth: '160px', background: '#fafbfc', position: 'relative' }}>
                  <img
                    src={img.url}
                    alt={img.name}
                    title={img.name}
                    style={{ width: '120px', height: '120px', objectFit: 'cover', borderRadius: '4px', border: '1px solid #ccc' }}
                  />
                  <div style={{ fontWeight: 'bold', marginTop: '0.5rem' }}>{img.name}</div>
                  <div style={{ fontSize: '0.9em', color: '#444' }}>{img.folder}</div>
                  <div style={{ fontSize: '0.85em', color: '#888' }}>{img.mimetype}</div>
                  <div style={{ fontSize: '0.8em', color: '#aaa' }}>{img.uploaded_at?.slice(0, 10)}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* FOLDERS & IMAGES UI */}
      <section style={{ marginBottom: '2rem', background: '#fff', borderRadius: '8px', boxShadow: '0 2px 8px #0001', padding: '1.5rem' }}>
        <h2 style={{ marginTop: 0 }}>Folders & Images</h2>
        {loadingFolders && <div>Loading folders...</div>}
        {foldersError && <div style={{ color: 'red' }}>{foldersError}</div>}
        {!loadingFolders && !foldersError && !searchResults && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem' }}>
            {Object.keys(folders).length === 0 && <div>No folders found.</div>}
            {Object.entries(folders).map(([folder, images]) => (
              <div key={folder} style={{ border: '1px solid #ddd', borderRadius: '8px', padding: '1rem', minWidth: '220px', background: '#fafbfc', position: 'relative' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{folder}</span>
                  <button onClick={() => handleDeleteFolder(folder)} style={{ background: '#f33', color: '#fff', border: 'none', borderRadius: '4px', padding: '0.25rem 0.7rem', fontWeight: 'bold', cursor: 'pointer' }}>Delete Folder</button>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                  {images.map((img, idx) => (
                    <div key={img.name + idx} style={{ position: 'relative', display: 'inline-block' }}>
                      <img
                        src={img.url}
                        alt={img.name}
                        title={img.name}
                        style={{ width: '80px', height: '80px', objectFit: 'cover', borderRadius: '4px', border: '1px solid #ccc' }}
                      />
                      <button
                        onClick={() => handleDeleteImage(folder, img.name)}
                        title="Delete image"
                        style={{ position: 'absolute', top: 2, right: 2, background: '#f33', color: '#fff', border: 'none', borderRadius: '50%', width: '20px', height: '20px', fontWeight: 'bold', cursor: 'pointer', fontSize: '0.9rem', lineHeight: '18px', padding: 0 }}
                      >&times;</button>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* UPLOAD UI */}
      <section style={{ padding: '2rem', borderTop: '1px solid #eee' }}>
        <h2>Upload a Group of Images to a Folder</h2>
        <form onSubmit={handleGroupUpload} style={{ marginBottom: '2rem', background: '#f3f6fa', padding: '1rem', borderRadius: '8px', maxWidth: '500px' }}>
          <div style={{ marginBottom: '0.5rem' }}>
            <input
              type="text"
              placeholder="Folder Name"
              value={folderName}
              required
              onChange={e => setFolderName(e.target.value)}
              style={{ width: '100%', padding: '0.5rem' }}
            />
          </div>
          <div style={{ marginBottom: '0.5rem' }}>
            <input
              type="file"
              multiple
              accept="image/*"
              onChange={e => setFolderImages([...e.target.files])}
              style={{ width: '100%' }}
            />
          </div>
          <button type="submit" disabled={uploadingGroup} style={{ padding: '0.5rem 1.5rem', background: '#2a5298', color: '#fff', border: 'none', borderRadius: '4px', fontWeight: 'bold' }}>
            {uploadingGroup ? 'Uploading...' : 'Upload Images'}
          </button>
          {groupUploadError && <div style={{ color: 'red', marginTop: '0.5rem' }}>{groupUploadError}</div>}
        </form>
      </section>

      {/* USERS UI */}
      <section style={{ padding: '2rem' }}>
        <h2>Users from Backend API</h2>
        {loadingUsers && <p>Loading users...</p>}
        {userError && <p style={{ color: 'red' }}>Error: {userError}</p>}
        {!loadingUsers && !userError && (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {users.length === 0 && <li>No users found.</li>}
            {users.map((user, idx) => (
              <li key={user.id || idx} style={{ marginBottom: '0.5rem' }}>
                <strong>{user.name}</strong> ({user.email})
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

export default App;
