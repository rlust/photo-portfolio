import React, { useState } from "react";

export default function LargeBatchUpload({ onUploaded }) {
  const [files, setFiles] = useState([]);
  const [progress, setProgress] = useState({});
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [folder, setFolder] = useState("");

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
    setProgress({});
    setError(null);
  };

  const handleFolderChange = (e) => {
    setFolder(e.target.value);
  };

  const handleUpload = async () => {
    setUploading(true);
    setError(null);
    let newProgress = {};
    for (const file of files) {
      try {
        // 1. Request a signed URL for this file
        const res = await fetch(
          `https://photoportfolio-backend-839093975626.us-central1.run.app/api/signed-url`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              filename: file.name,
              contentType: file.type,
              folder,
            }),
          }
        );
        if (!res.ok) throw new Error(`Failed to get signed URL for ${file.name}`);
        const { url, publicUrl } = await res.json();
        // 2. Upload the file directly to GCS
        await new Promise((resolve, reject) => {
          const xhr = new window.XMLHttpRequest();
          xhr.open("PUT", url);
          xhr.setRequestHeader("Content-Type", file.type);
          xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
              newProgress[file.name] = Math.round((e.loaded / e.total) * 100);
              setProgress({ ...newProgress });
            }
          };
          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              newProgress[file.name] = 100;
              setProgress({ ...newProgress });
              resolve();
            } else {
              reject(new Error(`Failed to upload ${file.name}`));
            }
          };
          xhr.onerror = () => reject(new Error(`Network error uploading ${file.name}`));
          xhr.send(file);
        });
        // 3. Notify backend to register the file
        await fetch(
          `https://photoportfolio-backend-839093975626.us-central1.run.app/api/register-upload`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              filename: file.name,
              contentType: file.type,
              folder,
              publicUrl,
            }),
          }
        );
      } catch (err) {
        newProgress[file.name] = -1;
        setProgress({ ...newProgress });
        setError(err.message);
      }
    }
    setUploading(false);
    if (onUploaded) onUploaded();
  };

  return (
    <div style={{ padding: 20 }}>
      <h2>Large Batch Upload (Direct to Cloud)</h2>
      <label>
        Folder name:
        <input
          type="text"
          value={folder}
          onChange={handleFolderChange}
          disabled={uploading}
          style={{ marginLeft: 8 }}
        />
      </label>
      <br />
      <input
        type="file"
        multiple
        onChange={handleFileChange}
        disabled={uploading}
        style={{ margin: "10px 0" }}
      />
      <br />
      <button onClick={handleUpload} disabled={!files.length || !folder || uploading}>
        Upload All
      </button>
      {error && <div style={{ color: "red" }}>{error}</div>}
      <div style={{ marginTop: 20 }}>
        {files.map((file) => (
          <div key={file.name}>
            {file.name} - {progress[file.name] === 100
              ? "Uploaded"
              : progress[file.name] === -1
              ? "Failed"
              : progress[file.name] >= 0
              ? `${progress[file.name]}%`
              : "Pending"}
          </div>
        ))}
      </div>
    </div>
  );
}
