"""
Entity validation and linking pipeline for content intelligence.
"""
import os
import logging
import json
import sqlite3
import hashlib
from typing import List, Dict, Set, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import threading
import time

import requests
from fuzzywuzzy import fuzz, process
import wikipedia
from urllib.parse import quote_plus

from .entity_recognition_flair import EntityMention, EntityExtractionResult

logger = logging.getLogger(__name__)


@dataclass
class EntityValidationResult:
    """Result of entity validation."""
    entity: EntityMention
    is_valid: bool
    confidence_score: float
    validation_source: str
    canonical_form: Optional[str] = None
    external_links: Optional[Dict[str, str]] = None
    aliases: Optional[List[str]] = None
    description: Optional[str] = None
    entity_type: Optional[str] = None


@dataclass
class EntityLinkingResult:
    """Result of entity linking process."""
    validated_entities: List[EntityValidationResult]
    processing_time: float
    validation_stats: Dict[str, int]


class EntityKnowledgeBase:
    """Local knowledge base for entity validation and linking."""
    
    def __init__(self, db_path: str = "storage/entity_kb.db"):
        """Initialize entity knowledge base."""
        self.db_path = db_path
        self._lock = threading.Lock()
        
        # Create storage directory
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Initialize database
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database for entity storage."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Create entities table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS entities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        canonical_name TEXT UNIQUE NOT NULL,
                        entity_type TEXT,
                        confidence_score REAL DEFAULT 0.0,
                        source TEXT,
                        description TEXT,
                        external_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create aliases table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS entity_aliases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_id INTEGER,
                        alias TEXT NOT NULL,
                        confidence_score REAL DEFAULT 1.0,
                        FOREIGN KEY (entity_id) REFERENCES entities (id),
                        UNIQUE(entity_id, alias)
                    )
                """)
                
                # Create validation cache table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS validation_cache (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        text_hash TEXT UNIQUE NOT NULL,
                        is_valid BOOLEAN,
                        confidence_score REAL,
                        source TEXT,
                        canonical_form TEXT,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_entities_canonical ON entities(canonical_name)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_aliases_alias ON entity_aliases(alias)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_cache_hash ON validation_cache(text_hash)")
                
                conn.commit()
                logger.info("Entity knowledge base initialized")
                
            finally:
                conn.close()
    
    def add_entity(self, canonical_name: str, entity_type: str = None,
                  aliases: List[str] = None, source: str = "manual",
                  confidence: float = 1.0, description: str = None,
                  external_id: str = None):
        """Add entity to knowledge base."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Insert entity
                cursor.execute("""
                    INSERT OR REPLACE INTO entities 
                    (canonical_name, entity_type, confidence_score, source, description, external_id, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (canonical_name, entity_type, confidence, source, description, external_id))
                
                entity_id = cursor.lastrowid
                
                # Add aliases
                if aliases:
                    for alias in aliases:
                        cursor.execute("""
                            INSERT OR REPLACE INTO entity_aliases (entity_id, alias, confidence_score)
                            VALUES (?, ?, ?)
                        """, (entity_id, alias, confidence))
                
                conn.commit()
                logger.debug(f"Added entity: {canonical_name}")
                
            finally:
                conn.close()
    
    def find_entity(self, text: str, threshold: int = 80) -> Optional[Dict[str, Any]]:
        """Find entity by text or alias."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Try exact match first
                cursor.execute("""
                    SELECT e.canonical_name, e.entity_type, e.confidence_score, e.description, e.external_id
                    FROM entities e
                    WHERE e.canonical_name = ? COLLATE NOCASE
                """, (text,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "canonical_name": result[0],
                        "entity_type": result[1],
                        "confidence_score": result[2],
                        "description": result[3],
                        "external_id": result[4],
                        "match_type": "exact"
                    }
                
                # Try alias match
                cursor.execute("""
                    SELECT e.canonical_name, e.entity_type, e.confidence_score, e.description, e.external_id, a.confidence_score
                    FROM entities e
                    JOIN entity_aliases a ON e.id = a.entity_id
                    WHERE a.alias = ? COLLATE NOCASE
                """, (text,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "canonical_name": result[0],
                        "entity_type": result[1],
                        "confidence_score": min(result[2], result[5]),  # Use minimum confidence
                        "description": result[3],
                        "external_id": result[4],
                        "match_type": "alias"
                    }
                
                # Try fuzzy matching
                cursor.execute("""
                    SELECT canonical_name, entity_type, confidence_score, description, external_id
                    FROM entities
                """)
                
                entities = cursor.fetchall()
                if entities:
                    best_match = None
                    best_score = 0
                    
                    for entity in entities:
                        score = fuzz.ratio(text.lower(), entity[0].lower())
                        if score > best_score and score >= threshold:
                            best_score = score
                            best_match = {
                                "canonical_name": entity[0],
                                "entity_type": entity[1],
                                "confidence_score": entity[2] * (score / 100.0),
                                "description": entity[3],
                                "external_id": entity[4],
                                "match_type": "fuzzy",
                                "fuzzy_score": score
                            }
                    
                    return best_match
                
                return None
                
            finally:
                conn.close()
    
    def get_validation_cache(self, text: str) -> Optional[Dict[str, Any]]:
        """Get cached validation result."""
        text_hash = hashlib.md5(text.lower().encode()).hexdigest()
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                # Check if cached result is recent (within 7 days)
                cursor.execute("""
                    SELECT is_valid, confidence_score, source, canonical_form
                    FROM validation_cache
                    WHERE text_hash = ? AND cached_at > datetime('now', '-7 days')
                """, (text_hash,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        "is_valid": bool(result[0]),
                        "confidence_score": result[1],
                        "source": result[2],
                        "canonical_form": result[3]
                    }
                
                return None
                
            finally:
                conn.close()
    
    def cache_validation_result(self, text: str, is_valid: bool,
                              confidence_score: float, source: str,
                              canonical_form: str = None):
        """Cache validation result."""
        text_hash = hashlib.md5(text.lower().encode()).hexdigest()
        
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO validation_cache 
                    (text_hash, is_valid, confidence_score, source, canonical_form, cached_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (text_hash, is_valid, confidence_score, source, canonical_form))
                
                conn.commit()
                
            finally:
                conn.close()
    
    def cleanup_cache(self, days_old: int = 30):
        """Clean up old cache entries."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM validation_cache 
                    WHERE cached_at < datetime('now', '-{} days')
                """.format(days_old))
                
                deleted = cursor.rowcount
                conn.commit()
                
                if deleted > 0:
                    logger.info(f"Cleaned up {deleted} old cache entries")
                
            finally:
                conn.close()


class ExternalValidators:
    """External validation sources for entities."""
    
    @staticmethod
    def validate_with_wikipedia(entity_text: str, max_results: int = 3) -> Optional[Dict[str, Any]]:
        """Validate entity using Wikipedia."""
        try:
            # Search Wikipedia
            search_results = wikipedia.search(entity_text, results=max_results)
            
            if not search_results:
                return None
            
            # Try to get page for best match
            best_match = search_results[0]
            
            try:
                page = wikipedia.page(best_match, auto_suggest=False)
                
                return {
                    "is_valid": True,
                    "confidence_score": 0.8,
                    "canonical_form": page.title,
                    "description": page.summary[:500] + "..." if len(page.summary) > 500 else page.summary,
                    "external_links": {"wikipedia": page.url},
                    "aliases": search_results,
                    "entity_type": "wikipedia_entity"
                }
                
            except wikipedia.exceptions.DisambiguationError as e:
                # Handle disambiguation pages
                if e.options:
                    return {
                        "is_valid": True,
                        "confidence_score": 0.6,
                        "canonical_form": e.options[0],
                        "aliases": e.options[:5],
                        "entity_type": "wikipedia_disambiguation"
                    }
            
            except wikipedia.exceptions.PageError:
                # Page not found, but search had results
                return {
                    "is_valid": False,
                    "confidence_score": 0.3,
                    "canonical_form": best_match
                }
        
        except Exception as e:
            logger.debug(f"Wikipedia validation failed for '{entity_text}': {str(e)}")
            return None
    
    @staticmethod
    def validate_with_wikidata(entity_text: str) -> Optional[Dict[str, Any]]:
        """Validate entity using Wikidata API."""
        try:
            # Search Wikidata
            search_url = "https://www.wikidata.org/w/api.php"
            params = {
                "action": "wbsearchentities",
                "search": entity_text,
                "language": "en",
                "format": "json",
                "limit": 3
            }
            
            response = requests.get(search_url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("search"):
                best_match = data["search"][0]
                
                return {
                    "is_valid": True,
                    "confidence_score": 0.7,
                    "canonical_form": best_match.get("label", entity_text),
                    "description": best_match.get("description", ""),
                    "external_links": {"wikidata": f"https://www.wikidata.org/wiki/{best_match['id']}"},
                    "entity_type": "wikidata_entity",
                    "external_id": best_match["id"]
                }
            
            return None
            
        except Exception as e:
            logger.debug(f"Wikidata validation failed for '{entity_text}': {str(e)}")
            return None


class EntityLinker:
    """Main entity linking and validation system."""
    
    def __init__(self, knowledge_base: EntityKnowledgeBase = None):
        """Initialize entity linker."""
        self.kb = knowledge_base or EntityKnowledgeBase()
        self.validators = {
            "wikipedia": ExternalValidators.validate_with_wikipedia,
            "wikidata": ExternalValidators.validate_with_wikidata,
        }
        
        # Validation settings
        self.validation_threshold = 0.5
        self.use_cache = True
        self.external_validation = True
        
        # Load domain-specific entities
        self._load_domain_entities()
    
    def _load_domain_entities(self):
        """Load domain-specific entities into knowledge base."""
        # Technology companies
        tech_companies = {
            "Google": {"type": "technology_company", "aliases": ["Alphabet", "Google LLC"]},
            "Microsoft": {"type": "technology_company", "aliases": ["MSFT", "Microsoft Corporation"]},
            "Apple": {"type": "technology_company", "aliases": ["Apple Inc.", "AAPL"]},
            "Amazon": {"type": "technology_company", "aliases": ["Amazon.com", "AWS", "AMZN"]},
            "Meta": {"type": "technology_company", "aliases": ["Facebook", "Meta Platforms"]},
            "Tesla": {"type": "automotive_company", "aliases": ["Tesla Inc.", "TSLA"]},
            "OpenAI": {"type": "ai_company", "aliases": ["Open AI"]},
            "NVIDIA": {"type": "technology_company", "aliases": ["Nvidia Corporation"]},
            "Intel": {"type": "technology_company", "aliases": ["Intel Corporation"]},
            "AMD": {"type": "technology_company", "aliases": ["Advanced Micro Devices"]},
        }
        
        for name, info in tech_companies.items():
            try:
                self.kb.add_entity(
                    canonical_name=name,
                    entity_type=info["type"],
                    aliases=info.get("aliases", []),
                    source="domain_knowledge",
                    confidence=0.9
                )
            except Exception as e:
                logger.debug(f"Failed to add entity {name}: {str(e)}")
    
    def validate_entity(self, entity: EntityMention) -> EntityValidationResult:
        """Validate a single entity mention."""
        start_time = time.time()
        
        # Check cache first
        if self.use_cache:
            cached = self.kb.get_validation_cache(entity.text)
            if cached:
                return EntityValidationResult(
                    entity=entity,
                    is_valid=cached["is_valid"],
                    confidence_score=cached["confidence_score"],
                    validation_source=cached["source"],
                    canonical_form=cached.get("canonical_form")
                )
        
        # Check local knowledge base
        kb_result = self.kb.find_entity(entity.text)
        if kb_result:
            result = EntityValidationResult(
                entity=entity,
                is_valid=True,
                confidence_score=kb_result["confidence_score"],
                validation_source="knowledge_base",
                canonical_form=kb_result["canonical_name"],
                entity_type=kb_result["entity_type"],
                description=kb_result.get("description")
            )
            
            # Cache result
            if self.use_cache:
                self.kb.cache_validation_result(
                    entity.text, True, kb_result["confidence_score"],
                    "knowledge_base", kb_result["canonical_name"]
                )
            
            return result
        
        # Try external validation
        if self.external_validation:
            for validator_name, validator_func in self.validators.items():
                try:
                    validation_result = validator_func(entity.text)
                    if validation_result and validation_result.get("is_valid"):
                        
                        # Add to knowledge base for future use
                        if validation_result.get("canonical_form"):
                            self.kb.add_entity(
                                canonical_name=validation_result["canonical_form"],
                                entity_type=validation_result.get("entity_type"),
                                aliases=validation_result.get("aliases", []),
                                source=validator_name,
                                confidence=validation_result["confidence_score"],
                                description=validation_result.get("description"),
                                external_id=validation_result.get("external_id")
                            )
                        
                        result = EntityValidationResult(
                            entity=entity,
                            is_valid=validation_result["is_valid"],
                            confidence_score=validation_result["confidence_score"],
                            validation_source=validator_name,
                            canonical_form=validation_result.get("canonical_form"),
                            external_links=validation_result.get("external_links"),
                            aliases=validation_result.get("aliases"),
                            description=validation_result.get("description"),
                            entity_type=validation_result.get("entity_type")
                        )
                        
                        # Cache result
                        if self.use_cache:
                            self.kb.cache_validation_result(
                                entity.text, True, validation_result["confidence_score"],
                                validator_name, validation_result.get("canonical_form")
                            )
                        
                        return result
                        
                except Exception as e:
                    logger.debug(f"Validation with {validator_name} failed: {str(e)}")
                    continue
        
        # Entity not validated
        result = EntityValidationResult(
            entity=entity,
            is_valid=False,
            confidence_score=0.0,
            validation_source="none"
        )
        
        # Cache negative result
        if self.use_cache:
            self.kb.cache_validation_result(
                entity.text, False, 0.0, "none"
            )
        
        return result
    
    def link_entities(self, extraction_result: EntityExtractionResult) -> EntityLinkingResult:
        """Link and validate all entities in extraction result."""
        start_time = time.time()
        
        validated_entities = []
        stats = defaultdict(int)
        
        for entity in extraction_result.entities:
            try:
                validation_result = self.validate_entity(entity)
                validated_entities.append(validation_result)
                
                # Update stats
                stats["total"] += 1
                if validation_result.is_valid:
                    stats["valid"] += 1
                    stats[validation_result.validation_source] += 1
                else:
                    stats["invalid"] += 1
                    
            except Exception as e:
                logger.error(f"Entity validation failed for '{entity.text}': {str(e)}")
                # Add as invalid entity
                invalid_result = EntityValidationResult(
                    entity=entity,
                    is_valid=False,
                    confidence_score=0.0,
                    validation_source="error"
                )
                validated_entities.append(invalid_result)
                stats["error"] += 1
        
        processing_time = time.time() - start_time
        
        result = EntityLinkingResult(
            validated_entities=validated_entities,
            processing_time=processing_time,
            validation_stats=dict(stats)
        )
        
        logger.info(f"Entity linking completed in {processing_time:.2f}s")
        logger.info(f"Validation stats: {dict(stats)}")
        
        return result
    
    def get_entity_statistics(self) -> Dict[str, Any]:
        """Get statistics about the entity knowledge base."""
        with self.kb._lock:
            conn = sqlite3.connect(self.kb.db_path)
            try:
                cursor = conn.cursor()
                
                # Count entities by type
                cursor.execute("""
                    SELECT entity_type, COUNT(*) 
                    FROM entities 
                    WHERE entity_type IS NOT NULL 
                    GROUP BY entity_type
                """)
                entity_types = dict(cursor.fetchall())
                
                # Count total entities
                cursor.execute("SELECT COUNT(*) FROM entities")
                total_entities = cursor.fetchone()[0]
                
                # Count aliases
                cursor.execute("SELECT COUNT(*) FROM entity_aliases")
                total_aliases = cursor.fetchone()[0]
                
                # Count cache entries
                cursor.execute("SELECT COUNT(*) FROM validation_cache")
                cache_entries = cursor.fetchone()[0]
                
                return {
                    "total_entities": total_entities,
                    "total_aliases": total_aliases,
                    "cache_entries": cache_entries,
                    "entity_types": entity_types
                }
                
            finally:
                conn.close()


# Global entity linker instance
_entity_linker = None


def get_entity_linker() -> EntityLinker:
    """Get or create global entity linker instance."""
    global _entity_linker
    
    if _entity_linker is None:
        _entity_linker = EntityLinker()
    
    return _entity_linker


def validate_and_link_entities(extraction_result: EntityExtractionResult) -> EntityLinkingResult:
    """Validate and link entities from extraction result."""
    linker = get_entity_linker()
    return linker.link_entities(extraction_result)