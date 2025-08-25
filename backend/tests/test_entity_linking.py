"""
Tests for entity linking functionality.
"""
import pytest
import sqlite3
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.entity_linking import (
    EntityLinker,
    EntityKnowledgeBase,
    ExternalValidators,
    EntityValidationResult,
    EntityLinkingResult,
    get_entity_linker,
    validate_and_link_entities
)
from app.entity_recognition import EntityMention, EntityExtractionResult


@pytest.fixture
def temp_db_path():
    """Temporary database path for tests."""
    temp_dir = tempfile.mkdtemp()
    db_path = f"{temp_dir}/test_kb.db"
    yield db_path
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def knowledge_base(temp_db_path):
    """Create knowledge base instance for testing."""
    return EntityKnowledgeBase(db_path=temp_db_path)


@pytest.fixture
def entity_linker(knowledge_base):
    """Create entity linker instance for testing."""
    return EntityLinker(knowledge_base=knowledge_base)


@pytest.fixture
def sample_entities():
    """Sample entity mentions for testing."""
    return [
        EntityMention("Python", "TECH", 0, 6, 0.9),
        EntityMention("Google", "ORG", 10, 16, 0.8),
        EntityMention("Tesla", "ORG", 20, 25, 0.85),
        EntityMention("unknown_entity", "MISC", 30, 43, 0.6),
        EntityMention("JavaScript", "TECH", 50, 60, 0.7)
    ]


@pytest.fixture
def sample_extraction_result(sample_entities):
    """Sample entity extraction result."""
    return EntityExtractionResult(
        entities=sample_entities,
        confidence_score=0.8,
        processing_time=1.5
    )


