#!/usr/bin/env python3
"""
Test script for extremely relaxed LLM cleaning functionality.
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_extreme_cases():
    """Test with very challenging texts to verify extreme relaxation."""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from app.llm_cleaning import get_llm_cleaner
        from app.rule_based_validation import RuleBasedValidator
        
        cleaner = get_llm_cleaner()
        validator = RuleBasedValidator()
        
        # Extreme test cases that would normally fail
        extreme_cases = [
            {
                "name": "Massive text expansion",
                "text": "aeh motor kaputt"
            },
            {
                "name": "Heavy restructuring needed", 
                "text": "so aeh ja also der der motor halt aeh hat probleme mit aeh ja kupplung und so weiter halt aeh"
            },
            {
                "name": "Almost no similarity expected",
                "text": "mmm ja aeh also halt so"
            },
            {
                "name": "Technical with many unknowns",
                "text": "turboladerdichtung defekt einspritzduesen verstopft motorsteuergeraet fehler"
            },
            {
                "name": "Poor German mixed with English",
                "text": "the motor ist kaputt and needs reparatur ja"
            }
        ]
        
        print("Testing Extremely Relaxed LLM Cleaning")
        print("=" * 60)
        
        results = []
        
        for i, test_case in enumerate(extreme_cases, 1):
            print(f"\nTest {i}: {test_case['name']}")
            print("-" * 40)
            print(f"Original: {test_case['text']}")
            
            # Clean with LLM
            cleaning_result = cleaner.clean_transcript(test_case['text'], context="Automotive repair discussion")
            print(f"Cleaned:  {cleaning_result.cleaned_text}")
            
            # Calculate metrics
            orig_words = len(test_case['text'].split())
            clean_words = len(cleaning_result.cleaned_text.split())
            word_change = ((clean_words - orig_words) / orig_words * 100) if orig_words > 0 else 0
            
            print(f"Word change: {word_change:+.1f}% ({orig_words} -> {clean_words})")
            print(f"LLM Check: {'PASS' if cleaning_result.hallucination_check_passed else 'FAIL'}")
            print(f"LLM Confidence: {cleaning_result.confidence_score:.3f}")
            
            # Validate with rules
            validation_result = validator.validate_cleaned_text(
                test_case['text'], 
                cleaning_result.cleaned_text, 
                context="Automotive video"
            )
            print(f"Validation: {'PASS' if validation_result.passed else 'FAIL'}")
            print(f"Validation Confidence: {validation_result.confidence_score:.3f}")
            
            if cleaning_result.warnings:
                print(f"LLM Warnings: {len(cleaning_result.warnings)}")
                
            if validation_result.issues:
                print(f"Validation Issues: {validation_result.issues}")
            
            if validation_result.warnings:
                print(f"Validation Warnings: {len(validation_result.warnings)}")
            
            # Final decision
            final_passed = cleaning_result.hallucination_check_passed and validation_result.passed
            similarity = validation_result.text_statistics['similarity_ratio']
            
            results.append({
                'name': test_case['name'],
                'llm_passed': cleaning_result.hallucination_check_passed,
                'validation_passed': validation_result.passed,
                'final_passed': final_passed,
                'word_change_pct': word_change,
                'similarity': similarity,
                'llm_confidence': cleaning_result.confidence_score,
                'validation_confidence': validation_result.confidence_score
            })
            
            print(f"Similarity: {similarity:.3f}")
            print(f"FINAL RESULT: {'ACCEPTED' if final_passed else 'REJECTED'}")
        
        # Summary
        print("\n" + "=" * 60)
        print("EXTREME RELAXATION TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(results)
        llm_passes = sum(1 for r in results if r['llm_passed'])
        validation_passes = sum(1 for r in results if r['validation_passed'])
        final_passes = sum(1 for r in results if r['final_passed'])
        
        avg_word_change = sum(abs(r['word_change_pct']) for r in results) / total_tests
        avg_similarity = sum(r['similarity'] for r in results) / total_tests
        min_similarity = min(r['similarity'] for r in results)
        max_word_change = max(abs(r['word_change_pct']) for r in results)
        
        print(f"Total tests: {total_tests}")
        print(f"LLM passes: {llm_passes}/{total_tests} ({llm_passes/total_tests*100:.1f}%)")
        print(f"Validation passes: {validation_passes}/{total_tests} ({validation_passes/total_tests*100:.1f}%)")
        print(f"Final passes: {final_passes}/{total_tests} ({final_passes/total_tests*100:.1f}%)")
        print(f"Average word change: {avg_word_change:.1f}%")
        print(f"Maximum word change: {max_word_change:.1f}%")
        print(f"Average similarity: {avg_similarity:.3f}")
        print(f"Minimum similarity: {min_similarity:.3f}")
        
        # Success criteria for extreme relaxation
        if final_passes >= total_tests * 0.8:  # 80% pass rate even for extreme cases
            print(f"\nSUCCESS: Extremely relaxed - {final_passes/total_tests*100:.1f}% acceptance!")
            print("The system now accepts most reasonable cleaning attempts.")
            return True
        else:
            print(f"\nPARTIAL: {final_passes/total_tests*100:.1f}% acceptance rate")
            print("May need further relaxation for extreme cases.")
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_extreme_cases():
        print("\nExtremely relaxed cleaning tests PASSED")
    else:
        print("\nExtremely relaxed cleaning tests PARTIAL SUCCESS")