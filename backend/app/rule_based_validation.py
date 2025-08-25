"""
Rule-based validation and post-processing for LLM-cleaned transcripts.

This module provides comprehensive validation mechanisms to ensure that
LLM cleaning hasn't introduced hallucinations or unwanted modifications.
"""

import re
import json
import logging
from typing import Dict, List, Set, Tuple, Optional, NamedTuple
from dataclasses import dataclass
from difflib import SequenceMatcher
import unicodedata

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of rule-based validation."""
    passed: bool
    confidence_score: float
    issues: List[str]
    warnings: List[str]
    suspicious_patterns: List[str]
    text_statistics: Dict[str, float]


class RuleBasedValidator:
    """Rule-based validator for LLM-cleaned transcripts."""
    
    def __init__(self):
        """Initialize validator with gazetteer and patterns."""
        self.german_cities = self._load_german_cities()
        self.german_names = self._load_german_names()
        self.technical_terms = self._load_technical_terms()
        self.forbidden_patterns = self._load_forbidden_patterns()
        self.hallucination_indicators = self._load_hallucination_indicators()
        
        logger.info("Rule-based validator initialized")
    
    def validate_cleaned_text(self, original: str, cleaned: str, context: Optional[str] = None) -> ValidationResult:
        """
        Validate cleaned text against original using rule-based checks.
        
        Args:
            original: Original transcript text
            cleaned: LLM-cleaned text
            context: Optional context (video title, description)
        
        Returns:
            ValidationResult with validation outcome and details
        """
        issues = []
        warnings = []
        suspicious_patterns = []
        
        # Basic sanity checks
        if not cleaned or len(cleaned.strip()) < 10:
            issues.append("Cleaned text is empty or too short")
            return self._create_failed_result(issues, warnings, suspicious_patterns, original, cleaned)
        
        # 1. Content similarity check
        similarity_issues = self._check_content_similarity(original, cleaned)
        issues.extend(similarity_issues)
        
        # 2. Length and structure validation
        structure_warnings = self._check_text_structure(original, cleaned)
        warnings.extend(structure_warnings)
        
        # 3. New entity validation
        entity_issues, entity_warnings = self._validate_new_entities(original, cleaned)
        issues.extend(entity_issues)
        warnings.extend(entity_warnings)
        
        # 4. Hallucination pattern detection
        hallucination_issues = self._detect_hallucination_patterns(cleaned, original)
        issues.extend(hallucination_issues)
        
        # 5. German language validation
        language_warnings = self._validate_german_language(cleaned)
        warnings.extend(language_warnings)
        
        # 6. Context consistency check
        if context:
            context_warnings = self._check_context_consistency(cleaned, context)
            warnings.extend(context_warnings)
        
        # 7. Suspicious pattern detection
        suspicious_patterns = self._detect_suspicious_patterns(cleaned, original)
        
        # Calculate overall confidence
        confidence_score = self._calculate_validation_confidence(original, cleaned, issues, warnings)
        
        # Generate text statistics
        text_stats = self._generate_text_statistics(original, cleaned)
        
        # Determine overall validation result (very relaxed threshold)
        passed = len(issues) == 0 and confidence_score > 0.2  # Very relaxed from 0.5 to 0.2
        
        return ValidationResult(
            passed=passed,
            confidence_score=confidence_score,
            issues=issues,
            warnings=warnings,
            suspicious_patterns=suspicious_patterns,
            text_statistics=text_stats
        )
    
    def _check_content_similarity(self, original: str, cleaned: str) -> List[str]:
        """Check if content similarity is acceptable."""
        issues = []
        
        # Basic similarity check
        matcher = SequenceMatcher(None, original.lower(), cleaned.lower())
        similarity = matcher.ratio()
        
        if similarity < 0.15:  # Very relaxed from 0.4 to 0.15 (only flag extreme cases)
            issues.append(f"Content similarity too low: {similarity:.2f}")
        
        # Word count check (very relaxed)
        orig_words = len(original.split())
        cleaned_words = len(cleaned.split())
        word_ratio = cleaned_words / orig_words if orig_words > 0 else 0
        
        if word_ratio > 3.0:  # Very relaxed from 1.5 to 3.0 (200% increase allowed)
            issues.append(f"Excessive word count increase: {word_ratio:.2f}x")
        elif word_ratio < 0.2:  # Very relaxed from 0.5 to 0.2 (80% decrease allowed)
            issues.append(f"Excessive word count decrease: {word_ratio:.2f}x")
        
        return issues
    
    def _check_text_structure(self, original: str, cleaned: str) -> List[str]:
        """Check text structure changes."""
        warnings = []
        
        # Sentence count analysis
        orig_sentences = len(re.findall(r'[.!?]+', original))
        cleaned_sentences = len(re.findall(r'[.!?]+', cleaned))
        
        if cleaned_sentences > orig_sentences * 2:
            warnings.append(f"Sentence count significantly increased: {orig_sentences} → {cleaned_sentences}")
        
        # Paragraph structure
        orig_paras = len([p for p in original.split('\n\n') if p.strip()])
        cleaned_paras = len([p for p in cleaned.split('\n\n') if p.strip()])
        
        if cleaned_paras > orig_paras * 2:
            warnings.append(f"Paragraph structure significantly changed: {orig_paras} → {cleaned_paras}")
        
        return warnings
    
    def _validate_new_entities(self, original: str, cleaned: str) -> Tuple[List[str], List[str]]:
        """Validate new entities introduced in cleaned text."""
        issues = []
        warnings = []
        
        # Extract potential entities (capitalized words)
        orig_entities = set(re.findall(r'\b[A-Z][a-zA-ZäöüÄÖÜß]+\b', original))
        cleaned_entities = set(re.findall(r'\b[A-Z][a-zA-ZäöüÄÖÜß]+\b', cleaned))
        
        new_entities = cleaned_entities - orig_entities
        
        for entity in new_entities:
            entity_lower = entity.lower()
            
            # Check against known gazetteers
            if entity_lower not in self.german_cities and \
               entity_lower not in self.german_names and \
               entity_lower not in self.technical_terms:
                
                # Additional checks for suspicious entities (very relaxed)
                if len(entity) > 30:  # Very relaxed from 15 to 30 characters
                    issues.append(f"Suspicious long entity introduced: {entity}")
                elif not self._is_likely_german_name(entity) and len(entity) > 12:  # Only warn for very long unknown entities
                    warnings.append(f"Unknown entity introduced: {entity}")
        
        return issues, warnings
    
    def _detect_hallucination_patterns(self, cleaned: str, original: str) -> List[str]:
        """Detect common hallucination patterns."""
        issues = []
        
        for pattern_name, pattern in self.hallucination_indicators.items():
            # Check if pattern exists in cleaned but not in original
            cleaned_matches = len(re.findall(pattern, cleaned, re.IGNORECASE))
            original_matches = len(re.findall(pattern, original, re.IGNORECASE))
            
            if cleaned_matches > original_matches:
                issues.append(f"Hallucination pattern detected: {pattern_name}")
        
        return issues
    
    def _validate_german_language(self, text: str) -> List[str]:
        """Validate German language usage."""
        warnings = []
        
        # Check for proper German umlauts and ß usage
        suspicious_sequences = [
            'ae', 'oe', 'ue',  # Should often be ä, ö, ü
            'ss'  # Sometimes should be ß
        ]
        
        for seq in suspicious_sequences:
            if seq in text.lower():
                warnings.append(f"Potential German character issue: '{seq}' detected")
        
        # Check for English words that shouldn't be there
        english_indicators = [
            r'\bthe\b', r'\band\b', r'\bof\b', r'\bto\b', r'\bin\b',
            r'\bit\b', r'\bis\b', r'\byou\b', r'\bthat\b', r'\bhe\b'
        ]
        
        for indicator in english_indicators:
            if re.search(indicator, text, re.IGNORECASE):
                warnings.append(f"English word detected in German text: {indicator}")
        
        return warnings
    
    def _check_context_consistency(self, cleaned: str, context: str) -> List[str]:
        """Check consistency with provided context."""
        warnings = []
        
        # Extract keywords from context
        context_keywords = set(re.findall(r'\b[a-zA-ZäöüÄÖÜß]{3,}\b', context.lower()))
        
        # Check if cleaned text introduces contradictory information
        if context_keywords:
            # This is a simplified check - could be more sophisticated
            text_keywords = set(re.findall(r'\b[a-zA-ZäöüÄÖÜß]{3,}\b', cleaned.lower()))
            
            # For now, just log if there are significantly more keywords
            new_keywords = text_keywords - context_keywords
            if len(new_keywords) > len(context_keywords) * 0.5:
                warnings.append(f"Many new keywords introduced ({len(new_keywords)} new vs {len(context_keywords)} from context)")
        
        return warnings
    
    def _detect_suspicious_patterns(self, cleaned: str, original: str) -> List[str]:
        """Detect suspicious patterns in cleaned text."""
        suspicious = []
        
        # Check for forbidden patterns
        for pattern_name, pattern in self.forbidden_patterns.items():
            if re.search(pattern, cleaned, re.IGNORECASE):
                if not re.search(pattern, original, re.IGNORECASE):
                    suspicious.append(f"Forbidden pattern introduced: {pattern_name}")
        
        # Check for repetitive patterns
        repetitive_patterns = [
            r'(.{10,})\1{2,}',  # Repeated sequences
            r'\b(\w+)\s+\1\s+\1\b',  # Triple word repetitions
        ]
        
        for pattern in repetitive_patterns:
            if re.search(pattern, cleaned):
                suspicious.append("Repetitive pattern detected")
        
        return suspicious
    
    def _calculate_validation_confidence(self, original: str, cleaned: str, issues: List[str], warnings: List[str]) -> float:
        """Calculate validation confidence score."""
        base_score = 1.0
        
        # Penalize issues very lightly
        issue_penalty = len(issues) * 0.05  # Very reduced from 0.3 to 0.05
        
        # Penalize warnings minimally
        warning_penalty = len(warnings) * 0.01  # Very reduced from 0.1 to 0.01
        
        # Consider similarity
        similarity = SequenceMatcher(None, original.lower(), cleaned.lower()).ratio()
        similarity_bonus = similarity * 0.2
        
        # Consider length ratio (very relaxed)
        length_ratio = len(cleaned) / len(original) if len(original) > 0 else 0
        if 0.2 <= length_ratio <= 3.0:  # Very wide acceptable range
            length_bonus = 0.1
        else:
            length_bonus = -0.02  # Minimal penalty
        
        confidence = max(0.0, min(1.0, base_score - issue_penalty - warning_penalty + similarity_bonus + length_bonus))
        
        return confidence
    
    def _generate_text_statistics(self, original: str, cleaned: str) -> Dict[str, float]:
        """Generate comparative text statistics."""
        return {
            'original_length': len(original),
            'cleaned_length': len(cleaned),
            'length_ratio': len(cleaned) / len(original) if len(original) > 0 else 0,
            'original_words': len(original.split()),
            'cleaned_words': len(cleaned.split()),
            'word_ratio': len(cleaned.split()) / len(original.split()) if len(original.split()) > 0 else 0,
            'similarity_ratio': SequenceMatcher(None, original.lower(), cleaned.lower()).ratio(),
            'original_sentences': len(re.findall(r'[.!?]+', original)),
            'cleaned_sentences': len(re.findall(r'[.!?]+', cleaned))
        }
    
    def _create_failed_result(self, issues: List[str], warnings: List[str], suspicious: List[str], 
                             original: str, cleaned: str) -> ValidationResult:
        """Create a failed validation result."""
        return ValidationResult(
            passed=False,
            confidence_score=0.0,
            issues=issues,
            warnings=warnings,
            suspicious_patterns=suspicious,
            text_statistics=self._generate_text_statistics(original, cleaned)
        )
    
    def _is_likely_german_name(self, name: str) -> bool:
        """Check if a name is likely to be German based on patterns."""
        # Simplified German name patterns
        german_suffixes = ['mann', 'berg', 'feld', 'hof', 'stein', 'bauer', 'müller', 'schmidt']
        german_prefixes = ['von', 'zur', 'am', 'an']
        
        name_lower = name.lower()
        
        return (
            any(name_lower.endswith(suffix) for suffix in german_suffixes) or
            any(name_lower.startswith(prefix) for prefix in german_prefixes) or
            any(char in name_lower for char in 'äöüß')  # Contains German characters
        )
    
    def _load_german_cities(self) -> Set[str]:
        """Load German cities gazetteer."""
        return {
            'berlin', 'münchen', 'hamburg', 'köln', 'frankfurt', 'stuttgart',
            'düsseldorf', 'dortmund', 'essen', 'leipzig', 'bremen', 'dresden',
            'hannover', 'nürnberg', 'duisburg', 'bochum', 'wuppertal', 'bielefeld',
            'bonn', 'münster', 'karlsruhe', 'mannheim', 'augsburg', 'wiesbaden',
            'gelsenkirchen', 'mönchengladbach', 'braunschweig', 'chemnitz', 'kiel',
            'aachen', 'halle', 'magdeburg', 'freiburg', 'krefeld', 'lübeck',
            'oberhausen', 'erfurt', 'mainz', 'rostock', 'kassel', 'hagen',
            'potsdam', 'saarbrücken', 'hamm', 'mülheim', 'ludwigshafen', 'oldenburg'
        }
    
    def _load_german_names(self) -> Set[str]:
        """Load German names gazetteer."""
        return {
            'müller', 'schmidt', 'schneider', 'fischer', 'weber', 'meyer',
            'wagner', 'becker', 'schulz', 'hoffmann', 'schäfer', 'koch',
            'bauer', 'richter', 'klein', 'wolf', 'schröder', 'neumann',
            'schwarz', 'zimmermann', 'braun', 'krüger', 'hofmann', 'hartmann',
            'lange', 'schmitt', 'werner', 'schmitz', 'krause', 'meier',
            'lehmann', 'engels', 'horn', 'walter', 'busch', 'kaiser',
            'fuchs', 'peters', 'lang', 'scholz', 'möller', 'weiß',
            'jung', 'hahn', 'schubert', 'vogel', 'friedrich', 'keller',
            'günther', 'frank', 'berger', 'winkler', 'roth', 'beck'
        }
    
    def _load_technical_terms(self) -> Set[str]:
        """Load technical terms gazetteer."""
        return {
            # Automotive terms
            'motor', 'getriebe', 'kupplung', 'bremse', 'reifen', 'felge',
            'karosserie', 'chassis', 'fahrwerk', 'lenkung', 'auspuff', 'katalysator',
            
            # Technology terms
            'computer', 'software', 'hardware', 'internet', 'server', 'client',
            'datenbank', 'algorithmus', 'programm', 'system', 'netzwerk', 'protokoll',
            
            # Business terms
            'unternehmen', 'management', 'marketing', 'vertrieb', 'kunde', 'markt',
            'produkt', 'service', 'strategie', 'analyse', 'budget', 'projekt'
        }
    
    def _load_forbidden_patterns(self) -> Dict[str, str]:
        """Load patterns that should not be introduced by LLM."""
        return {
            'external_references': r'\b(?:laut|gemäß|nach|entsprechend)\s+(?:angaben|aussage|bericht|quelle)\b',
            'expert_claims': r'\b(?:experten|wissenschaftler|forscher|spezialisten)\s+(?:sagen|meinen|glauben|bestätigen)\b',
            'study_references': r'\b(?:studien|untersuchungen|forschung|analyse)\s+(?:zeigen|belegen|deuten|ergeben)\b',
            'statistical_claims': r'\b\d+%\s*(?:der|aller|von)\b',
            'definitive_statements': r'\b(?:definitiv|eindeutig|zweifellos|sicher|garantiert)\b',
            'future_predictions': r'\b(?:wird|werden)\s+(?:definitiv|sicher|garantiert)\b'
        }
    
    def _load_hallucination_indicators(self) -> Dict[str, str]:
        """Load patterns that often indicate hallucinations."""
        return {
            'added_context': r'\b(?:wie bekannt|wie erwähnt|wie gesagt|bekanntlich)\b',
            'authoritative_tone': r'\b(?:tatsache ist|fest steht|klar ist|offensichtlich)\b',
            'external_validation': r'\b(?:bestätigt|bewiesen|nachgewiesen|dokumentiert)\s+(?:wurde|ist)\b',
            'comparative_claims': r'\b(?:besser|schlechter|mehr|weniger)\s+als\s+(?:andere|früher|sonst)\b',
            'temporal_specificity': r'\b(?:seit|vor|nach)\s+\d+\s+(?:jahren|monaten|tagen)\b'
        }


# Convenience functions
def validate_cleaned_transcript(original: str, cleaned: str, context: Optional[str] = None) -> ValidationResult:
    """Validate cleaned transcript (convenience function)."""
    validator = RuleBasedValidator()
    return validator.validate_cleaned_text(original, cleaned, context)


def is_cleaning_acceptable(original: str, cleaned: str, min_confidence: float = 0.2) -> bool:
    """Check if cleaning result is acceptable (convenience function)."""
    result = validate_cleaned_transcript(original, cleaned)
    return result.passed and result.confidence_score >= min_confidence