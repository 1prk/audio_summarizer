"""
Domain-specific entity recognition using spaCy and custom dictionaries.
"""
import os
import logging
import json
import re
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

import spacy
from spacy.matcher import PhraseMatcher
from fuzzywuzzy import fuzz, process
import wikipedia

logger = logging.getLogger(__name__)


@dataclass
class EntityMention:
    """Data class for entity mentions."""
    text: str
    label: str
    start: int
    end: int
    confidence: float
    canonical_name: Optional[str] = None
    external_id: Optional[str] = None
    context: Optional[str] = None


@dataclass
class EntityExtractionResult:
    """Result of entity extraction."""
    entities: List[EntityMention]
    confidence_score: float
    processing_time: float


class DomainDictionary:
    """Domain-specific entity dictionary."""
    
    def __init__(self, domain_name: str):
        self.domain_name = domain_name
        self.entities = {}  # canonical_name -> variations
        self.categories = defaultdict(set)  # category -> set of canonical names
        
    def add_entity(self, canonical_name: str, variations: List[str], category: str = None):
        """Add entity with variations to dictionary."""
        self.entities[canonical_name] = variations
        if category:
            self.categories[category].add(canonical_name)
    
    def get_variations(self, canonical_name: str) -> List[str]:
        """Get all variations of an entity."""
        return self.entities.get(canonical_name, [canonical_name])
    
    def search_entity(self, text: str, threshold: int = 80) -> Optional[Tuple[str, int]]:
        """Search for entity using fuzzy matching."""
        best_match = None
        best_score = 0
        
        for canonical_name, variations in self.entities.items():
            all_forms = [canonical_name] + variations
            for form in all_forms:
                score = fuzz.ratio(text.lower(), form.lower())
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = canonical_name
        
        return (best_match, best_score) if best_match else None


