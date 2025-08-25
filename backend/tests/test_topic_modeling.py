"""
Tests for topic modeling functionality.
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from app.topic_modeling import (
    TopicModelManager,
    TopicEvolutionTracker,
    TopicInfo,
    DocumentTopic,
    TopicModelingResult,
    get_topic_manager,
    analyze_transcript_topics,
    predict_document_topics
)


@pytest.fixture
def sample_documents():
    """Sample documents for topic modeling tests."""
    return [
        "Python is a popular programming language used for web development and data science. "
        "Many developers choose Python for machine learning projects because of its simplicity.",
        
        "Artificial intelligence and machine learning are transforming the technology industry. "
        "Deep learning models like neural networks are being used in various applications.",
        
        "Electric vehicles are becoming more popular as Tesla leads the automotive industry. "
        "Battery technology and autonomous driving are key innovations in modern cars.",
        
        "Cryptocurrency and blockchain technology are revolutionizing financial systems. "
        "Bitcoin and Ethereum are the most popular digital currencies in the market.",
        
        "Climate change is a major global challenge requiring sustainable energy solutions. "
        "Renewable energy sources like solar and wind power are becoming more efficient."
    ]


@pytest.fixture
def sample_document_ids():
    """Sample document IDs corresponding to sample documents."""
    return ["doc1", "doc2", "doc3", "doc4", "doc5"]


@pytest.fixture
def sample_timestamps():
    """Sample timestamps for documents."""
    base_time = datetime.now() - timedelta(days=10)
    return [base_time + timedelta(days=i) for i in range(5)]


@pytest.fixture
def topic_manager():
    """Create topic model manager for testing."""
    return TopicModelManager()


@pytest.fixture
def evolution_tracker():
    """Create topic evolution tracker for testing."""
    return TopicEvolutionTracker()


class TestTopicEvolutionTracker:
    """Test topic evolution tracking functionality."""
    
    def test_evolution_tracker_initialization(self, evolution_tracker):
        """Test evolution tracker initialization."""
        assert len(evolution_tracker.topic_timeline) == 0
        assert len(evolution_tracker.topic_merges) == 0
        assert len(evolution_tracker.topic_splits) == 0
    
    def test_add_topic_observation(self, evolution_tracker):
        """Test adding topic observations."""
        timestamp = datetime.now()
        evolution_tracker.add_topic_observation(1, timestamp, 0.8)
        
        assert 1 in evolution_tracker.topic_timeline
        assert len(evolution_tracker.topic_timeline[1]) == 1
        assert evolution_tracker.topic_timeline[1][0] == (timestamp, 0.8)
    
    def test_detect_topic_emergence(self, evolution_tracker):
        """Test detecting emerging topics."""
        # Add recent observations
        recent_time = datetime.now() - timedelta(days=3)
        evolution_tracker.add_topic_observation(1, recent_time, 0.5)
        
        # Add old observations
        old_time = datetime.now() - timedelta(days=20)
        evolution_tracker.add_topic_observation(2, old_time, 0.5)
        
        assert evolution_tracker.detect_topic_emergence(1, threshold_days=7)
        assert not evolution_tracker.detect_topic_emergence(2, threshold_days=7)
    
    def test_detect_topic_decline(self, evolution_tracker):
        """Test detecting declining topics."""
        base_time = datetime.now() - timedelta(days=10)
        
        # Add observations showing decline
        evolution_tracker.add_topic_observation(1, base_time, 1.0)  # Peak
        evolution_tracker.add_topic_observation(1, base_time + timedelta(days=5), 0.4)  # Decline
        evolution_tracker.add_topic_observation(1, base_time + timedelta(days=8), 0.3)  # Further decline
        
        assert evolution_tracker.detect_topic_decline(1, threshold_ratio=0.5)
    
    def test_get_topic_trends(self, evolution_tracker):
        """Test getting topic trends."""
        base_time = datetime.now() - timedelta(days=15)
        
        # Add observations showing upward trend
        for i in range(5):
            timestamp = base_time + timedelta(days=i)
            strength = 0.2 + (i * 0.2)  # Increasing strength
            evolution_tracker.add_topic_observation(1, timestamp, strength)
        
        trends = evolution_tracker.get_topic_trends(days_back=20)
        
        assert 1 in trends
        assert trends[1] > 0  # Positive trend


class TestTopicModelManager:
    """Test topic model manager functionality."""
    
    def test_topic_manager_initialization(self, topic_manager):
        """Test topic manager initialization."""
        assert topic_manager.embedding_model is not None
        assert topic_manager.topic_model is not None
        assert isinstance(topic_manager.evolution_tracker, TopicEvolutionTracker)
    
    @patch('app.topic_modeling.SentenceTransformer')
    def test_embedding_model_setup(self, mock_transformer):
        """Test embedding model setup."""
        mock_model = Mock()
        mock_transformer.return_value = mock_model
        
        manager = TopicModelManager()
        
        mock_transformer.assert_called_once()
        assert manager.embedding_model == mock_model
    
    def test_train_topic_model_insufficient_documents(self, topic_manager):
        """Test training with insufficient documents."""
        short_docs = ["Short doc", "Another short"]
        
        with pytest.raises(ValueError, match="Not enough valid documents"):
            topic_manager.train_topic_model(short_docs)
    
    def test_train_topic_model_success(self, topic_manager, sample_documents, 
                                     sample_document_ids, sample_timestamps):
        """Test successful topic model training."""
        result = topic_manager.train_topic_model(
            documents=sample_documents,
            document_ids=sample_document_ids,
            timestamps=sample_timestamps
        )
        
        assert isinstance(result, TopicModelingResult)
        assert len(result.topics) > 0
        assert len(result.document_topics) > 0
        assert result.processing_time > 0
        assert result.coherence_score >= 0
        
        # Check topic info structure
        for topic in result.topics:
            assert isinstance(topic, TopicInfo)
            assert topic.topic_id >= 0
            assert len(topic.keywords) > 0
            assert topic.size > 0
    
    def test_predict_topics_without_training(self, topic_manager):
        """Test predicting topics without training first."""
        with pytest.raises(ValueError, match="Topic model not trained"):
            topic_manager.predict_topics(["Test document"])
    
    def test_predict_topics_after_training(self, topic_manager, sample_documents):
        """Test predicting topics after training."""
        # First train the model
        topic_manager.train_topic_model(sample_documents)
        
        # Then predict on new documents
        new_docs = ["Python machine learning framework for data analysis"]
        predictions = topic_manager.predict_topics(new_docs)
        
        assert len(predictions) == 1
        topic_id, confidence = predictions[0]
        assert isinstance(topic_id, int)
        assert isinstance(confidence, float)
        assert 0 <= confidence <= 1
    
    def test_save_and_load_model(self, topic_manager, sample_documents, tmp_path):
        """Test saving and loading topic models."""
        # Set temporary model directory
        topic_manager.model_dir = str(tmp_path)
        
        # Train model
        topic_manager.train_topic_model(sample_documents)
        
        # Save model
        model_name = "test_model"
        topic_manager.save_model(model_name)
        
        # Create new manager and load model
        new_manager = TopicModelManager(model_dir=str(tmp_path))
        new_manager.load_model(model_name)
        
        # Test that loaded model works
        predictions = new_manager.predict_topics(["Test document about Python"])
        assert len(predictions) == 1
    
    def test_get_emerging_topics(self, topic_manager, sample_documents):
        """Test getting emerging topics."""
        # Train model with timestamps
        timestamps = [datetime.now() - timedelta(days=i) for i in range(len(sample_documents))]
        topic_manager.train_topic_model(sample_documents, timestamps=timestamps)
        
        emerging = topic_manager.get_emerging_topics(threshold_days=30)
        assert isinstance(emerging, list)
    
    def test_get_declining_topics(self, topic_manager, sample_documents):
        """Test getting declining topics."""
        topic_manager.train_topic_model(sample_documents)
        
        declining = topic_manager.get_declining_topics()
        assert isinstance(declining, list)
    
    def test_visualize_topics(self, topic_manager, sample_documents):
        """Test topic visualization."""
        topic_manager.train_topic_model(sample_documents)
        
        html = topic_manager.visualize_topics()
        assert isinstance(html, str)
        assert len(html) > 0


class TestTopicModelingDataClasses:
    """Test topic modeling data classes."""
    
    def test_topic_info_creation(self):
        """Test TopicInfo creation."""
        topic = TopicInfo(
            topic_id=1,
            name="Technology",
            description="Discussion about technology",
            keywords=["python", "programming", "ai"],
            size=10,
            coherence_score=0.8,
            representative_docs=["Python is great"],
            created_at=datetime.now(),
            last_updated=datetime.now()
        )
        
        assert topic.topic_id == 1
        assert topic.name == "Technology"
        assert len(topic.keywords) == 3
        assert topic.coherence_score == 0.8
    
    def test_document_topic_creation(self):
        """Test DocumentTopic creation."""
        doc_topic = DocumentTopic(
            document_id="doc1",
            topic_id=1,
            probability=0.8,
            text="Sample text",
            timestamp=datetime.now()
        )
        
        assert doc_topic.document_id == "doc1"
        assert doc_topic.topic_id == 1
        assert doc_topic.probability == 0.8
    
    def test_topic_modeling_result_creation(self):
        """Test TopicModelingResult creation."""
        topics = [TopicInfo(
            topic_id=1, name="Test", description="Test topic",
            keywords=["test"], size=5, coherence_score=0.7,
            representative_docs=[], created_at=datetime.now(),
            last_updated=datetime.now()
        )]
        
        doc_topics = [DocumentTopic("doc1", 1, 0.8, "text")]
        
        result = TopicModelingResult(
            topics=topics,
            document_topics=doc_topics,
            model_info={"num_topics": 1},
            processing_time=1.5,
            coherence_score=0.7
        )
        
        assert len(result.topics) == 1
        assert len(result.document_topics) == 1
        assert result.processing_time == 1.5


class TestTopicModelingIntegration:
    """Test topic modeling integration functions."""
    
    def test_get_topic_manager_singleton(self):
        """Test that get_topic_manager returns singleton."""
        manager1 = get_topic_manager()
        manager2 = get_topic_manager()
        
        assert manager1 is manager2
    
    def test_analyze_transcript_topics(self, sample_documents, sample_document_ids):
        """Test transcript topic analysis function."""
        result = analyze_transcript_topics(sample_documents, sample_document_ids)
        
        assert isinstance(result, TopicModelingResult)
        assert len(result.topics) > 0
    
    def test_predict_document_topics_untrained(self):
        """Test predicting topics with untrained model."""
        # Reset global manager to ensure clean state
        import app.topic_modeling
        app.topic_modeling._topic_manager = None
        
        with pytest.raises(ValueError):
            predict_document_topics(["Test document"])
    
    def test_analyze_transcript_topics_empty_input(self):
        """Test topic analysis with empty input."""
        with pytest.raises(ValueError):
            analyze_transcript_topics([], [])
    
    def test_analyze_transcript_topics_mismatched_input(self):
        """Test topic analysis with mismatched input lengths."""
        with pytest.raises(ValueError):
            analyze_transcript_topics(["doc1"], ["id1", "id2"])


@pytest.mark.integration
class TestTopicModelingPerformance:
    """Test topic modeling performance."""
    
    def test_large_document_collection(self, topic_manager):
        """Test processing large document collection."""
        # Create large collection of documents
        large_collection = []
        for i in range(50):
            doc = f"Document {i} about technology and programming. " * 10
            large_collection.append(doc)
        
        result = topic_manager.train_topic_model(large_collection)
        
        # Should complete in reasonable time
        assert result.processing_time < 60.0  # Less than 1 minute
        assert len(result.topics) > 0
    
    def test_incremental_topic_updates(self, topic_manager, sample_documents):
        """Test incremental topic model updates."""
        # Train initial model
        initial_result = topic_manager.train_topic_model(sample_documents[:3])
        initial_topics = len(initial_result.topics)
        
        # Add more documents
        extended_result = topic_manager.train_topic_model(sample_documents)
        extended_topics = len(extended_result.topics)
        
        # Should handle both scenarios
        assert extended_topics >= initial_topics
    
    def test_concurrent_topic_prediction(self, topic_manager, sample_documents):
        """Test concurrent topic prediction."""
        import threading
        
        # Train model first
        topic_manager.train_topic_model(sample_documents)
        
        results = []
        
        def predict_topics():
            docs = ["Python programming and machine learning"]
            result = topic_manager.predict_topics(docs)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=predict_topics)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should complete successfully
        assert len(results) == 5
        for result in results:
            assert len(result) == 1
            assert isinstance(result[0], tuple)


class TestTopicModelingEdgeCases:
    """Test edge cases in topic modeling."""
    
    def test_very_short_documents(self, topic_manager):
        """Test handling very short documents."""
        short_docs = ["Hi", "Hello", "Good", "Nice", "Cool"] * 10  # Repeat to meet minimum
        
        # Should handle gracefully
        result = topic_manager.train_topic_model(short_docs)
        assert isinstance(result, TopicModelingResult)
    
    def test_duplicate_documents(self, topic_manager):
        """Test handling duplicate documents."""
        duplicate_docs = ["Python programming"] * 20
        
        result = topic_manager.train_topic_model(duplicate_docs)
        assert isinstance(result, TopicModelingResult)
    
    def test_mixed_language_content(self, topic_manager):
        """Test handling mixed language content."""
        mixed_docs = [
            "Python programming is great for data science",
            "Machine learning algorithms are powerful",
            "Technology advancement in artificial intelligence",
            "Software development best practices",
            "Computer science fundamentals"
        ]
        
        result = topic_manager.train_topic_model(mixed_docs)
        assert isinstance(result, TopicModelingResult)
    
    def test_special_characters_and_unicode(self, topic_manager):
        """Test handling special characters (converted to ASCII as per requirements)."""
        special_docs = [
            "Programming with special chars: @#$%^&*()",
            "Numbers and symbols: 123 456 789",
            "Email addresses: test@example.com",
            "URLs: https://www.example.com",
            "Mixed content with various symbols"
        ]
        
        result = topic_manager.train_topic_model(special_docs)
        assert isinstance(result, TopicModelingResult)