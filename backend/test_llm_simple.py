#!/usr/bin/env python3
"""
Simple test script for LLM cleaning functionality.
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_simple():
    """Simple test of LLM cleaning."""
    try:
        # Test environment
        from dotenv import load_dotenv
        load_dotenv()
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            print("ERROR: OPENAI_API_KEY not found in environment")
            return False
        
        print(f"API key found: {api_key[:10]}...")
        
        # Test imports
        from app.llm_cleaning import get_llm_cleaner
        from app.rule_based_validation import RuleBasedValidator
        
        print("Imports successful")
        
        # Initialize components
        cleaner = get_llm_cleaner()
        validator = RuleBasedValidator()
        
        print("Components initialized")
        
        # Test with simple text
        test_text = "aeh das ist ein test mit fuellwoertern"
        print(f"Original: {test_text}")
        
        result = cleaner.clean_transcript(test_text)
        print(f"Cleaned: {result.cleaned_text}")
        print(f"Passed: {result.hallucination_check_passed}")
        print(f"Confidence: {result.confidence_score}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Simple LLM Cleaning Test")
    print("=" * 40)
    
    if test_simple():
        print("\nSUCCESS: Test completed")
    else:
        print("\nFAILED: Test failed")