class EntityRecognizer:
    """Enhanced entity recognizer with domain-specific knowledge."""
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """Initialize entity recognizer."""
        self.model_name = model_name
        self.nlp = None
        self.phrase_matcher = None
        self.domain_dictionaries = {}
        self.custom_patterns = {}
        
        # Load model and setup
        self._load_model()
        self._setup_domain_dictionaries()
        self._setup_custom_patterns()
    
    def _load_model(self):
        """Load spaCy model."""
        try:
            self.nlp = spacy.load(self.model_name)
            logger.info(f"Loaded spaCy model: {self.model_name}")
        except OSError:
            logger.warning(f"Model {self.model_name} not found. Installing...")
            os.system(f"python -m spacy download {self.model_name}")
            self.nlp = spacy.load(self.model_name)
        
        # Setup phrase matcher
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
    
    def _setup_domain_dictionaries(self):
        """Setup domain-specific dictionaries."""
        # Technology domain
        tech_dict = DomainDictionary("technology")
        tech_entities = {
            "Python": ["python", "Python programming", "Python language"],
            "JavaScript": ["javascript", "js", "JS", "ECMAScript"],
            "React": ["react", "ReactJS", "React.js"],
            "Node.js": ["nodejs", "node", "Node"],
            "Docker": ["docker", "containerization"],
            "Kubernetes": ["kubernetes", "k8s", "K8s"],
            "AWS": ["amazon web services", "aws", "Amazon AWS"],
            "Google Cloud": ["gcp", "google cloud platform", "GCP"],
            "Machine Learning": ["ml", "machine learning", "ML"],
            "Artificial Intelligence": ["ai", "artificial intelligence", "AI"],
            "Deep Learning": ["deep learning", "neural networks"],
            "TensorFlow": ["tensorflow", "TF"],
            "PyTorch": ["pytorch", "torch"],
            "OpenAI": ["openai", "open ai"],
            "ChatGPT": ["chatgpt", "chat gpt", "gpt"],
            "GitHub": ["github", "git hub"],
            "Visual Studio Code": ["vscode", "vs code", "visual studio code"],
            "Linux": ["linux", "gnu/linux"],
            "Ubuntu": ["ubuntu"],
            "Windows": ["windows", "microsoft windows"],
            "macOS": ["macos", "mac os", "osx"],
        }
        
        for canonical, variations in tech_entities.items():
            tech_dict.add_entity(canonical, variations, "software")
        
        self.domain_dictionaries["technology"] = tech_dict
        
        # Automotive domain
        auto_dict = DomainDictionary("automotive")
        auto_entities = {
            "Tesla": ["tesla", "tesla motors"],
            "BMW": ["bmw", "bavarian motor works"],
            "Mercedes-Benz": ["mercedes", "mercedes-benz", "benz"],
            "Audi": ["audi"],
            "Toyota": ["toyota"],
            "Honda": ["honda"],
            "Ford": ["ford", "ford motor company"],
            "Volkswagen": ["volkswagen", "vw"],
            "Electric Vehicle": ["ev", "electric car", "electric vehicle"],
            "Autonomous Driving": ["self-driving", "autonomous", "autopilot"],
            "Internal Combustion Engine": ["ice", "combustion engine"],
            "Hybrid": ["hybrid vehicle", "hybrid car"],
        }
        
        for canonical, variations in auto_entities.items():
            auto_dict.add_entity(canonical, variations, "automotive")
        
        self.domain_dictionaries["automotive"] = auto_dict
        
        # Gaming domain
        gaming_dict = DomainDictionary("gaming")
        gaming_entities = {
            "PlayStation": ["playstation", "ps", "sony playstation"],
            "Xbox": ["xbox", "microsoft xbox"],
            "Nintendo": ["nintendo", "nintendo switch"],
            "Steam": ["steam", "valve steam"],
            "Epic Games": ["epic", "epic games", "fortnite"],
            "Unity": ["unity", "unity engine", "unity3d"],
            "Unreal Engine": ["unreal", "unreal engine", "ue4", "ue5"],
            "Minecraft": ["minecraft", "mc"],
            "Fortnite": ["fortnite"],
            "Call of Duty": ["cod", "call of duty"],
            "League of Legends": ["lol", "league of legends"],
            "Counter-Strike": ["cs", "counter-strike", "csgo"],
        }
        
        for canonical, variations in gaming_entities.items():
            gaming_dict.add_entity(canonical, variations, "gaming")
        
        self.domain_dictionaries["gaming"] = gaming_dict
        
        # Setup phrase matcher patterns
        self._setup_phrase_patterns()
    
    def _setup_phrase_patterns(self):
        """Setup phrase matcher patterns from dictionaries."""
        patterns = []
        
        for domain_dict in self.domain_dictionaries.values():
            for canonical_name, variations in domain_dict.entities.items():
                all_forms = [canonical_name] + variations
                for form in all_forms:
                    doc = self.nlp(form)
                    patterns.append((doc, canonical_name, domain_dict.domain_name))
        
        # Add patterns to matcher
        if patterns:
            docs, canonical_names, domains = zip(*patterns)
            self.phrase_matcher.add("DOMAIN_ENTITIES", docs)
            
            # Store mapping for lookup
            self.pattern_mapping = {}
            for i, (doc, canonical, domain) in enumerate(patterns):
                self.pattern_mapping[doc.text.lower()] = (canonical, domain)
    
    def _setup_custom_patterns(self):
        """Setup custom regex patterns for specific entity types."""
        self.custom_patterns = {
            "VERSION": [
                r'\bv?\d+\.\d+(?:\.\d+)?\b',  # Version numbers
                r'\b(?:version\s+)?\d+\.\d+(?:\.\d+)?\b',
            ],
            "URL": [
                r'https?://[^\s]+',
                r'www\.[^\s]+',
            ],
            "EMAIL": [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            ],
            "CURRENCY": [
                r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
                r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:dollars?|USD|usd)',
            ],
            "PERCENTAGE": [
                r'\d+(?:\.\d+)?%',
                r'\d+(?:\.\d+)?\s*percent',
            ],
        }
    
    def extract_custom_patterns(self, text: str) -> List[EntityMention]:
        """Extract entities using custom regex patterns."""
        entities = []
        
        for label, patterns in self.custom_patterns.items():
            for pattern in patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    entity = EntityMention(
                        text=match.group(),
                        label=label,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.9,  # High confidence for regex matches
                        canonical_name=match.group(),
                    )
                    entities.append(entity)
        
        return entities
    
    def extract_spacy_entities(self, text: str) -> List[EntityMention]:
        """Extract entities using spaCy NER."""
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            # Skip very short entities or common stop words
            if len(ent.text.strip()) < 2:
                continue
                
            entity = EntityMention(
                text=ent.text,
                label=ent.label_,
                start=ent.start_char,
                end=ent.end_char,
                confidence=0.8,  # Default confidence for spaCy
                canonical_name=ent.text,
                context=self._get_context(text, ent.start_char, ent.end_char)
            )
            entities.append(entity)
        
        return entities
    
    def extract_domain_entities(self, text: str) -> List[EntityMention]:
        """Extract entities using domain dictionaries and phrase matching."""
        doc = self.nlp(text)
        matches = self.phrase_matcher(doc)
        entities = []
        
        for match_id, start, end in matches:
            span = doc[start:end]
            matched_text = span.text.lower()
            
            if matched_text in self.pattern_mapping:
                canonical_name, domain = self.pattern_mapping[matched_text]
                
                entity = EntityMention(
                    text=span.text,
                    label=f"DOMAIN_{domain.upper()}",
                    start=span.start_char,
                    end=span.end_char,
                    confidence=0.95,  # High confidence for exact matches
                    canonical_name=canonical_name,
                    context=self._get_context(text, span.start_char, span.end_char)
                )
                entities.append(entity)
        
        return entities
    
    def extract_fuzzy_entities(self, text: str, threshold: int = 85) -> List[EntityMention]:
        """Extract entities using fuzzy matching for transcription errors."""
        words = re.findall(r'\b\w+(?:\s+\w+){0,2}\b', text)  # 1-3 word phrases
        entities = []
        
        for word_phrase in words:
            word_phrase = word_phrase.strip()
            if len(word_phrase) < 3:
                continue
                
            for domain_dict in self.domain_dictionaries.values():
                result = domain_dict.search_entity(word_phrase, threshold)
                if result:
                    canonical_name, score = result
                    
                    # Find position in original text
                    start_pos = text.lower().find(word_phrase.lower())
                    if start_pos != -1:
                        entity = EntityMention(
                            text=word_phrase,
                            label=f"FUZZY_{domain_dict.domain_name.upper()}",
                            start=start_pos,
                            end=start_pos + len(word_phrase),
                            confidence=score / 100.0,
                            canonical_name=canonical_name,
                            context=self._get_context(text, start_pos, start_pos + len(word_phrase))
                        )
                        entities.append(entity)
        
        return entities
    
    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Get context around entity mention."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()
    
    def validate_entity(self, entity: EntityMention) -> EntityMention:
        """Validate entity using external sources."""
        try:
            # Try Wikipedia lookup for validation
            if entity.canonical_name and len(entity.canonical_name) > 3:
                search_results = wikipedia.search(entity.canonical_name, results=1)
                if search_results:
                    # Entity found in Wikipedia
                    entity.confidence = min(entity.confidence + 0.1, 1.0)
                    entity.external_id = f"wikipedia:{search_results[0]}"
        except Exception as e:
            logger.debug(f"Wikipedia validation failed for {entity.canonical_name}: {str(e)}")
        
        return entity
    
    def merge_overlapping_entities(self, entities: List[EntityMention]) -> List[EntityMention]:
        """Merge overlapping entity mentions."""
        if not entities:
            return []
        
        # Sort by start position
        entities.sort(key=lambda x: x.start)
        merged = []
        
        for entity in entities:
            if not merged:
                merged.append(entity)
                continue
            
            last_entity = merged[-1]
            
            # Check for overlap
            if entity.start <= last_entity.end:
                # Choose entity with higher confidence
                if entity.confidence > last_entity.confidence:
                    merged[-1] = entity
                # If same confidence, prefer longer entity
                elif (entity.confidence == last_entity.confidence and 
                      len(entity.text) > len(last_entity.text)):
                    merged[-1] = entity
            else:
                merged.append(entity)
        
        return merged
    
    def extract_entities(self, text: str, validate: bool = True, 
                        include_fuzzy: bool = True) -> EntityExtractionResult:
        """Extract all entities from text."""
        import time
        start_time = time.time()
        
        all_entities = []
        
        # Extract using different methods
        all_entities.extend(self.extract_spacy_entities(text))
        all_entities.extend(self.extract_domain_entities(text))
        all_entities.extend(self.extract_custom_patterns(text))
        
        if include_fuzzy:
            all_entities.extend(self.extract_fuzzy_entities(text))
        
        # Merge overlapping entities
        merged_entities = self.merge_overlapping_entities(all_entities)
        
        # Validate entities if requested
        if validate:
            validated_entities = []
            for entity in merged_entities:
                validated_entity = self.validate_entity(entity)
                validated_entities.append(validated_entity)
            merged_entities = validated_entities
        
        # Calculate overall confidence
        if merged_entities:
            avg_confidence = sum(e.confidence for e in merged_entities) / len(merged_entities)
        else:
            avg_confidence = 0.0
        
        processing_time = time.time() - start_time
        
        return EntityExtractionResult(
            entities=merged_entities,
            confidence_score=avg_confidence,
            processing_time=processing_time
        )


# Global recognizer instance
_entity_recognizer = None


def get_entity_recognizer() -> EntityRecognizer:
    """Get or create global entity recognizer instance."""
    global _entity_recognizer
    
    if _entity_recognizer is None:
        _entity_recognizer = EntityRecognizer()
    
    return _entity_recognizer


def extract_entities_from_transcript(transcript_text: str) -> EntityExtractionResult:
    """Extract entities from transcript text."""
    recognizer = get_entity_recognizer()
    return recognizer.extract_entities(transcript_text)