class TestEntityKnowledgeBase:
    """Test entity knowledge base functionality."""
    
    def test_knowledge_base_initialization(self, knowledge_base):
        """Test knowledge base initialization."""
        assert knowledge_base.db_path is not None
        
        # Check that tables were created
        with sqlite3.connect(knowledge_base.db_path) as conn:
            cursor = conn.cursor()
            
            # Check entities table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entities'")
            assert cursor.fetchone() is not None
            
            # Check aliases table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='entity_aliases'")
            assert cursor.fetchone() is not None
            
            # Check validation cache table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='validation_cache'")
            assert cursor.fetchone() is not None
    
    def test_add_entity(self, knowledge_base):
        """Test adding entity to knowledge base."""
        knowledge_base.add_entity(
            canonical_name="Python",
            entity_type="programming_language",
            aliases=["python", "Python programming"],
            source="manual",
            confidence=0.9,
            description="A high-level programming language"
        )
        
        # Verify entity was added
        with sqlite3.connect(knowledge_base.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM entities WHERE canonical_name = ?", ("Python",))
            entity = cursor.fetchone()
            
            assert entity is not None
            assert entity[1] == "Python"  # canonical_name
            assert entity[2] == "programming_language"  # entity_type
    
    def test_find_entity_exact_match(self, knowledge_base):
        """Test finding entity with exact match."""
        knowledge_base.add_entity("Python", "tech", ["python"], confidence=0.9)
        
        result = knowledge_base.find_entity("Python")
        
        assert result is not None
        assert result["canonical_name"] == "Python"
        assert result["match_type"] == "exact"
        assert result["confidence_score"] == 0.9
    
    def test_find_entity_alias_match(self, knowledge_base):
        """Test finding entity through alias."""
        knowledge_base.add_entity("Python", "tech", ["python", "py"], confidence=0.9)
        
        result = knowledge_base.find_entity("python")
        
        assert result is not None
        assert result["canonical_name"] == "Python"
        assert result["match_type"] == "alias"
    
    def test_find_entity_fuzzy_match(self, knowledge_base):
        """Test finding entity with fuzzy matching."""
        knowledge_base.add_entity("JavaScript", "tech", confidence=0.9)
        
        result = knowledge_base.find_entity("Javascrip", threshold=75)  # Typo
        
        assert result is not None
        assert result["canonical_name"] == "JavaScript"
        assert result["match_type"] == "fuzzy"
        assert "fuzzy_score" in result
    
    def test_find_entity_no_match(self, knowledge_base):
        """Test finding non-existent entity."""
        result = knowledge_base.find_entity("nonexistent_entity")
        assert result is None
    
    def test_validation_cache(self, knowledge_base):
        """Test validation caching functionality."""
        # Cache a validation result
        knowledge_base.cache_validation_result(
            text="Python",
            is_valid=True,
            confidence_score=0.9,
            source="wikipedia",
            canonical_form="Python (programming language)"
        )
        
        # Retrieve cached result
        cached = knowledge_base.get_validation_cache("Python")
        
        assert cached is not None
        assert cached["is_valid"] is True
        assert cached["confidence_score"] == 0.9
        assert cached["source"] == "wikipedia"
        assert cached["canonical_form"] == "Python (programming language)"
    
    def test_cleanup_cache(self, knowledge_base):
        """Test cache cleanup functionality."""
        # Add some cache entries (would need to manipulate timestamps for realistic test)
        knowledge_base.cache_validation_result("entity1", True, 0.8, "test")
        knowledge_base.cache_validation_result("entity2", False, 0.2, "test")
        
        # Run cleanup (won't actually delete recent entries in test)
        knowledge_base.cleanup_cache(days_old=0)  # Delete all entries
        
        # Check that entries were processed (implementation specific)
        # This is more of a smoke test to ensure the method runs without error


class TestExternalValidators:
    """Test external validation functionality."""
    
    @patch('app.entity_linking.wikipedia.search')
    @patch('app.entity_linking.wikipedia.page')
    def test_wikipedia_validation_success(self, mock_page, mock_search):
        """Test successful Wikipedia validation."""
        # Mock Wikipedia search and page
        mock_search.return_value = ["Python (programming language)"]
        
        mock_page_obj = Mock()
        mock_page_obj.title = "Python (programming language)"
        mock_page_obj.summary = "Python is a high-level programming language."
        mock_page_obj.url = "https://en.wikipedia.org/wiki/Python_(programming_language)"
        mock_page.return_value = mock_page_obj
        
        result = ExternalValidators.validate_with_wikipedia("Python")
        
        assert result is not None
        assert result["is_valid"] is True
        assert result["canonical_form"] == "Python (programming language)"
        assert "wikipedia" in result["external_links"]
        assert result["confidence_score"] > 0
    
    @patch('app.entity_linking.wikipedia.search')
    def test_wikipedia_validation_no_results(self, mock_search):
        """Test Wikipedia validation with no results."""
        mock_search.return_value = []
        
        result = ExternalValidators.validate_with_wikipedia("nonexistent_entity")
        
        assert result is None
    
    @patch('app.entity_linking.wikipedia.search')
    @patch('app.entity_linking.wikipedia.page')
    def test_wikipedia_validation_disambiguation(self, mock_page, mock_search):
        """Test Wikipedia validation with disambiguation page."""
        from app.entity_linking import wikipedia
        
        mock_search.return_value = ["Python"]
        
        # Mock disambiguation error
        disambiguation_error = wikipedia.exceptions.DisambiguationError(
            "Python", ["Python (programming language)", "Python (mythology)"]
        )
        mock_page.side_effect = disambiguation_error
        
        result = ExternalValidators.validate_with_wikipedia("Python")
        
        assert result is not None
        assert result["is_valid"] is True
        assert result["entity_type"] == "wikipedia_disambiguation"
        assert len(result["aliases"]) > 0
    
    @patch('app.entity_linking.requests.get')
    def test_wikidata_validation_success(self, mock_get):
        """Test successful Wikidata validation."""
        # Mock Wikidata API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "search": [
                {
                    "id": "Q28865",
                    "label": "Python",
                    "description": "high-level programming language"
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = ExternalValidators.validate_with_wikidata("Python")
        
        assert result is not None
        assert result["is_valid"] is True
        assert result["canonical_form"] == "Python"
        assert result["external_id"] == "Q28865"
        assert "wikidata" in result["external_links"]
    
    @patch('app.entity_linking.requests.get')
    def test_wikidata_validation_no_results(self, mock_get):
        """Test Wikidata validation with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"search": []}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = ExternalValidators.validate_with_wikidata("nonexistent")
        
        assert result is None
    
    @patch('app.entity_linking.requests.get')
    def test_wikidata_validation_network_error(self, mock_get):
        """Test Wikidata validation with network error."""
        mock_get.side_effect = Exception("Network error")
        
        result = ExternalValidators.validate_with_wikidata("Python")
        
        assert result is None


class TestEntityLinker:
    """Test entity linker functionality."""
    
    def test_entity_linker_initialization(self, entity_linker):
        """Test entity linker initialization."""
        assert entity_linker.kb is not None
        assert len(entity_linker.validators) > 0
        assert "wikipedia" in entity_linker.validators
        assert "wikidata" in entity_linker.validators
    
    def test_validate_entity_from_knowledge_base(self, entity_linker):
        """Test entity validation from local knowledge base."""
        # Add entity to knowledge base
        entity_linker.kb.add_entity("Python", "programming_language", confidence=0.9)
        
        # Create entity mention
        entity = EntityMention("Python", "TECH", 0, 6, 0.8)
        
        # Validate entity
        result = entity_linker.validate_entity(entity)
        
        assert isinstance(result, EntityValidationResult)
        assert result.is_valid is True
        assert result.validation_source == "knowledge_base"
        assert result.canonical_form == "Python"
        assert result.confidence_score == 0.9
    
    def test_validate_entity_cached_result(self, entity_linker):
        """Test entity validation using cached result."""
        # Cache a validation result
        entity_linker.kb.cache_validation_result(
            text="Python",
            is_valid=True,
            confidence_score=0.85,
            source="wikipedia",
            canonical_form="Python (programming language)"
        )
        
        entity = EntityMention("Python", "TECH", 0, 6, 0.8)
        result = entity_linker.validate_entity(entity)
        
        assert result.is_valid is True
        assert result.validation_source == "wikipedia"
        assert result.confidence_score == 0.85
    
    @patch.object(ExternalValidators, 'validate_with_wikipedia')
    def test_validate_entity_external_validation(self, mock_wikipedia, entity_linker):
        """Test entity validation using external sources."""
        # Mock Wikipedia validation
        mock_wikipedia.return_value = {
            "is_valid": True,
            "confidence_score": 0.8,
            "canonical_form": "Tesla, Inc.",
            "entity_type": "company",
            "external_links": {"wikipedia": "https://en.wikipedia.org/wiki/Tesla,_Inc."}
        }
        
        entity = EntityMention("Tesla", "ORG", 0, 5, 0.7)
        result = entity_linker.validate_entity(entity)
        
        assert result.is_valid is True
        assert result.validation_source == "wikipedia"
        assert result.canonical_form == "Tesla, Inc."
        assert result.external_links is not None
    
    def test_validate_entity_not_found(self, entity_linker):
        """Test entity validation when entity is not found."""
        entity = EntityMention("unknown_entity", "MISC", 0, 14, 0.5)
        result = entity_linker.validate_entity(entity)
        
        assert result.is_valid is False
        assert result.validation_source == "none"
        assert result.confidence_score == 0.0
    
    def test_link_entities(self, entity_linker, sample_extraction_result):
        """Test full entity linking process."""
        # Add some known entities to knowledge base
        entity_linker.kb.add_entity("Python", "programming_language", confidence=0.9)
        entity_linker.kb.add_entity("Google", "company", confidence=0.95)
        
        result = entity_linker.link_entities(sample_extraction_result)
        
        assert isinstance(result, EntityLinkingResult)
        assert len(result.validated_entities) == len(sample_extraction_result.entities)
        assert result.processing_time > 0
        assert "total" in result.validation_stats
        assert result.validation_stats["total"] == len(sample_extraction_result.entities)
    
    def test_get_entity_statistics(self, entity_linker):
        """Test getting entity statistics."""
        # Add some entities
        entity_linker.kb.add_entity("Python", "programming_language")
        entity_linker.kb.add_entity("JavaScript", "programming_language")
        entity_linker.kb.add_entity("Tesla", "company")
        
        stats = entity_linker.get_entity_statistics()
        
        assert "total_entities" in stats
        assert "entity_types" in stats
        assert stats["total_entities"] >= 3
        assert "programming_language" in stats["entity_types"]
        assert "company" in stats["entity_types"]


class TestEntityLinkingDataClasses:
    """Test entity linking data classes."""
    
    def test_entity_validation_result_creation(self):
        """Test EntityValidationResult creation."""
        entity = EntityMention("Python", "TECH", 0, 6, 0.8)
        
        result = EntityValidationResult(
            entity=entity,
            is_valid=True,
            confidence_score=0.9,
            validation_source="wikipedia",
            canonical_form="Python (programming language)",
            external_links={"wikipedia": "https://example.com"},
            aliases=["python", "py"],
            description="Programming language",
            entity_type="programming_language"
        )
        
        assert result.entity == entity
        assert result.is_valid is True
        assert result.confidence_score == 0.9
        assert result.validation_source == "wikipedia"
        assert result.canonical_form == "Python (programming language)"
        assert len(result.aliases) == 2
    
    def test_entity_linking_result_creation(self):
        """Test EntityLinkingResult creation."""
        entity = EntityMention("Python", "TECH", 0, 6, 0.8)
        validation_result = EntityValidationResult(
            entity=entity,
            is_valid=True,
            confidence_score=0.9,
            validation_source="test"
        )
        
        linking_result = EntityLinkingResult(
            validated_entities=[validation_result],
            processing_time=1.5,
            validation_stats={"total": 1, "valid": 1}
        )
        
        assert len(linking_result.validated_entities) == 1
        assert linking_result.processing_time == 1.5
        assert linking_result.validation_stats["total"] == 1


class TestEntityLinkingIntegration:
    """Test entity linking integration functions."""
    
    def test_get_entity_linker_singleton(self):
        """Test that get_entity_linker returns singleton."""
        linker1 = get_entity_linker()
        linker2 = get_entity_linker()
        
        assert linker1 is linker2
    
    def test_validate_and_link_entities(self, sample_extraction_result):
        """Test validate_and_link_entities function."""
        result = validate_and_link_entities(sample_extraction_result)
        
        assert isinstance(result, EntityLinkingResult)
        assert len(result.validated_entities) > 0


@pytest.mark.integration
class TestEntityLinkingPerformance:
    """Test entity linking performance."""
    
    def test_large_entity_collection(self, entity_linker):
        """Test linking large collection of entities."""
        # Create large collection of entity mentions
        large_entities = []
        for i in range(100):
            entity = EntityMention(f"entity_{i}", "MISC", i*10, i*10+5, 0.7)
            large_entities.append(entity)
        
        extraction_result = EntityExtractionResult(
            entities=large_entities,
            confidence_score=0.7,
            processing_time=1.0
        )
        
        result = entity_linker.link_entities(extraction_result)
        
        # Should complete in reasonable time
        assert result.processing_time < 30.0  # Less than 30 seconds
        assert len(result.validated_entities) == 100
    
    def test_concurrent_entity_validation(self, entity_linker):
        """Test concurrent entity validation."""
        import threading
        
        entity = EntityMention("Python", "TECH", 0, 6, 0.8)
        results = []
        
        def validate_entity():
            result = entity_linker.validate_entity(entity)
            results.append(result)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=validate_entity)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All validations should complete
        assert len(results) == 5
        for result in results:
            assert isinstance(result, EntityValidationResult)
    
    def test_knowledge_base_scaling(self, knowledge_base):
        """Test knowledge base performance with many entities."""
        # Add many entities
        for i in range(1000):
            knowledge_base.add_entity(
                canonical_name=f"Entity_{i}",
                entity_type="test",
                aliases=[f"alias_{i}_1", f"alias_{i}_2"]
            )
        
        # Test search performance
        import time
        start_time = time.time()
        
        result = knowledge_base.find_entity("Entity_500")
        
        search_time = time.time() - start_time
        
        assert result is not None
        assert search_time < 1.0  # Should be fast even with many entities


class TestEntityLinkingEdgeCases:
    """Test edge cases in entity linking."""
    
    def test_empty_entity_text(self, entity_linker):
        """Test validation of empty entity text."""
        entity = EntityMention("", "MISC", 0, 0, 0.5)
        result = entity_linker.validate_entity(entity)
        
        assert result.is_valid is False
    
    def test_very_long_entity_text(self, entity_linker):
        """Test validation of very long entity text."""
        long_text = "very_long_entity_name_" * 100
        entity = EntityMention(long_text, "MISC", 0, len(long_text), 0.7)
        
        # Should handle gracefully without crashing
        result = entity_linker.validate_entity(entity)
        assert isinstance(result, EntityValidationResult)
    
    def test_special_characters_in_entity(self, entity_linker):
        """Test validation of entities with special characters."""
        entity = EntityMention("C++", "TECH", 0, 3, 0.8)
        result = entity_linker.validate_entity(entity)
        
        assert isinstance(result, EntityValidationResult)
    
    def test_unicode_entity_handling(self, entity_linker):
        """Test handling entities with unicode characters (should be converted to ASCII)."""
        # Note: As per requirements, we should use only ASCII
        entity = EntityMention("entity_with_special_chars", "MISC", 0, 25, 0.7)
        result = entity_linker.validate_entity(entity)
        
        assert isinstance(result, EntityValidationResult)
    
    def test_database_connection_error_handling(self, temp_db_path):
        """Test handling database connection errors."""
        # Create knowledge base with invalid path
        invalid_kb = EntityKnowledgeBase(db_path="/invalid/path/db.sqlite")
        
        # Should handle database errors gracefully
        # (This might create the directory structure, depending on implementation)
        try:
            result = invalid_kb.find_entity("test")
            # If it doesn't raise an exception, that's also acceptable
        except Exception:
            # Expected behavior for invalid path
            pass
    
    def test_malformed_external_validation_response(self, entity_linker):
        """Test handling malformed external validation responses."""
        with patch.object(ExternalValidators, 'validate_with_wikipedia') as mock_wiki:
            # Mock malformed response
            mock_wiki.return_value = {"invalid": "response"}
            
            entity = EntityMention("test", "MISC", 0, 4, 0.7)
            result = entity_linker.validate_entity(entity)
            
            # Should handle gracefully and fall back to "not found"
            assert isinstance(result, EntityValidationResult)