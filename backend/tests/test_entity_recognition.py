"""
Tests for entity recognition functionality.
"""
import pytest
from unittest.mock import Mock, patch
from app.entity_recognition import (
    EntityRecognizer,
    EntityMention,
    EntityExtractionResult,
    DomainDictionary,
    get_entity_recognizer,
    extract_entities_from_transcript
)


@pytest.fixture
def sample_text():
    """Sample text for testing entity recognition."""
    return """
    In this tech talk about Python programming, we'll discuss how Google and Microsoft 
    are using machine learning with TensorFlow and PyTorch. The speaker mentioned that 
    Tesla's autopilot system uses NVIDIA GPUs running at version 3.2.1 for processing.
    You can contact support at help@example.com or visit https://docs.example.com
    for more information about the $500 investment in AI research.
    """


@pytest.fixture
def entity_recognizer():
    """Create entity recognizer instance for testing."""
    return EntityRecognizer()


class TestDomainDictionary:
    """Test domain dictionary functionality."""
    
    def test_domain_dictionary_creation(self):
        """Test creating a domain dictionary."""
        domain_dict = DomainDictionary("test_domain")
        assert domain_dict.domain_name == "test_domain"
        assert domain_dict.entities == {}
        assert len(domain_dict.categories) == 0
    
    def test_add_entity(self):
        """Test adding entities to domain dictionary."""
        domain_dict = DomainDictionary("technology")
        domain_dict.add_entity("Python", ["python", "Python programming"], "language")
        
        assert "Python" in domain_dict.entities
        assert domain_dict.entities["Python"] == ["python", "Python programming"]
        assert "Python" in domain_dict.categories["language"]
    
    def test_get_variations(self):
        """Test getting entity variations."""
        domain_dict = DomainDictionary("technology")
        domain_dict.add_entity("Python", ["python", "Python programming"])
        
        variations = domain_dict.get_variations("Python")
        assert "python" in variations
        assert "Python programming" in variations
    
    def test_search_entity_exact_match(self):
        """Test searching for entities with exact match."""
        domain_dict = DomainDictionary("technology")
        domain_dict.add_entity("Python", ["python", "Python programming"])
        
        result = domain_dict.search_entity("Python")
        assert result is not None
        assert result[0] == "Python"
        assert result[1] == 100  # Exact match
    
    def test_search_entity_fuzzy_match(self):
        """Test searching for entities with fuzzy matching."""
        domain_dict = DomainDictionary("technology")
        domain_dict.add_entity("JavaScript", ["javascript", "js"])
        
        result = domain_dict.search_entity("Javascrip", threshold=70)  # Typo
        assert result is not None
        assert result[0] == "JavaScript"
        assert result[1] >= 70


class TestEntityRecognizer:
    """Test entity recognizer functionality."""
    
    def test_entity_recognizer_initialization(self, entity_recognizer):
        """Test entity recognizer initialization."""
        assert entity_recognizer.nlp is not None
        assert entity_recognizer.phrase_matcher is not None
        assert len(entity_recognizer.domain_dictionaries) > 0
        assert "technology" in entity_recognizer.domain_dictionaries
    
    def test_extract_custom_patterns(self, entity_recognizer, sample_text):
        """Test custom pattern extraction."""
        entities = entity_recognizer.extract_custom_patterns(sample_text)
        
        # Should find version numbers, email, URL, currency
        entity_types = [e.label for e in entities]
        assert "VERSION" in entity_types
        assert "EMAIL" in entity_types
        assert "URL" in entity_types
        assert "CURRENCY" in entity_types
    
    def test_extract_spacy_entities(self, entity_recognizer, sample_text):
        """Test spaCy NER extraction."""
        entities = entity_recognizer.extract_spacy_entities(sample_text)
        
        # Should find organizations, persons, etc.
        assert len(entities) > 0
        entity_labels = [e.label for e in entities]
        assert any(label in ["ORG", "PERSON", "GPE"] for label in entity_labels)
    
    def test_extract_domain_entities(self, entity_recognizer, sample_text):
        """Test domain-specific entity extraction."""
        entities = entity_recognizer.extract_domain_entities(sample_text)
        
        # Should find technology companies
        entity_texts = [e.text.lower() for e in entities]
        assert any("google" in text for text in entity_texts)
        assert any("microsoft" in text for text in entity_texts)
    
    def test_extract_fuzzy_entities(self, entity_recognizer):
        """Test fuzzy entity extraction with transcription errors."""
        # Text with deliberate transcription errors
        fuzzy_text = "I'm using Pyton for machine lerning with Goggle Cloud"
        
        entities = entity_recognizer.extract_fuzzy_entities(fuzzy_text, threshold=75)
        
        # Should match despite typos
        canonical_names = [e.canonical_name for e in entities if e.canonical_name]
        assert any("Python" in name for name in canonical_names)
        assert any("Google" in name for name in canonical_names)
    
    def test_merge_overlapping_entities(self, entity_recognizer):
        """Test merging overlapping entity mentions."""
        entities = [
            EntityMention("Google", "ORG", 0, 6, 0.9),
            EntityMention("Google Cloud", "TECH", 0, 12, 0.8),  # Overlapping
            EntityMention("Microsoft", "ORG", 20, 29, 0.9)
        ]
        
        merged = entity_recognizer.merge_overlapping_entities(entities)
        
        # Should prefer higher confidence entity
        assert len(merged) == 2
        assert merged[0].text == "Google"  # Higher confidence
        assert merged[1].text == "Microsoft"
    
    @patch('app.entity_recognition.wikipedia.search')
    def test_validate_entity_wikipedia(self, mock_search, entity_recognizer):
        """Test entity validation using Wikipedia."""
        mock_search.return_value = ["Python (programming language)"]
        
        entity = EntityMention("Python", "TECH", 0, 6, 0.8, canonical_name="Python")
        validated = entity_recognizer.validate_entity(entity)
        
        assert validated.confidence >= entity.confidence
        assert validated.external_id is not None
    
    def test_extract_entities_full_pipeline(self, entity_recognizer, sample_text):
        """Test full entity extraction pipeline."""
        result = entity_recognizer.extract_entities(sample_text, validate=False)
        
        assert isinstance(result, EntityExtractionResult)
        assert len(result.entities) > 0
        assert result.confidence_score > 0
        assert result.processing_time > 0
        
        # Check for expected entity types
        entity_labels = [e.label for e in result.entities]
        assert any("DOMAIN_" in label for label in entity_labels)
        assert any(label in ["VERSION", "EMAIL", "URL", "CURRENCY"] for label in entity_labels)


