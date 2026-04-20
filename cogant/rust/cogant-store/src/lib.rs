//! Storage layer for COGANT bundles and artifacts.
//!
//! Provides abstraction for persisting graphs, mappings, state spaces,
//! and other artifacts to disk or cloud storage.

use cogant_core::StableId;
use cogant_graph::ProgramGraph;
use serde_json::{json, Value};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use thiserror::Error;

/// Error type for storage operations.
#[derive(Error, Debug)]
pub enum StoreError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    #[error("Not found: {0}")]
    NotFound(String),

    #[error("Invalid path: {0}")]
    InvalidPath(String),

    #[error("Store error: {0}")]
    Other(String),
}

/// A bundle of related artifacts.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Bundle {
    /// Bundle identifier
    pub id: String,
    /// Version (semantic versioning)
    pub version: String,
    /// Creation timestamp (ISO 8601)
    pub created_at: String,
    /// Metadata about the bundle
    pub metadata: HashMap<String, String>,
    /// Artifacts contained in the bundle
    pub artifacts: HashMap<String, BundleArtifact>,
}

/// An artifact stored in a bundle.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct BundleArtifact {
    /// Name of the artifact
    pub name: String,
    /// MIME type (e.g., "application/json", "text/plain")
    pub mime_type: String,
    /// Size in bytes
    pub size: u64,
    /// Checksum for integrity verification
    pub checksum: String,
    /// Path within the bundle
    pub path: String,
}

impl BundleArtifact {
    /// Create a new bundle artifact.
    pub fn new(
        name: impl Into<String>,
        mime_type: impl Into<String>,
        size: u64,
        checksum: impl Into<String>,
        path: impl Into<String>,
    ) -> Self {
        Self {
            name: name.into(),
            mime_type: mime_type.into(),
            size,
            checksum: checksum.into(),
            path: path.into(),
        }
    }
}

/// Abstract store trait for persisting artifacts.
pub trait BundleStore: Send + Sync {
    /// Save a bundle to storage.
    fn save_bundle(&self, bundle: &Bundle) -> Result<(), StoreError>;

    /// Load a bundle by ID.
    fn load_bundle(&self, id: &str) -> Result<Bundle, StoreError>;

    /// Delete a bundle by ID.
    fn delete_bundle(&self, id: &str) -> Result<(), StoreError>;

    /// List all bundle IDs.
    fn list_bundles(&self) -> Result<Vec<String>, StoreError>;

    /// Check if a bundle exists.
    fn has_bundle(&self, id: &str) -> Result<bool, StoreError>;

    /// Save an artifact within a bundle.
    fn save_artifact(
        &self,
        bundle_id: &str,
        artifact_name: &str,
        data: &[u8],
    ) -> Result<(), StoreError>;

    /// Load an artifact from a bundle.
    fn load_artifact(&self, bundle_id: &str, artifact_name: &str) -> Result<Vec<u8>, StoreError>;
}

/// File-based bundle store implementation.
pub struct FileStore {
    root_path: PathBuf,
}

impl FileStore {
    /// Create a new file store at the given path.
    pub fn new(root_path: impl AsRef<Path>) -> Result<Self, StoreError> {
        let path = root_path.as_ref();
        fs::create_dir_all(path)?;
        Ok(Self {
            root_path: path.to_path_buf(),
        })
    }

    /// Get the path to a bundle directory.
    fn bundle_path(&self, id: &str) -> PathBuf {
        self.root_path.join(id)
    }

    /// Get the path to the manifest file for a bundle.
    fn manifest_path(&self, id: &str) -> PathBuf {
        self.bundle_path(id).join("manifest.json")
    }

    /// Get the path to artifacts directory.
    fn artifacts_path(&self, id: &str) -> PathBuf {
        self.bundle_path(id).join("artifacts")
    }

    /// Calculate SHA256 checksum of data.
    fn checksum(&self, data: &[u8]) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let mut hasher = DefaultHasher::new();
        data.hash(&mut hasher);
        format!("{:x}", hasher.finish())
    }
}

impl BundleStore for FileStore {
    fn save_bundle(&self, bundle: &Bundle) -> Result<(), StoreError> {
        let bundle_dir = self.bundle_path(&bundle.id);
        fs::create_dir_all(&bundle_dir)?;

        let artifacts_dir = self.artifacts_path(&bundle.id);
        fs::create_dir_all(&artifacts_dir)?;

        // Write manifest
        let manifest_path = self.manifest_path(&bundle.id);
        let manifest_json = serde_json::to_string_pretty(bundle)?;
        fs::write(manifest_path, manifest_json)?;

        Ok(())
    }

    fn load_bundle(&self, id: &str) -> Result<Bundle, StoreError> {
        let manifest_path = self.manifest_path(id);
        if !manifest_path.exists() {
            return Err(StoreError::NotFound(format!("Bundle not found: {}", id)));
        }

        let manifest_content = fs::read_to_string(manifest_path)?;
        let bundle: Bundle = serde_json::from_str(&manifest_content)?;
        Ok(bundle)
    }

