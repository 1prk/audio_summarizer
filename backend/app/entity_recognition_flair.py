"""
German-focused entity recognition using Flair NER and custom dictionaries.
"""
import os
import logging
import time
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict

from flair.data import Sentence
from flair.models import SequenceTagger
from fuzzywuzzy import fuzz, process

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


class FlairEntityRecognizer:
    """German NER using Flair with domain-specific enhancements."""
    
    def __init__(self, model_name: str = "flair/ner-german-large"):
        """Initialize Flair entity recognizer."""
        self.model_name = model_name
        self.tagger = None
        self.domain_dictionaries = {}
        self.custom_patterns = {}
        
        # Load model and setup
        self._load_model()
        self._setup_domain_dictionaries()
        
    def _load_model(self):
        """Load Flair NER model."""
        try:
            logger.info(f"Loading Flair model: {self.model_name}")
            self.tagger = SequenceTagger.load(self.model_name)
            logger.info(f"Successfully loaded Flair model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load Flair model {self.model_name}: {str(e)}")
            logger.info("Falling back to English model...")
            try:
                self.tagger = SequenceTagger.load('flair/ner-english-large')
                self.model_name = 'flair/ner-english-large'
                logger.info(f"Loaded fallback model: {self.model_name}")
            except Exception as e2:
                logger.error(f"Failed to load fallback model: {str(e2)}")
                logger.info("Using English ontonotes model as final fallback...")
                self.tagger = SequenceTagger.load('flair/ner-english-ontonotes-large')
                self.model_name = 'flair/ner-english-ontonotes-large'
                logger.info(f"Loaded final fallback model: {self.model_name}")
    
    def _setup_domain_dictionaries(self):
        """Setup domain-specific dictionaries for German content."""
        # Technology domain (German-focused)
        tech_dict = DomainDictionary("technology")
        tech_entities = {
            "Python": ["python", "Python-Programmierung", "Python-Sprache"],
            "JavaScript": ["javascript", "js", "JS", "ECMAScript"],
            "React": ["react", "ReactJS", "React.js"],
            "Node.js": ["nodejs", "node", "Node"],
            "Docker": ["docker", "containerization", "Containerisierung"],
            "Kubernetes": ["kubernetes", "k8s", "K8s"],
            "AWS": ["amazon web services", "aws", "Amazon AWS"],
            "Google Cloud": ["gcp", "google cloud platform", "GCP", "Google-Cloud"],
            "Machine Learning": ["ml", "machine learning", "ML", "maschinelles lernen", "Maschinelles Lernen"],
            "Artificial Intelligence": ["ai", "artificial intelligence", "AI", "künstliche intelligenz", "KI"],
            "Deep Learning": ["deep learning", "neural networks", "neuronale netze", "Neuronale Netze"],
            "TensorFlow": ["tensorflow", "TF"],
            "PyTorch": ["pytorch", "torch"],
            "OpenAI": ["openai", "open ai"],
            "ChatGPT": ["chatgpt", "chat gpt", "gpt"],
            "GitHub": ["github", "git hub"],
            "Visual Studio Code": ["vscode", "vs code", "visual studio code"],
            "Linux": ["linux", "gnu/linux"],
            "Ubuntu": ["ubuntu", "Ubuntu"],
            "Windows": ["windows", "microsoft windows", "Microsoft Windows"],
            "macOS": ["macos", "mac os", "osx", "MacOS"],
        }
        
        for canonical, variations in tech_entities.items():
            tech_dict.add_entity(canonical, variations, "software")
        
        self.domain_dictionaries["technology"] = tech_dict
        
        # Automotive domain (German brands prominent)
        auto_dict = DomainDictionary("automotive")
        auto_entities = {
            "BMW": ["bmw", "bayerische motoren werke", "Bayerische Motoren Werke"],
            "Mercedes-Benz": ["mercedes", "mercedes benz", "benz", "Mercedes", "Mercedes-Benz"],
            "Volkswagen": ["vw", "volkswagen", "volks wagen", "VW", "Volkswagen"],
            "Audi": ["audi", "Audi"],
            "Porsche": ["porsche", "Porsche"],
            "Opel": ["opel", "Opel"],
            "Ford": ["ford", "Ford"],
            "Toyota": ["toyota", "Toyota"],
            "Tesla": ["tesla", "Tesla"],
            "General Motors": ["gm", "general motors", "GM"],
        }
        
        for canonical, variations in auto_entities.items():
            auto_dict.add_entity(canonical, variations, "manufacturer")
        
        self.domain_dictionaries["automotive"] = auto_dict
        
        # Gaming domain (including German preferences)
        gaming_dict = DomainDictionary("gaming")
        gaming_entities = {
            "PlayStation": ["playstation", "ps", "sony playstation", "Playstation"],
            "Xbox": ["xbox", "microsoft xbox", "Xbox"],
            "Nintendo": ["nintendo", "Nintendo"],
            "Steam": ["steam", "steam platform", "Steam"],
            "Epic Games": ["epic games", "epic", "Epic Games"],
            "Valve": ["valve corporation", "valve", "Valve"],
            "Blizzard": ["blizzard entertainment", "blizzard", "Blizzard"],
            "EA": ["electronic arts", "ea", "EA"],
            "Ubisoft": ["ubisoft", "Ubisoft"],
        }
        
        for canonical, variations in gaming_entities.items():
            gaming_dict.add_entity(canonical, variations, "company")
        
        self.domain_dictionaries["gaming"] = gaming_dict
        
        # German Media & Personalities
        media_dict = DomainDictionary("media")
        media_entities = {
            "Tagesschau": ["tagesschau", "Tagesschau"],
            "ZDF": ["zdf", "ZDF", "Zweites Deutsches Fernsehen"],
            "ARD": ["ard", "ARD"],
            "RTL": ["rtl", "RTL"],
            "ProSieben": ["prosieben", "pro7", "Pro7", "ProSieben"],
            "Sat.1": ["sat1", "sat.1", "Sat1", "Sat.1"],
            "YouTube": ["youtube", "YouTube"],
            "Twitch": ["twitch", "Twitch"],
        }
        
        for canonical, variations in media_entities.items():
            media_dict.add_entity(canonical, variations, "media")
        
        self.domain_dictionaries["media"] = media_dict
    
    def extract_flair_entities(self, text: str) -> List[EntityMention]:
        """Extract entities using Flair NER."""
        entities = []
        
        try:
            # Create sentence and predict
            sentence = Sentence(text)
            self.tagger.predict(sentence)
            
            # Convert Flair entities to our format
            for entity in sentence.get_spans('ner'):
                # Map Flair labels to our labels
                label = self._map_flair_label(entity.tag)
                
                entities.append(EntityMention(
                    text=entity.text,
                    label=label,
                    start=entity.start_position,
                    end=entity.end_position,
                    confidence=entity.score,
                    canonical_name=entity.text
                ))
                
        except Exception as e:
            logger.error(f"Error in Flair NER: {str(e)}")
        
        return entities
    
    def _map_flair_label(self, flair_label: str) -> str:
        """Map Flair labels to our standard labels."""
        label_mapping = {
            'PER': 'PERSON',
            'LOC': 'LOCATION', 
            'ORG': 'ORG',
            'MISC': 'MISC',
            # German model specific
            'PERSON': 'PERSON',
            'LOCATION': 'LOCATION',
            'ORGANIZATION': 'ORG',
            'MISCELLANEOUS': 'MISC',
        }
        
        return label_mapping.get(flair_label, flair_label)
    
    def extract_domain_entities(self, text: str) -> List[EntityMention]:
        """Extract entities using domain dictionaries."""
        entities = []
        
        for domain_name, dictionary in self.domain_dictionaries.items():
            for canonical_name, variations in dictionary.entities.items():
                all_forms = [canonical_name] + variations
                
                for form in all_forms:
                    # Case insensitive search
                    import re
                    pattern = r'\b' + re.escape(form) + r'\b'
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    
                    for match in matches:
                        # Determine entity type based on domain
                        if domain_name == "technology":
                            label = "TECH"
                        elif domain_name == "automotive":
                            label = "ORG"  # Car companies are organizations
                        elif domain_name == "gaming":
                            label = "PRODUCT"
                        elif domain_name == "media":
                            label = "ORG"
                        else:
                            label = "MISC"
                        
                        entities.append(EntityMention(
                            text=match.group(),
                            label=label,
                            start=match.start(),
                            end=match.end(),
                            confidence=0.95,  # High confidence for exact matches
                            canonical_name=canonical_name
                        ))
        
        return entities
    
    def merge_overlapping_entities(self, entities: List[EntityMention]) -> List[EntityMention]:
        """Merge overlapping entities, preferring higher confidence."""
        if not entities:
            return []
        
        # Sort by start position
        sorted_entities = sorted(entities, key=lambda e: (e.start, -e.confidence))
        merged = []
        
        for entity in sorted_entities:
            # Check for overlap with existing entities
            overlaps = False
            for i, existing in enumerate(merged):
                if (entity.start < existing.end and entity.end > existing.start):
                    overlaps = True
                    # Keep the entity with higher confidence
                    if entity.confidence > existing.confidence:
                        merged[i] = entity
                    break
            
            if not overlaps:
                merged.append(entity)
        
        return merged
    
    def extract_entities(self, text: str, validate: bool = False) -> EntityExtractionResult:
        """Extract all entities from text using Flair + domain knowledge."""
        start_time = time.time()
        
        all_entities = []
        
        # Extract using Flair NER
        all_entities.extend(self.extract_flair_entities(text))
        
        # Extract using domain dictionaries
        all_entities.extend(self.extract_domain_entities(text))
        
        # Merge overlapping entities
        merged_entities = self.merge_overlapping_entities(all_entities)
        
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


# Global instance
_entity_recognizer = None

def get_entity_recognizer() -> FlairEntityRecognizer:
    """Get or create global entity recognizer instance."""
    global _entity_recognizer
    if _entity_recognizer is None:
        _entity_recognizer = FlairEntityRecognizer()
    return _entity_recognizer


def extract_entities_from_transcript(transcript_text: str) -> EntityExtractionResult:
    """Extract entities from transcript text using Flair German NER."""
    recognizer = get_entity_recognizer()
    return recognizer.extract_entities(transcript_text)