class TestEntityRecognitionIntegration:
    """Test entity recognition integration functions."""
    
    def test_get_entity_recognizer_singleton(self):
        """Test that get_entity_recognizer returns singleton."""
        recognizer1 = get_entity_recognizer()
        recognizer2 = get_entity_recognizer()
        
        assert recognizer1 is recognizer2
    
    def test_extract_entities_from_transcript(self, sample_text):
        """Test transcript entity extraction function."""
        result = extract_entities_from_transcript(sample_text)
        
        assert isinstance(result, EntityExtractionResult)
        assert len(result.entities) > 0
    
    def test_entity_extraction_empty_text(self):
        """Test entity extraction with empty text."""
        result = extract_entities_from_transcript("")
        
        assert isinstance(result, EntityExtractionResult)
        assert len(result.entities) == 0
    
    def test_entity_extraction_short_text(self):
        """Test entity extraction with very short text."""
        result = extract_entities_from_transcript("Hi")
        
        assert isinstance(result, EntityExtractionResult)
        # May or may not find entities in very short text


class TestEntityMention:
    """Test EntityMention data class."""
    
    def test_entity_mention_creation(self):
        """Test creating EntityMention."""
        entity = EntityMention(
            text="Python",
            label="TECH",
            start=0,
            end=6,
            confidence=0.9,
            canonical_name="Python",
            context="discussing Python programming"
        )
        
        assert entity.text == "Python"
        assert entity.label == "TECH"
        assert entity.start == 0
        assert entity.end == 6
        assert entity.confidence == 0.9
        assert entity.canonical_name == "Python"
        assert entity.context == "discussing Python programming"


class TestEntityExtractionResult:
    """Test EntityExtractionResult data class."""
    
    def test_extraction_result_creation(self):
        """Test creating EntityExtractionResult."""
        entities = [
            EntityMention("Python", "TECH", 0, 6, 0.9),
            EntityMention("Google", "ORG", 10, 16, 0.8)
        ]
        
        result = EntityExtractionResult(
            entities=entities,
            confidence_score=0.85,
            processing_time=1.5
        )
        
        assert len(result.entities) == 2
        assert result.confidence_score == 0.85
        assert result.processing_time == 1.5


@pytest.mark.integration
class TestEntityRecognitionPerformance:
    """Test entity recognition performance."""
    
    def test_large_text_processing(self, entity_recognizer):
        """Test processing large text efficiently."""
        # Create large text (simulate long transcript)
        large_text = " ".join([
            "Python is a programming language developed by Google and Microsoft.",
            "Machine learning frameworks like TensorFlow and PyTorch are popular.",
            "Tesla uses NVIDIA GPUs for autonomous driving.",
        ] * 100)  # Repeat 100 times
        
        result = entity_recognizer.extract_entities(large_text, validate=False)
        
        # Should complete in reasonable time
        assert result.processing_time < 30.0  # Less than 30 seconds
        assert len(result.entities) > 0
    
    def test_concurrent_processing(self, entity_recognizer):
        """Test that entity recognizer handles concurrent access."""
        import threading
        import time
        
        results = []
        
        def extract_entities():
            text = "Python programming with TensorFlow and Google Cloud"
            result = entity_recognizer.extract_entities(text, validate=False)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=extract_entities)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All threads should have completed successfully
        assert len(results) == 5
        for result in results:
            assert isinstance(result, EntityExtractionResult)
            assert len(result.entities) > 0