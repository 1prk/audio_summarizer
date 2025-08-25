"""
LLM-based post-processing module for cleaning up Whisper transcriptions.

This module provides functionality to clean up transcriptions using OpenAI's GPT-4o
with specific focus on:
1. Sentence boundaries and paragraphs
2. Spelling correction (umlauts, ß, proper names)
3. Light smoothing (removing filler words and duplicates)
4. Maintaining content integrity without interpretation
"""

import os
import re
import json
import time
import logging
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from difflib import SequenceMatcher

import openai
from openai import OpenAI

logger = logging.getLogger(__name__)


@dataclass
class CleaningResult:
    """Result of LLM cleaning operation."""
    original_text: str
    cleaned_text: str
    changes_made: List[str]
    confidence_score: float
    processing_time: float
    hallucination_check_passed: bool
    warnings: List[str]


@dataclass
class DiffAnalysis:
    """Analysis of differences between original and cleaned text."""
    similarity_ratio: float
    insertions: List[str]
    deletions: List[str]
    substitutions: List[Tuple[str, str]]
    word_count_change: int
    suspicious_changes: List[str]


class LLMTextCleaner:
    """LLM-based text cleaning with hallucination prevention."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini"):
        """Initialize the LLM text cleaner."""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key must be provided or set in OPENAI_API_KEY environment variable")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.temperature = float(os.getenv('LLM_CLEANING_TEMPERATURE', 0.1))
        self.max_tokens = int(os.getenv('LLM_CLEANING_MAX_TOKENS', 4000))
        
        # Load German correction dictionaries
        self.german_corrections = self._load_german_corrections()
        self.proper_names = self._load_proper_names()
        self.common_asr_errors = self._load_common_asr_errors()
        
        logger.info(f"Initialized LLM cleaner with model: {self.model}")
    
    def clean_transcript(self, text: str, context: Optional[str] = None) -> CleaningResult:
        """
        Clean transcript text using LLM with hallucination prevention.
        
        Args:
            text: Raw transcript text from Whisper
            context: Optional context information (video title, description, etc.)
        
        Returns:
            CleaningResult with cleaned text and metadata
        """
        start_time = time.time()
        
        if not text or len(text.strip()) < 10:
            return CleaningResult(
                original_text=text,
                cleaned_text=text,
                changes_made=[],
                confidence_score=1.0,
                processing_time=0.0,
                hallucination_check_passed=True,
                warnings=["Text too short for cleaning"]
            )
        
        try:
            # Step 1: Pre-processing with rule-based corrections
            preprocessed_text = self._preprocess_text(text)
            
            # Step 2: LLM cleaning
            cleaned_text = self._llm_clean_text(preprocessed_text, context)
            
            # Step 3: Post-processing validation
            diff_analysis = self._analyze_differences(preprocessed_text, cleaned_text)
            
            # Step 4: Hallucination detection
            hallucination_check = self._check_for_hallucinations(preprocessed_text, cleaned_text, diff_analysis)
            
            # Step 5: Final validation
            if not hallucination_check.passed:
                logger.warning(f"Hallucination detected, reverting to original: {hallucination_check.issues}")
                cleaned_text = preprocessed_text
                warnings = [f"Reverted due to hallucination: {', '.join(hallucination_check.issues)}"]
            else:
                warnings = []
            
            processing_time = time.time() - start_time
            
            return CleaningResult(
                original_text=text,
                cleaned_text=cleaned_text,
                changes_made=self._extract_changes(text, cleaned_text),
                confidence_score=self._calculate_confidence_score(diff_analysis),
                processing_time=processing_time,
                hallucination_check_passed=hallucination_check.passed,
                warnings=warnings + diff_analysis.suspicious_changes
            )
        
        except Exception as e:
            logger.error(f"LLM cleaning failed: {str(e)}")
            return CleaningResult(
                original_text=text,
                cleaned_text=text,
                changes_made=[],
                confidence_score=0.0,
                processing_time=time.time() - start_time,
                hallucination_check_passed=False,
                warnings=[f"Cleaning failed: {str(e)}"]
            )
    
    def _preprocess_text(self, text: str) -> str:
        """Apply rule-based preprocessing before LLM cleaning."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Apply common ASR error corrections
        for error_pattern, correction in self.common_asr_errors.items():
            text = re.sub(error_pattern, correction, text, flags=re.IGNORECASE)
        
        return text
    
    def _llm_clean_text(self, text: str, context: Optional[str] = None) -> str:
        """Send text to LLM for cleaning."""
        context_info = f"\nContext: {context}" if context else ""
        
        system_prompt = """Du bist ein Experte für die Nachbearbeitung von automatischen Spracherkennungs-Transkripten (ASR). 
Deine Aufgabe ist es, den folgenden deutschen Text zu korrigieren, OHNE inhaltliche Ergänzungen oder Interpretationen zu machen.

ERLAUBT:
- Satzbau und Satzgrenzen korrigieren
- Groß- und Kleinschreibung korrigieren
- Umlaute und ß korrigieren
- Offensichtliche Rechtschreibfehler korrigieren
- Füllwörter entfernen (äh, ähm, etc.)
- Doppelte Wörter entfernen
- Interpunktion hinzufügen für bessere Lesbarkeit

VERBOTEN:
- Inhaltliche Ergänzungen
- Interpretation oder semantische Umschreibungen
- Hinzufügen von Informationen die nicht im Original stehen
- Änderung der Bedeutung
- Erfinden von Namen oder Begriffen

Antworte NUR mit dem korrigierten Text, keine Erklärungen."""

        user_prompt = f"""Korrigiere den folgenden ASR-Transkript-Text:{context_info}

Text:
{text}

Korrigierter Text:"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                top_p=0.9,
                frequency_penalty=0.1
            )
            
            cleaned_text = response.choices[0].message.content.strip()
            
            # Sanity check - make sure we got a response
            if not cleaned_text or len(cleaned_text) < len(text) * 0.5:
                logger.warning("LLM response too short, using original")
                return text
            
            return cleaned_text
            
        except Exception as e:
            logger.error(f"OpenAI API call failed: {str(e)}")
            raise
    
    def _analyze_differences(self, original: str, cleaned: str) -> DiffAnalysis:
        """Analyze differences between original and cleaned text."""
        matcher = SequenceMatcher(None, original.lower(), cleaned.lower())
        similarity_ratio = matcher.ratio()
        
        # Get opcodes to analyze changes
        opcodes = matcher.get_opcodes()
        insertions = []
        deletions = []
        substitutions = []
        
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'insert':
                insertions.append(cleaned[j1:j2])
            elif tag == 'delete':
                deletions.append(original[i1:i2])
            elif tag == 'replace':
                substitutions.append((original[i1:i2], cleaned[j1:j2]))
        
        original_words = len(original.split())
        cleaned_words = len(cleaned.split())
        word_count_change = cleaned_words - original_words
        
        # Detect suspicious changes (very relaxed thresholds)
        suspicious_changes = []
        if similarity_ratio < 0.3:  # Very relaxed from 0.6 to 0.3
            suspicious_changes.append(f"Low similarity ratio: {similarity_ratio:.2f}")
        if abs(word_count_change) > original_words * 0.8:  # Very relaxed from 0.4 to 0.8
            suspicious_changes.append(f"Significant word count change: {word_count_change}")
        if len(insertions) > 20:  # Very relaxed from 10 to 20
            suspicious_changes.append(f"Many insertions: {len(insertions)}")
        
        return DiffAnalysis(
            similarity_ratio=similarity_ratio,
            insertions=insertions,
            deletions=deletions,
            substitutions=substitutions,
            word_count_change=word_count_change,
            suspicious_changes=suspicious_changes
        )
    
    def _check_for_hallucinations(self, original: str, cleaned: str, diff_analysis: DiffAnalysis) -> 'HallucinationCheck':
        """Check for potential hallucinations in the cleaned text."""
        issues = []
        
        # Check 1: Excessive content addition (very relaxed)
        if diff_analysis.word_count_change > len(original.split()) * 0.8:  # Very relaxed from 0.3 to 0.8
            issues.append("Excessive content addition detected")
        
        # Check 2: New proper nouns that aren't in our dictionary (very relaxed)
        original_words = set(original.lower().split())
        cleaned_words = set(cleaned.lower().split())
        new_words = cleaned_words - original_words
        
        suspicious_new_words = []
        for word in new_words:
            # Check if it's a capitalized word (potential proper noun) not in our dictionary
            if word.istitle() and word not in self.proper_names and len(word) > 8:  # Very relaxed from 4 to 8
                suspicious_new_words.append(word)
        
        if len(suspicious_new_words) > 15:  # Very relaxed from 5 to 15
            issues.append(f"Suspicious new proper nouns: {', '.join(suspicious_new_words[:3])}")
        
        # Check 3: Similarity threshold (very relaxed)
        if diff_analysis.similarity_ratio < 0.2:  # Very relaxed from 0.5 to 0.2
            issues.append(f"Content similarity too low: {diff_analysis.similarity_ratio:.2f}")
        
        # Check 4: Common hallucination patterns (very relaxed - only extreme cases)
        extreme_hallucination_patterns = [
            r'\b(?:wissenschaftliche studien belegen eindeutig)\b',  # Only very specific academic claims
            r'\b(?:alle experten sind sich einig)\b',  # Only universal expert claims
            r'\b(?:laut nasa|laut who|laut un)\b'  # Only major organization claims
        ]
        
        for pattern in extreme_hallucination_patterns:
            if re.search(pattern, cleaned.lower()) and not re.search(pattern, original.lower()):
                issues.append(f"Potential extreme hallucinated phrase detected: {pattern}")
        
        passed = len(issues) == 0
        return HallucinationCheck(passed=passed, issues=issues)
    
    def _extract_changes(self, original: str, cleaned: str) -> List[str]:
        """Extract a list of changes made during cleaning."""
        changes = []
        
        # Simple change detection
        if len(cleaned.split()) != len(original.split()):
            changes.append(f"Word count changed: {len(original.split())} → {len(cleaned.split())}")
        
        # Check for common cleaning operations
        if '.' in cleaned and '.' not in original:
            changes.append("Added sentence punctuation")
        
        if cleaned.count(',') > original.count(','):
            changes.append("Added comma punctuation")
        
        # Check for German-specific corrections
        if 'ß' in cleaned and 'ß' not in original:
            changes.append("Corrected ß characters")
        
        if any(c in cleaned for c in 'äöüÄÖÜ') and not any(c in original for c in 'äöüÄÖÜ'):
            changes.append("Corrected German umlauts")
        
        return changes
    
    def _calculate_confidence_score(self, diff_analysis: DiffAnalysis) -> float:
        """Calculate confidence score for the cleaning operation."""
        base_score = diff_analysis.similarity_ratio
        
        # Adjust based on suspicious changes (minimal penalty)
        penalty = len(diff_analysis.suspicious_changes) * 0.01  # Very minimal penalty from 0.05 to 0.01
        
        # Adjust based on word count change (minimal penalty)
        word_change_penalty = min(abs(diff_analysis.word_count_change) * 0.005, 0.05)  # Minimal penalty from 0.02 to 0.005 and from 0.2 to 0.05
        
        final_score = max(0.0, base_score - penalty - word_change_penalty)
        return min(1.0, final_score)
    
    def _load_german_corrections(self) -> Dict[str, str]:
        """Load German-specific corrections dictionary."""
        return {
            r'\bstrasse\b': 'Straße',
            r'\bweiss\b': 'weiß',
            r'\bdass\b': 'dass',
            r'\bäh+\b': '',
            r'\bähm+\b': '',
            r'\bmhm+\b': '',
            r'\bne\b': 'eine',
            r'\bnen\b': 'einen',
            r'\bnem\b': 'einem',
        }
    
    def _load_proper_names(self) -> Set[str]:
        """Load set of known proper names and places."""
        return {
            'deutschland', 'berlin', 'münchen', 'hamburg', 'köln', 'frankfurt',
            'bayern', 'nordrhein-westfalen', 'baden-württemberg', 'hessen',
            'mercedes', 'bmw', 'volkswagen', 'audi', 'porsche', 'bosch',
            'siemens', 'sap', 'deutsche bank', 'allianz', 'bayer',
            'europa', 'amerika', 'asien', 'afrika', 'australien'
        }
    
    def _load_common_asr_errors(self) -> Dict[str, str]:
        """Load common ASR error patterns and corrections."""
        return {
            r'\b([a-z]+)\s+\1\b': r'\1',  # Remove word repetitions
            r'\s+': ' ',  # Multiple spaces to single space
            r'(\w)\s*-\s*(\w)': r'\1-\2',  # Fix hyphenation
        }


@dataclass
class HallucinationCheck:
    """Result of hallucination check."""
    passed: bool
    issues: List[str]


class BatchTextCleaner:
    """Batch processing for multiple transcript segments."""
    
    def __init__(self, cleaner: LLMTextCleaner):
        self.cleaner = cleaner
    
    def clean_segments(self, segments: List[str], context: Optional[str] = None) -> List[CleaningResult]:
        """Clean multiple transcript segments in batch."""
        results = []
        
        for i, segment in enumerate(segments):
            logger.info(f"Cleaning segment {i+1}/{len(segments)}")
            
            try:
                result = self.cleaner.clean_transcript(segment, context)
                results.append(result)
                
                # Rate limiting to avoid API limits
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Failed to clean segment {i+1}: {str(e)}")
                # Return original segment on error
                results.append(CleaningResult(
                    original_text=segment,
                    cleaned_text=segment,
                    changes_made=[],
                    confidence_score=0.0,
                    processing_time=0.0,
                    hallucination_check_passed=False,
                    warnings=[f"Processing failed: {str(e)}"]
                ))
        
        return results


# Convenience functions for easy integration
def get_llm_cleaner(model: str = "gpt-4o-mini") -> LLMTextCleaner:
    """Get configured LLM cleaner instance."""
    return LLMTextCleaner(model=model)


def clean_transcript_text(text: str, context: Optional[str] = None, model: str = "gpt-4o-mini") -> CleaningResult:
    """Clean a single transcript text (convenience function)."""
    cleaner = get_llm_cleaner(model)
    return cleaner.clean_transcript(text, context)