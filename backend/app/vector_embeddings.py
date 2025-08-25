"""
Vector embedding generation and similarity search using sentence-transformers and FAISS.
"""
import os
import logging
import json
import pickle
import hashlib
from typing import List, Dict, Tuple, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import threading
import time

import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from scipy.spatial.distance import cosine

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embeddings: np.ndarray
    processing_time: float
    model_name: str
    dimension: int
    num_documents: int


@dataclass
class SimilarityResult:
    """Result of similarity search."""
    similar_documents: List[Tuple[str, float]]
    query_embedding: np.ndarray
    search_time: float
    total_candidates: int


@dataclass
class EmbeddingMetadata:
    """Metadata for stored embeddings."""
    document_id: str
    text_hash: str
    embedding_dimension: int
    model_name: str
    created_at: datetime
    text_preview: str


class EmbeddingVersionManager:
    """Manage different versions of embeddings."""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        self.versions = {}  # model_name -> version_info
        self._load_version_info()
    
    def _load_version_info(self):
        """Load version information from disk."""
        version_file = os.path.join(self.storage_dir, "versions.json")
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    self.versions = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load version info: {str(e)}")
                self.versions = {}
    
    def _save_version_info(self):
        """Save version information to disk."""
        version_file = os.path.join(self.storage_dir, "versions.json")
        try:
            with open(version_file, 'w') as f:
                json.dump(self.versions, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save version info: {str(e)}")
    
    def register_version(self, model_name: str, dimension: int, 
                        num_documents: int, created_at: datetime):
        """Register a new embedding version."""
        version_id = f"{model_name}_{int(created_at.timestamp())}"
        
        self.versions[version_id] = {
            "model_name": model_name,
            "dimension": dimension,
            "num_documents": num_documents,
            "created_at": created_at.isoformat(),
            "status": "active"
        }
        
        self._save_version_info()
        return version_id
    
    def get_latest_version(self, model_name: str) -> Optional[str]:
        """Get the latest version for a model."""
        matching_versions = [
            (version_id, info) for version_id, info in self.versions.items()
            if info["model_name"] == model_name and info["status"] == "active"
        ]
        
        if not matching_versions:
            return None
        
        # Sort by creation time and return latest
        latest = max(matching_versions, key=lambda x: x[1]["created_at"])
        return latest[0]
    
    def mark_deprecated(self, version_id: str):
        """Mark a version as deprecated."""
        if version_id in self.versions:
            self.versions[version_id]["status"] = "deprecated"
            self._save_version_info()


class FAISSIndexManager:
    """Manage FAISS indexes for fast similarity search."""
    
    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        self.indexes = {}  # version_id -> faiss_index
        self.document_mappings = {}  # version_id -> {internal_id -> document_id}
        self.metadata_store = {}  # version_id -> {document_id -> metadata}
        self._lock = threading.Lock()
        
        os.makedirs(storage_dir, exist_ok=True)
    
    def create_index(self, embeddings: np.ndarray, document_ids: List[str],
                    version_id: str, index_type: str = "flat") -> str:
        """Create a new FAISS index."""
        with self._lock:
            dimension = embeddings.shape[1]
            
            # Create appropriate index type
            if index_type == "flat":
                index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            elif index_type == "ivf":
                # IVF index for larger collections
                nlist = min(100, max(10, embeddings.shape[0] // 10))
                quantizer = faiss.IndexFlatIP(dimension)
                index = faiss.IndexIVFFlat(quantizer, dimension, nlist)
                index.train(embeddings)
            else:
                raise ValueError(f"Unsupported index type: {index_type}")
            
            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)
            
            # Add embeddings to index
            index.add(embeddings)
            
            # Store document mapping
            self.document_mappings[version_id] = {
                i: doc_id for i, doc_id in enumerate(document_ids)
            }
            
            # Store index
            self.indexes[version_id] = index
            
            # Save to disk
            self._save_index(version_id, index)
            self._save_mappings(version_id)
            
            logger.info(f"Created FAISS index {version_id} with {len(document_ids)} documents")
            return version_id
    
    def _save_index(self, version_id: str, index):
        """Save FAISS index to disk."""
        index_path = os.path.join(self.storage_dir, f"{version_id}.index")
        try:
            faiss.write_index(index, index_path)
        except Exception as e:
            logger.error(f"Failed to save index {version_id}: {str(e)}")
    
    def _save_mappings(self, version_id: str):
        """Save document mappings to disk."""
        mapping_path = os.path.join(self.storage_dir, f"{version_id}_mapping.pkl")
        try:
            with open(mapping_path, 'wb') as f:
                pickle.dump(self.document_mappings[version_id], f)
        except Exception as e:
            logger.error(f"Failed to save mappings {version_id}: {str(e)}")
    
    def load_index(self, version_id: str) -> bool:
        """Load FAISS index from disk."""
        index_path = os.path.join(self.storage_dir, f"{version_id}.index")
        mapping_path = os.path.join(self.storage_dir, f"{version_id}_mapping.pkl")
        
        try:
            if os.path.exists(index_path) and os.path.exists(mapping_path):
                # Load index
                index = faiss.read_index(index_path)
                self.indexes[version_id] = index
                
                # Load mappings
                with open(mapping_path, 'rb') as f:
                    self.document_mappings[version_id] = pickle.load(f)
                
                logger.info(f"Loaded FAISS index {version_id}")
                return True
            else:
                logger.warning(f"Index files not found for {version_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to load index {version_id}: {str(e)}")
            return False
    
    def search(self, query_embedding: np.ndarray, version_id: str,
               k: int = 10, threshold: float = 0.5) -> List[Tuple[str, float]]:
        """Search for similar documents."""
        if version_id not in self.indexes:
            if not self.load_index(version_id):
                raise ValueError(f"Index {version_id} not available")
        
        index = self.indexes[version_id]
        mapping = self.document_mappings[version_id]
        
        # Normalize query embedding
        query_embedding = query_embedding.copy()
        faiss.normalize_L2(query_embedding.reshape(1, -1))
        
        # Search
        scores, indices = index.search(query_embedding.reshape(1, -1), k)
        
        # Convert to document IDs and filter by threshold
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1 and score >= threshold:  # -1 indicates no result
                doc_id = mapping.get(idx)
                if doc_id:
                    results.append((doc_id, float(score)))
        
        return results
    
    def get_embedding(self, document_id: str, version_id: str) -> Optional[np.ndarray]:
        """Get embedding for a specific document."""
        if version_id not in self.indexes:
            if not self.load_index(version_id):
                return None
        
        mapping = self.document_mappings[version_id]
        
        # Find internal index for document
        internal_idx = None
        for idx, doc_id in mapping.items():
            if doc_id == document_id:
                internal_idx = idx
                break
        
        if internal_idx is None:
            return None
        
        # Reconstruct embedding from index
        try:
            index = self.indexes[version_id]
            embedding = index.reconstruct(internal_idx)
            return embedding
        except Exception as e:
            logger.error(f"Failed to get embedding for {document_id}: {str(e)}")
            return None


class VectorEmbeddingManager:
    """Main manager for vector embeddings and similarity search."""
    
    def __init__(self, storage_dir: str = "storage/embeddings"):
        """Initialize embedding manager."""
        self.storage_dir = storage_dir
        self.models = {}  # model_name -> SentenceTransformer
        
        # Create storage directories
        os.makedirs(storage_dir, exist_ok=True)
        
        # Initialize components
        self.version_manager = EmbeddingVersionManager(storage_dir)
        self.index_manager = FAISSIndexManager(os.path.join(storage_dir, "indexes"))
        
        # Default models to load
        self._load_default_models()
    
    def _load_default_models(self):
        """Load default sentence transformer models."""
        default_models = [
            "all-MiniLM-L6-v2",      # Fast and good general purpose
            "all-mpnet-base-v2",     # Higher quality but slower
        ]
        
        for model_name in default_models:
            try:
                self.load_model(model_name)
            except Exception as e:
                logger.warning(f"Failed to load default model {model_name}: {str(e)}")
    
    def load_model(self, model_name: str):
        """Load a sentence transformer model."""
        if model_name not in self.models:
            try:
                logger.info(f"Loading sentence transformer model: {model_name}")
                model = SentenceTransformer(model_name)
                self.models[model_name] = model
                logger.info(f"Successfully loaded model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to load model {model_name}: {str(e)}")
                raise
    
    def generate_embeddings(self, documents: List[str], document_ids: List[str],
                          model_name: str = "all-MiniLM-L6-v2",
                          batch_size: int = 32) -> EmbeddingResult:
        """Generate embeddings for a collection of documents."""
        start_time = time.time()
        
        if not documents:
            raise ValueError("No documents provided")
        
        if len(documents) != len(document_ids):
            raise ValueError("Number of documents must match number of document IDs")
        
        # Load model if needed
        if model_name not in self.models:
            self.load_model(model_name)
        
        model = self.models[model_name]
        
        try:
            logger.info(f"Generating embeddings for {len(documents)} documents using {model_name}")
            
            # Generate embeddings in batches
            all_embeddings = []
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                batch_embeddings = model.encode(
                    batch,
                    show_progress_bar=True,
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
                all_embeddings.append(batch_embeddings)
            
            # Combine all embeddings
            embeddings = np.vstack(all_embeddings)
            
            processing_time = time.time() - start_time
            
            # Create version and index
            version_id = self.version_manager.register_version(
                model_name=model_name,
                dimension=embeddings.shape[1],
                num_documents=len(documents),
                created_at=datetime.now()
            )
            
            # Create FAISS index
            self.index_manager.create_index(
                embeddings=embeddings,
                document_ids=document_ids,
                version_id=version_id
            )
            
            result = EmbeddingResult(
                embeddings=embeddings,
                processing_time=processing_time,
                model_name=model_name,
                dimension=embeddings.shape[1],
                num_documents=len(documents)
            )
            
            logger.info(f"Generated embeddings in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Embedding generation failed: {str(e)}")
            raise
    
    def search_similar(self, query: str, model_name: str = "all-MiniLM-L6-v2",
                      k: int = 10, threshold: float = 0.5) -> SimilarityResult:
        """Search for similar documents using text query."""
        start_time = time.time()
        
        # Get latest version for model
        version_id = self.version_manager.get_latest_version(model_name)
        if not version_id:
            raise ValueError(f"No embeddings available for model {model_name}")
        
        # Load model if needed
        if model_name not in self.models:
            self.load_model(model_name)
        
        model = self.models[model_name]
        
        try:
            # Generate query embedding
            query_embedding = model.encode([query], normalize_embeddings=True)[0]
            
            # Search using FAISS
            similar_docs = self.index_manager.search(
                query_embedding=query_embedding,
                version_id=version_id,
                k=k,
                threshold=threshold
            )
            
            search_time = time.time() - start_time
            
            result = SimilarityResult(
                similar_documents=similar_docs,
                query_embedding=query_embedding,
                search_time=search_time,
                total_candidates=len(similar_docs)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise
    
    def search_similar_by_embedding(self, query_embedding: np.ndarray,
                                   model_name: str = "all-MiniLM-L6-v2",
                                   k: int = 10, threshold: float = 0.5) -> SimilarityResult:
        """Search for similar documents using embedding vector."""
        start_time = time.time()
        
        # Get latest version for model
        version_id = self.version_manager.get_latest_version(model_name)
        if not version_id:
            raise ValueError(f"No embeddings available for model {model_name}")
        
        try:
            # Search using FAISS
            similar_docs = self.index_manager.search(
                query_embedding=query_embedding,
                version_id=version_id,
                k=k,
                threshold=threshold
            )
            
            search_time = time.time() - start_time
            
            result = SimilarityResult(
                similar_documents=similar_docs,
                query_embedding=query_embedding,
                search_time=search_time,
                total_candidates=len(similar_docs)
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Similarity search failed: {str(e)}")
            raise
    
    def get_document_embedding(self, document_id: str,
                              model_name: str = "all-MiniLM-L6-v2") -> Optional[np.ndarray]:
        """Get embedding for a specific document."""
        version_id = self.version_manager.get_latest_version(model_name)
        if not version_id:
            return None
        
        return self.index_manager.get_embedding(document_id, version_id)
    
    def calculate_similarity(self, embedding1: np.ndarray,
                           embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings."""
        return 1 - cosine(embedding1, embedding2)
    
    def reduce_dimensions(self, embeddings: np.ndarray,
                         method: str = "umap", n_components: int = 2) -> np.ndarray:
        """Reduce embedding dimensions for visualization."""
        if method == "pca":
            reducer = PCA(n_components=n_components, random_state=42)
        elif method == "tsne":
            reducer = TSNE(n_components=n_components, random_state=42, perplexity=30)
        elif method == "umap":
            reducer = umap.UMAP(n_components=n_components, random_state=42)
        else:
            raise ValueError(f"Unsupported reduction method: {method}")
        
        try:
            reduced = reducer.fit_transform(embeddings)
            return reduced
        except Exception as e:
            logger.error(f"Dimension reduction failed: {str(e)}")
            raise
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        info = {}
        for model_name, model in self.models.items():
            info[model_name] = {
                "dimension": model.get_sentence_embedding_dimension(),
                "max_sequence_length": model.max_seq_length,
                "version_id": self.version_manager.get_latest_version(model_name)
            }
        return info
    
    def cleanup_old_versions(self, keep_versions: int = 3):
        """Clean up old embedding versions."""
        # Implementation for cleaning up old versions
        # This would remove old indexes and embeddings while keeping recent ones
        pass


# Global embedding manager instance
_embedding_manager = None


def get_embedding_manager() -> VectorEmbeddingManager:
    """Get or create global embedding manager instance."""
    global _embedding_manager
    
    if _embedding_manager is None:
        _embedding_manager = VectorEmbeddingManager()
    
    return _embedding_manager


def generate_transcript_embeddings(transcript_texts: List[str],
                                 transcript_ids: List[str],
                                 model_name: str = "all-MiniLM-L6-v2") -> EmbeddingResult:
    """Generate embeddings for transcript collection."""
    manager = get_embedding_manager()
    return manager.generate_embeddings(transcript_texts, transcript_ids, model_name)


def search_similar_content(query: str, k: int = 10) -> SimilarityResult:
    """Search for similar content using text query."""
    manager = get_embedding_manager()
    return manager.search_similar(query, k=k)