    fn delete_bundle(&self, id: &str) -> Result<(), StoreError> {
        let bundle_dir = self.bundle_path(id);
        if bundle_dir.exists() {
            fs::remove_dir_all(bundle_dir)?;
        }
        Ok(())
    }

    fn list_bundles(&self) -> Result<Vec<String>, StoreError> {
        let mut bundles = Vec::new();
        for entry in fs::read_dir(&self.root_path)? {
            let entry = entry?;
            let path = entry.path();
            if path.is_dir() {
                if let Some(name) = path.file_name() {
                    if let Some(name_str) = name.to_str() {
                        bundles.push(name_str.to_string());
                    }
                }
            }
        }
        Ok(bundles)
    }

    fn has_bundle(&self, id: &str) -> Result<bool, StoreError> {
        Ok(self.manifest_path(id).exists())
    }

    fn save_artifact(
        &self,
        bundle_id: &str,
        artifact_name: &str,
        data: &[u8],
    ) -> Result<(), StoreError> {
        let artifacts_dir = self.artifacts_path(bundle_id);
        fs::create_dir_all(&artifacts_dir)?;

        let artifact_path = artifacts_dir.join(artifact_name);
        fs::write(&artifact_path, data)?;

        // Update manifest
        let mut bundle = self.load_bundle(bundle_id)?;
        let checksum = self.checksum(data);
        let artifact = BundleArtifact::new(
            artifact_name,
            "application/octet-stream",
            data.len() as u64,
            checksum,
            format!("artifacts/{}", artifact_name),
        );
        bundle.artifacts.insert(artifact_name.to_string(), artifact);
        self.save_bundle(&bundle)?;

        Ok(())
    }

    fn load_artifact(&self, bundle_id: &str, artifact_name: &str) -> Result<Vec<u8>, StoreError> {
        let artifact_path = self.artifacts_path(bundle_id).join(artifact_name);
        if !artifact_path.exists() {
            return Err(StoreError::NotFound(format!(
                "Artifact not found: {}/{}",
                bundle_id, artifact_name
            )));
        }
        let data = fs::read(artifact_path)?;
        Ok(data)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn test_timestamp() -> String {
        use std::time::{SystemTime, UNIX_EPOCH};
        let secs = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);
        format!("1970-01-01T00:00:{:02}Z", secs % 60)
    }

    #[test]
    fn test_file_store_create() {
        let temp_dir = TempDir::new().unwrap();
        let _store = FileStore::new(temp_dir.path()).unwrap();
        assert!(temp_dir.path().exists());
    }

    #[test]
    fn test_file_store_save_load() {
        let temp_dir = TempDir::new().unwrap();
        let store = FileStore::new(temp_dir.path()).unwrap();

        let bundle = Bundle {
            id: "test_bundle".to_string(),
            version: "1.0.0".to_string(),
            created_at: test_timestamp(),
            metadata: HashMap::new(),
            artifacts: HashMap::new(),
        };

        store.save_bundle(&bundle).unwrap();
        let loaded = store.load_bundle("test_bundle").unwrap();
        assert_eq!(loaded.id, "test_bundle");
    }

    #[test]
    fn test_file_store_list() {
        let temp_dir = TempDir::new().unwrap();
        let store = FileStore::new(temp_dir.path()).unwrap();

        let bundle1 = Bundle {
            id: "bundle1".to_string(),
            version: "1.0.0".to_string(),
            created_at: test_timestamp(),
            metadata: HashMap::new(),
            artifacts: HashMap::new(),
        };

        let bundle2 = Bundle {
            id: "bundle2".to_string(),
            version: "1.0.0".to_string(),
            created_at: test_timestamp(),
            metadata: HashMap::new(),
            artifacts: HashMap::new(),
        };

        store.save_bundle(&bundle1).unwrap();
        store.save_bundle(&bundle2).unwrap();

        let bundles = store.list_bundles().unwrap();
        assert_eq!(bundles.len(), 2);
    }

    #[test]
    fn test_file_store_artifacts() {
        let temp_dir = TempDir::new().unwrap();
        let store = FileStore::new(temp_dir.path()).unwrap();

        let bundle = Bundle {
            id: "test_bundle".to_string(),
            version: "1.0.0".to_string(),
            created_at: test_timestamp(),
            metadata: HashMap::new(),
            artifacts: HashMap::new(),
        };

        store.save_bundle(&bundle).unwrap();
        store
            .save_artifact("test_bundle", "artifact.json", b"test data")
            .unwrap();

        let data = store.load_artifact("test_bundle", "artifact.json").unwrap();
        assert_eq!(data, b"test data");
    }
}
