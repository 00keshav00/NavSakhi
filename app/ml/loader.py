import os
import json
import hashlib
import logging
import threading
from pathlib import Path
from typing import Tuple, Any, Dict
import joblib

logger = logging.getLogger("SafeSheMLLoader")

_cache_lock = threading.Lock()


class MLArtifactSecurityError(Exception):
    """Raised when an ML artifact fails security, existence, or integrity checks."""
    pass


class SafeMLArtifactLoader:
    """
    Secure loader for production ML artifacts.
    Enforces:
    - Fixed, trusted internal path resolution
    - Non-configurable, zero user-supplied file path injection
    - SHA-256 integrity verification against model_manifest.json
    - Strict fail-closed semantics (no silent degradation)
    """
    
    # Canonical trusted directory relative to repository root
    TRUSTED_MODELS_DIR = Path(__file__).resolve().parent / "Hack" / "ml" / "models"
    _cached_artifacts = None

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the in-memory cached artifacts (primarily for test isolation)."""
        with _cache_lock:
            cls._cached_artifacts = None
    
    @classmethod
    def get_trusted_dir(cls) -> Path:
        return cls.TRUSTED_MODELS_DIR

    @classmethod
    def compute_sha256(cls, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def load_manifest(cls) -> Dict[str, Any]:
        manifest_path = cls.TRUSTED_MODELS_DIR / "model_manifest.json"
        if not manifest_path.exists():
            raise MLArtifactSecurityError(f"Model manifest missing at trusted location: {manifest_path}")
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise MLArtifactSecurityError(f"Failed to read model manifest: {e}") from e

    @classmethod
    def load_feature_metadata(cls) -> Dict[str, Any]:
        meta_path = cls.TRUSTED_MODELS_DIR / "feature_metadata.json"
        if not meta_path.exists():
            raise MLArtifactSecurityError(f"Feature metadata missing at trusted location: {meta_path}")
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise MLArtifactSecurityError(f"Failed to read feature metadata: {e}") from e

    @classmethod
    def _do_load_artifacts(cls, verify_checksum: bool = True) -> Tuple[Any, Any, Dict[str, Any]]:
        manifest = cls.load_manifest()
        
        model_path = cls.TRUSTED_MODELS_DIR / "best_model.pkl"
        preprocessor_path = cls.TRUSTED_MODELS_DIR / "preprocessing_pipeline.pkl"
        
        if not model_path.exists():
            raise MLArtifactSecurityError(f"Model artifact missing: {model_path}")
        if not preprocessor_path.exists():
            raise MLArtifactSecurityError(f"Preprocessor artifact missing: {preprocessor_path}")
            
        if verify_checksum:
            expected_model_hash = manifest.get("sha256_model")
            expected_prep_hash = manifest.get("sha256_preprocessor")
            
            if not expected_model_hash or not expected_prep_hash:
                raise MLArtifactSecurityError("Model manifest is missing SHA-256 hash entries.")
                
            actual_model_hash = cls.compute_sha256(model_path)
            if actual_model_hash != expected_model_hash:
                raise MLArtifactSecurityError(
                    f"Model artifact SHA-256 mismatch! Expected: {expected_model_hash}, Actual: {actual_model_hash}"
                )
                
            actual_prep_hash = cls.compute_sha256(preprocessor_path)
            if actual_prep_hash != expected_prep_hash:
                raise MLArtifactSecurityError(
                    f"Preprocessor artifact SHA-256 mismatch! Expected: {expected_prep_hash}, Actual: {actual_prep_hash}"
                )
                
            logger.info("Artifact checksums verified successfully against manifest.")
            
        try:
            model = joblib.load(model_path)
            preprocessor = joblib.load(preprocessor_path)
        except Exception as e:
            raise MLArtifactSecurityError(f"Deserialization of trusted artifact failed: {e}") from e
            
        return (model, preprocessor, manifest)

    @classmethod
    def load_artifacts(cls, verify_checksum: bool = True, use_cache: bool = True) -> Tuple[Any, Any, Dict[str, Any]]:
        """
        Loads (model, preprocessor, manifest) with strict checksum verification.
        Fails closed if any artifact is missing, unreadable, or tampered.
        When use_cache=True, reuses verified in-memory artifacts to prevent redundant
        re-deserialization and peak memory spikes on constrained instances.
        Thread-safe via double-checked locking.
        """
        if use_cache and cls._cached_artifacts is not None:
            return cls._cached_artifacts

        if not use_cache:
            return cls._do_load_artifacts(verify_checksum=verify_checksum)

        with _cache_lock:
            if cls._cached_artifacts is not None:
                return cls._cached_artifacts
            artifacts = cls._do_load_artifacts(verify_checksum=verify_checksum)
            cls._cached_artifacts = artifacts
            return artifacts
