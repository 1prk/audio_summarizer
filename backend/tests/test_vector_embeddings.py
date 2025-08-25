"""
Tests for vector embeddings functionality.
"""
import pytest
import numpy as np
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from app.vector_embeddings import (
    VectorEmbeddingManager,
    FAISSIndexManager,
    EmbeddingVersionManager,
    EmbeddingResult,
    SimilarityResult,
    EmbeddingMetadata,
    get_embedding_manager,
    generate_transcript_embeddings,
    search_similar_content
)


@pytest.fixture
def sample_documents():
    """Sample documents for embedding tests."""
    return [
        "Python is a powerful programming language for data science and machine learning.",
        "Artificial intelligence and deep learning are transforming technology industries.",
        "Electric vehicles and sustainable energy are the future of transportation.",
        "Cryptocurrency and blockchain technology enable decentralized financial systems.",
        "Climate change requires innovative solutions and renewable energy adoption."
    ]


@pytest.fixture
def sample_document_ids():
    """Sample document IDs."""
    return ["doc1", "doc2", "doc3", "doc4", "doc5"]


@pytest.fixture
def temp_storage_dir():
    """Temporary storage directory for tests."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def embedding_manager(temp_storage_dir):
    """Create embedding manager with temporary storage."""
    return VectorEmbeddingManager(storage_dir=temp_storage_dir)


@pytest.fixture
def sample_embeddings():
    """Sample embedding vectors."""
    np.random.seed(42)  # For reproducible tests
    return np.random.random((5, 384)).astype(np.float32)  # 5 docs, 384 dims


class TestEmbeddingVersionManager:
    """Test embedding version management."""
    
    def test_version_manager_initialization(self, temp_storage_dir):
        """Test version manager initialization."""
        manager = EmbeddingVersionManager(temp_storage_dir)
        assert manager.storage_dir == temp_storage_dir
        assert isinstance(manager.versions, dict)
    
    def test_register_version(self, temp_storage_dir):
        """Test registering new embedding version."""
        manager = EmbeddingVersionManager(temp_storage_dir)
        
        from datetime import datetime
        created_at = datetime.now()
        version_id = manager.register_version(
            model_name="test-model",
            dimension=384,
            num_documents=100,
            created_at=created_at
        )
        
        assert version_id in manager.versions
        version_info = manager.versions[version_id]
        assert version_info["model_name"] == "test-model"
        assert version_info["dimension"] == 384
        assert version_info["num_documents"] == 100
        assert version_info["status"] == "active"
    
    def test_get_latest_version(self, temp_storage_dir):
        """Test getting latest version for model."""
        manager = EmbeddingVersionManager(temp_storage_dir)
        
        from datetime import datetime, timedelta
        
        # Register older version
        old_time = datetime.now() - timedelta(days=1)
        old_version = manager.register_version("test-model", 384, 50, old_time)
        
        # Register newer version
        new_time = datetime.now()
        new_version = manager.register_version("test-model", 384, 100, new_time)
        
        latest = manager.get_latest_version("test-model")
        assert latest == new_version
    
    def test_mark_deprecated(self, temp_storage_dir):
        """Test marking version as deprecated."""
        manager = EmbeddingVersionManager(temp_storage_dir)
        
        from datetime import datetime
        version_id = manager.register_version("test-model", 384, 100, datetime.now())
        
        manager.mark_deprecated(version_id)
        assert manager.versions[version_id]["status"] == "deprecated"


class TestFAISSIndexManager:
    """Test FAISS index management."""
    
    def test_index_manager_initialization(self, temp_storage_dir):
        """Test FAISS index manager initialization."""
        manager = FAISSIndexManager(temp_storage_dir)
        assert manager.storage_dir == temp_storage_dir
        assert isinstance(manager.indexes, dict)
        assert isinstance(manager.document_mappings, dict)
    
    def test_create_flat_index(self, temp_storage_dir, sample_embeddings, sample_document_ids):
        """Test creating flat FAISS index."""
        manager = FAISSIndexManager(temp_storage_dir)
        
        version_id = manager.create_index(
            embeddings=sample_embeddings,
            document_ids=sample_document_ids,
            version_id="test_v1",
            index_type="flat"
        )
        
        assert version_id == "test_v1"
        assert version_id in manager.indexes
        assert version_id in manager.document_mappings
        assert len(manager.document_mappings[version_id]) == len(sample_document_ids)
    
    def test_search_index(self, temp_storage_dir, sample_embeddings, sample_document_ids):
        """Test searching FAISS index."""
        manager = FAISSIndexManager(temp_storage_dir)
        
        # Create index
        version_id = manager.create_index(
            embeddings=sample_embeddings,
            document_ids=sample_document_ids,
            version_id="test_v1"
        )
        
        # Search with first embedding
        query_embedding = sample_embeddings[0]
        results = manager.search(query_embedding, version_id, k=3)
        
        assert len(results) <= 3
        # First result should be the same document (highest similarity)
        if results:
            assert results[0][0] == sample_document_ids[0]
            assert results[0][1] > 0.9  # High similarity
    
    def test_get_embedding(self, temp_storage_dir, sample_embeddings, sample_document_ids):
        """Test retrieving specific embedding."""
        manager = FAISSIndexManager(temp_storage_dir)
        
        # Create index
        version_id = manager.create_index(
            embeddings=sample_embeddings,
            document_ids=sample_document_ids,
            version_id="test_v1"
        )
        
        # Get embedding for first document
        retrieved = manager.get_embedding(sample_document_ids[0], version_id)
        
        assert retrieved is not None
        assert len(retrieved) == sample_embeddings.shape[1]
        # Should be similar to original (after normalization)
        np.testing.assert_allclose(retrieved, sample_embeddings[0], rtol=1e-3)
    
    def test_save_and_load_index(self, temp_storage_dir, sample_embeddings, sample_document_ids):
        """Test saving and loading FAISS index."""
        manager = FAISSIndexManager(temp_storage_dir)
        
        # Create and save index
        version_id = manager.create_index(
            embeddings=sample_embeddings,
            document_ids=sample_document_ids,
            version_id="test_v1"
        )
        
        # Create new manager and load index
        new_manager = FAISSIndexManager(temp_storage_dir)
        success = new_manager.load_index(version_id)
        
        assert success
        assert version_id in new_manager.indexes
        assert version_id in new_manager.document_mappings
        
        # Test that loaded index works
        query_embedding = sample_embeddings[0]
        results = new_manager.search(query_embedding, version_id, k=1)
        assert len(results) > 0


class TestVectorEmbeddingManager:
    """Test vector embedding manager functionality."""
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_embedding_manager_initialization(self, mock_transformer, temp_storage_dir):
        """Test embedding manager initialization."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        manager = VectorEmbeddingManager(storage_dir=temp_storage_dir)
        
        assert manager.storage_dir == temp_storage_dir
        assert isinstance(manager.version_manager, EmbeddingVersionManager)
        assert isinstance(manager.index_manager, FAISSIndexManager)
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_load_model(self, mock_transformer, embedding_manager):
        """Test loading sentence transformer model."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        embedding_manager.load_model("test-model")
        
        mock_transformer.assert_called_with("test-model")
        assert "test-model" in embedding_manager.models
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_generate_embeddings(self, mock_transformer, embedding_manager, 
                                sample_documents, sample_document_ids):
        """Test generating embeddings."""
        # Mock the model
        mock_model = Mock()
        mock_embeddings = np.random.random((len(sample_documents), 384)).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        # Load model
        embedding_manager.load_model("test-model")
        
        # Generate embeddings
        result = embedding_manager.generate_embeddings(
            documents=sample_documents,
            document_ids=sample_document_ids,
            model_name="test-model"
        )
        
        assert isinstance(result, EmbeddingResult)
        assert result.embeddings.shape == (len(sample_documents), 384)
        assert result.num_documents == len(sample_documents)
        assert result.model_name == "test-model"
        assert result.processing_time > 0
    
    def test_generate_embeddings_validation_errors(self, embedding_manager):
        """Test embedding generation validation."""
        # Empty documents
        with pytest.raises(ValueError, match="No documents provided"):
            embedding_manager.generate_embeddings([], [])
        
        # Mismatched lengths
        with pytest.raises(ValueError, match="Number of documents must match"):
            embedding_manager.generate_embeddings(["doc1"], ["id1", "id2"])
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_search_similar(self, mock_transformer, embedding_manager, 
                           sample_documents, sample_document_ids):
        """Test similarity search."""
        # Mock the model
        mock_model = Mock()
        mock_embeddings = np.random.random((len(sample_documents), 384)).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        # Load model and generate embeddings
        embedding_manager.load_model("test-model")
        embedding_manager.generate_embeddings(
            documents=sample_documents,
            document_ids=sample_document_ids,
            model_name="test-model"
        )
        
        # Mock query embedding
        query_embedding = np.random.random((1, 384)).astype(np.float32)
        mock_model.encode.return_value = query_embedding
        
        # Search for similar documents
        result = embedding_manager.search_similar(
            query="Python programming",
            model_name="test-model",
            k=3
        )
        
        assert isinstance(result, SimilarityResult)
        assert len(result.similar_documents) <= 3
        assert result.search_time > 0
        assert result.query_embedding is not None
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_search_similar_by_embedding(self, mock_transformer, embedding_manager,
                                        sample_documents, sample_document_ids):
        """Test similarity search using embedding vector."""
        # Setup similar to previous test
        mock_model = Mock()
        mock_embeddings = np.random.random((len(sample_documents), 384)).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        embedding_manager.load_model("test-model")
        embedding_manager.generate_embeddings(
            documents=sample_documents,
            document_ids=sample_document_ids,
            model_name="test-model"
        )
        
        # Search using embedding vector
        query_embedding = np.random.random(384).astype(np.float32)
        result = embedding_manager.search_similar_by_embedding(
            query_embedding=query_embedding,
            model_name="test-model",
            k=2
        )
        
        assert isinstance(result, SimilarityResult)
        assert len(result.similar_documents) <= 2
    
    def test_calculate_similarity(self, embedding_manager):
        """Test cosine similarity calculation."""
        # Create two similar vectors
        vec1 = np.array([1, 0, 0], dtype=np.float32)
        vec2 = np.array([0.8, 0.6, 0], dtype=np.float32)  # Normalized
        
        similarity = embedding_manager.calculate_similarity(vec1, vec2)
        
        assert 0 <= similarity <= 1
        assert similarity > 0.5  # Should be somewhat similar
    
    def test_reduce_dimensions(self, embedding_manager, sample_embeddings):
        """Test dimensionality reduction."""
        # Test PCA
        reduced_pca = embedding_manager.reduce_dimensions(
            embeddings=sample_embeddings,
            method="pca",
            n_components=2
        )
        
        assert reduced_pca.shape == (5, 2)
        
        # Test UMAP
        reduced_umap = embedding_manager.reduce_dimensions(
            embeddings=sample_embeddings,
            method="umap",
            n_components=2
        )
        
        assert reduced_umap.shape == (5, 2)
    
    def test_reduce_dimensions_invalid_method(self, embedding_manager, sample_embeddings):
        """Test dimensionality reduction with invalid method."""
        with pytest.raises(ValueError, match="Unsupported reduction method"):
            embedding_manager.reduce_dimensions(
                embeddings=sample_embeddings,
                method="invalid"
            )
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_get_model_info(self, mock_transformer, embedding_manager):
        """Test getting model information."""
        mock_model = Mock()
        mock_model.get_sentence_embedding_dimension.return_value = 384
        mock_model.max_seq_length = 512
        mock_transformer.return_value = mock_model
        
        embedding_manager.load_model("test-model")
        
        info = embedding_manager.get_model_info()
        
        assert "test-model" in info
        model_info = info["test-model"]
        assert model_info["dimension"] == 384
        assert model_info["max_sequence_length"] == 512


class TestEmbeddingDataClasses:
    """Test embedding data classes."""
    
    def test_embedding_result_creation(self):
        """Test EmbeddingResult creation."""
        embeddings = np.random.random((5, 384))
        
        result = EmbeddingResult(
            embeddings=embeddings,
            processing_time=1.5,
            model_name="test-model",
            dimension=384,
            num_documents=5
        )
        
        assert result.embeddings.shape == (5, 384)
        assert result.processing_time == 1.5
        assert result.model_name == "test-model"
        assert result.dimension == 384
        assert result.num_documents == 5
    
    def test_similarity_result_creation(self):
        """Test SimilarityResult creation."""
        similar_docs = [("doc1", 0.9), ("doc2", 0.8)]
        query_embedding = np.random.random(384)
        
        result = SimilarityResult(
            similar_documents=similar_docs,
            query_embedding=query_embedding,
            search_time=0.1,
            total_candidates=10
        )
        
        assert len(result.similar_documents) == 2
        assert result.similar_documents[0][1] == 0.9
        assert result.search_time == 0.1
        assert result.total_candidates == 10
    
    def test_embedding_metadata_creation(self):
        """Test EmbeddingMetadata creation."""
        from datetime import datetime
        
        metadata = EmbeddingMetadata(
            document_id="doc1",
            text_hash="abc123",
            embedding_dimension=384,
            model_name="test-model",
            created_at=datetime.now(),
            text_preview="Sample text..."
        )
        
        assert metadata.document_id == "doc1"
        assert metadata.text_hash == "abc123"
        assert metadata.embedding_dimension == 384
        assert metadata.model_name == "test-model"


class TestEmbeddingIntegration:
    """Test embedding integration functions."""
    
    def test_get_embedding_manager_singleton(self):
        """Test that get_embedding_manager returns singleton."""
        manager1 = get_embedding_manager()
        manager2 = get_embedding_manager()
        
        assert manager1 is manager2
    
    @patch('app.vector_embeddings.get_embedding_manager')
    def test_generate_transcript_embeddings(self, mock_get_manager, sample_documents, sample_document_ids):
        """Test transcript embedding generation function."""
        mock_manager = Mock()
        mock_result = EmbeddingResult(
            embeddings=np.random.random((len(sample_documents), 384)),
            processing_time=1.0,
            model_name="test-model",
            dimension=384,
            num_documents=len(sample_documents)
        )
        mock_manager.generate_embeddings.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        result = generate_transcript_embeddings(sample_documents, sample_document_ids)
        
        assert isinstance(result, EmbeddingResult)
        mock_manager.generate_embeddings.assert_called_once()
    
    @patch('app.vector_embeddings.get_embedding_manager')
    def test_search_similar_content(self, mock_get_manager):
        """Test similar content search function."""
        mock_manager = Mock()
        mock_result = SimilarityResult(
            similar_documents=[("doc1", 0.9)],
            query_embedding=np.random.random(384),
            search_time=0.1,
            total_candidates=1
        )
        mock_manager.search_similar.return_value = mock_result
        mock_get_manager.return_value = mock_manager
        
        result = search_similar_content("test query")
        
        assert isinstance(result, SimilarityResult)
        mock_manager.search_similar.assert_called_once()


@pytest.mark.integration
class TestEmbeddingPerformance:
    """Test embedding performance."""
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_large_batch_processing(self, mock_transformer, embedding_manager):
        """Test processing large batches efficiently."""
        # Create large document collection
        large_docs = [f"Document {i} about various topics" for i in range(100)]
        large_ids = [f"doc_{i}" for i in range(100)]
        
        # Mock model
        mock_model = Mock()
        mock_embeddings = np.random.random((100, 384)).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        embedding_manager.load_model("test-model")
        
        result = embedding_manager.generate_embeddings(
            documents=large_docs,
            document_ids=large_ids,
            model_name="test-model",
            batch_size=32
        )
        
        assert result.embeddings.shape == (100, 384)
        assert result.processing_time < 30.0  # Should be reasonably fast
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_concurrent_search(self, mock_transformer, embedding_manager, 
                              sample_documents, sample_document_ids):
        """Test concurrent similarity searches."""
        import threading
        
        # Setup embeddings
        mock_model = Mock()
        mock_embeddings = np.random.random((len(sample_documents), 384)).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        embedding_manager.load_model("test-model")
        embedding_manager.generate_embeddings(
            documents=sample_documents,
            document_ids=sample_document_ids,
            model_name="test-model"
        )
        
        results = []
        
        def search_similar():
            query_embedding = np.random.random(384).astype(np.float32)
            result = embedding_manager.search_similar_by_embedding(
                query_embedding=query_embedding,
                model_name="test-model"
            )
            results.append(result)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=search_similar)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All searches should complete successfully
        assert len(results) == 5
        for result in results:
            assert isinstance(result, SimilarityResult)


class TestEmbeddingEdgeCases:
    """Test edge cases in embedding functionality."""
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_empty_documents(self, mock_transformer, embedding_manager):
        """Test handling empty documents."""
        empty_docs = ["", "   ", "\n\t"]
        doc_ids = ["doc1", "doc2", "doc3"]
        
        mock_model = Mock()
        mock_embeddings = np.random.random((3, 384)).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        embedding_manager.load_model("test-model")
        
        # Should handle empty documents gracefully
        result = embedding_manager.generate_embeddings(
            documents=empty_docs,
            document_ids=doc_ids,
            model_name="test-model"
        )
        
        assert isinstance(result, EmbeddingResult)
        assert result.embeddings.shape[0] == 3
    
    @patch('app.vector_embeddings.SentenceTransformer')
    def test_very_long_documents(self, mock_transformer, embedding_manager):
        """Test handling very long documents."""
        long_doc = "This is a very long document. " * 1000  # Very long text
        
        mock_model = Mock()
        mock_model.max_seq_length = 512
        mock_embeddings = np.random.random((1, 384)).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings
        mock_transformer.return_value = mock_model
        
        embedding_manager.load_model("test-model")
        
        # Should handle long documents (model will truncate)
        result = embedding_manager.generate_embeddings(
            documents=[long_doc],
            document_ids=["doc1"],
            model_name="test-model"
        )
        
        assert isinstance(result, EmbeddingResult)
        assert result.embeddings.shape == (1, 384)
    
    def test_search_without_embeddings(self, embedding_manager):
        """Test searching without any embeddings."""
        with pytest.raises(ValueError, match="No embeddings available"):
            embedding_manager.search_similar("test query", model_name="nonexistent-model")
    
    def test_invalid_embedding_dimensions(self, embedding_manager):
        """Test handling invalid embedding dimensions."""
        # This would typically be caught by the underlying libraries
        # but we test that our code handles it gracefully
        with pytest.raises((ValueError, TypeError)):
            embedding_manager.search_similar_by_embedding(
                query_embedding=np.array([1, 2]),  # Wrong dimensions
                model_name="test-model"
            )