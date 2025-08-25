#!/usr/bin/env python3
"""
Test script for relaxed LLM cleaning functionality.
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_relaxed_cleaning():
    """Test with more challenging texts to see relaxed behavior."""
    try:
        # Test environment
        from dotenv import load_dotenv
        load_dotenv()
        
        from app.llm_cleaning import get_llm_cleaner
        from app.rule_based_validation import RuleBasedValidator
        
        cleaner = get_llm_cleaner()
        validator = RuleBasedValidator()
        
        # More challenging test texts
        test_cases = [
            {
                "name": "Heavy filler words",
                "text": "äh also äh das ist äh wirklich äh ein test mit äh sehr vielen äh füllwörtern und äh repetitionen repetitionen äh die entfernt werden sollten äh"
            },
            {
                "name": "Poor punctuation and structure",
                "text": "der motor hat probleme mit der kupplung und das getriebe macht komische geräusche also definitiv reparaturbedürftig aber vielleicht kann man es noch reparieren"
            },
            {
                "name": "Mixed German orthography",
                "text": "muenchen ist eine schoene stadt in bayern deutschland mit vielen sehenswuerdigkeiten strasse weiss dass"
            },
            {
                "name": "Technical automotive content",
                "text": "der bmw motor hat ein problem mit dem turbolader und die einspritzduesen sind verschmutzt ausserdem ist die kupplung verschlissen"
            }
        ]
        
        print("Testing Relaxed LLM Cleaning")
        print("=" * 50)
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\nTest {i}: {test_case['name']}")
            print("-" * 30)
            print(f"Original: {test_case['text']}")
            
            # Clean with LLM
            cleaning_result = cleaner.clean_transcript(test_case['text'], context="Automotive repair video")
            print(f"Cleaned:  {cleaning_result.cleaned_text}")
            print(f"LLM Check: {'PASS' if cleaning_result.hallucination_check_passed else 'FAIL'}")
            print(f"Confidence: {cleaning_result.confidence_score:.3f}")
            
            # Validate with rules
            validation_result = validator.validate_cleaned_text(
                test_case['text'], 
                cleaning_result.cleaned_text, 
                context="Automotive video"
            )
            print(f"Validation: {'PASS' if validation_result.passed else 'FAIL'}")
            print(f"Val. Confidence: {validation_result.confidence_score:.3f}")
            
            if cleaning_result.warnings:
                print(f"Warnings: {len(cleaning_result.warnings)} total")
                
            if validation_result.issues:
                print(f"Issues: {validation_result.issues}")
            
            # Calculate final decision
            final_passed = cleaning_result.hallucination_check_passed and validation_result.passed
            
            results.append({
                'name': test_case['name'],
                'llm_passed': cleaning_result.hallucination_check_passed,
                'validation_passed': validation_result.passed,
                'final_passed': final_passed,
                'llm_confidence': cleaning_result.confidence_score,
                'validation_confidence': validation_result.confidence_score
            })
            
            print(f"FINAL RESULT: {'ACCEPTED' if final_passed else 'REJECTED'}")
        
        # Summary
        print("\n" + "=" * 50)
        print("SUMMARY")
        print("=" * 50)
        
        total_tests = len(results)
        llm_passes = sum(1 for r in results if r['llm_passed'])
        validation_passes = sum(1 for r in results if r['validation_passed'])
        final_passes = sum(1 for r in results if r['final_passed'])
        
        avg_llm_conf = sum(r['llm_confidence'] for r in results) / total_tests
        avg_val_conf = sum(r['validation_confidence'] for r in results) / total_tests
        
        print(f"Total tests: {total_tests}")
        print(f"LLM passes: {llm_passes}/{total_tests} ({llm_passes/total_tests*100:.1f}%)")
        print(f"Validation passes: {validation_passes}/{total_tests} ({validation_passes/total_tests*100:.1f}%)")
        print(f"Final passes: {final_passes}/{total_tests} ({final_passes/total_tests*100:.1f}%)")
        print(f"Avg LLM confidence: {avg_llm_conf:.3f}")
        print(f"Avg validation confidence: {avg_val_conf:.3f}")
        
        # Success if we accept more cases than before
        if final_passes >= total_tests * 0.75:  # 75% pass rate target
            print(f"\nSUCCESS: High acceptance rate with relaxed checks!")
            return True
        else:
            print(f"\nNEEDS ADJUSTMENT: Only {final_passes/total_tests*100:.1f}% acceptance rate")
            return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_relaxed_cleaning():
        print("\nRelaxed cleaning tests PASSED")
    else:
        print("\nRelaxed cleaning tests FAILED")