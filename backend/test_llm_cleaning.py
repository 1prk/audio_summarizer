#!/usr/bin/env python3
"""
Test script for LLM cleaning functionality.

This script tests the LLM cleaning pipeline without requiring a full video transcription.
"""

import os
import sys
import json
import time
from dataclasses import asdict

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_llm_cleaning():
    """Test LLM cleaning with sample German text."""
    try:
        from app.llm_cleaning import get_llm_cleaner, CleaningResult
        from app.rule_based_validation import RuleBasedValidator
        
        # Sample text that mimics Whisper output with common issues
        test_texts = [
            "äh also das ist äh ein test mit ahm vielen füllwörtern und ahm repetitionen repetitionen die entfernt werden sollten",
            "strasse sollte zu straße werden und weiss zu weiß also das sind typische deutsche rechtschreibfehler",
            "der motor hat äh probleme mit der kupplung und das getriebe macht komische geräusche äh also definitiv reparaturbedürftig",
            "münchen ist eine schöne stadt in bayern deutschland mit vielen sehenswürdigkeiten und museen",
        ]
        
        print("Testing LLM cleaning functionality...")
        print("=" * 60)
        
        # Test 1: Initialize cleaner
        print("Test 1: Initializing LLM cleaner...")
        try:
            cleaner = get_llm_cleaner()
            print("[OK] LLM cleaner initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize cleaner: {e}")
            return False
        
        # Test 2: Initialize validator
        print("\nTest 2: Initializing rule-based validator...")
        try:
            validator = RuleBasedValidator()
            print("[OK] Rule-based validator initialized successfully")
        except Exception as e:
            print(f"[ERROR] Failed to initialize validator: {e}")
            return False
        
        # Test 3: Clean sample texts
        print("\nTest 3: Processing sample texts...")
        all_results = []
        
        for i, test_text in enumerate(test_texts, 1):
            print(f"\n--- Sample {i} ---")
            print(f"Original: {test_text}")
            
            try:
                # Clean with LLM
                start_time = time.time()
                cleaning_result = cleaner.clean_transcript(test_text, context="Test video about automotive issues")
                processing_time = time.time() - start_time
                
                print(f"Cleaned:  {cleaning_result.cleaned_text}")
                print(f"Hallucination check: {'✅ PASSED' if cleaning_result.hallucination_check_passed else '❌ FAILED'}")
                print(f"Confidence: {cleaning_result.confidence_score:.2f}")
                print(f"Processing time: {processing_time:.2f}s")
                
                if cleaning_result.changes_made:
                    print(f"Changes: {', '.join(cleaning_result.changes_made)}")
                
                if cleaning_result.warnings:
                    print(f"Warnings: {', '.join(cleaning_result.warnings[:3])}")
                
                # Validate with rule-based checker
                validation_result = validator.validate_cleaned_text(
                    test_text, 
                    cleaning_result.cleaned_text, 
                    context="Test video"
                )
                
                print(f"Validation: {'✅ PASSED' if validation_result.passed else '❌ FAILED'}")
                print(f"Validation confidence: {validation_result.confidence_score:.2f}")
                
                if validation_result.issues:
                    print(f"Issues: {', '.join(validation_result.issues)}")
                
                all_results.append({
                    'original': test_text,
                    'cleaned': cleaning_result.cleaned_text,
                    'cleaning_passed': cleaning_result.hallucination_check_passed,
                    'validation_passed': validation_result.passed,
                    'processing_time': processing_time
                })
                
            except Exception as e:
                print(f"❌ Error processing text: {e}")
                return False
        
        # Test 4: Summary statistics
        print("\n" + "=" * 60)
        print("📊 SUMMARY STATISTICS")
        print("=" * 60)
        
        total_texts = len(all_results)
        successful_cleanings = sum(1 for r in all_results if r['cleaning_passed'])
        successful_validations = sum(1 for r in all_results if r['validation_passed'])
        avg_processing_time = sum(r['processing_time'] for r in all_results) / total_texts
        
        print(f"Total texts processed: {total_texts}")
        print(f"Successful cleanings: {successful_cleanings}/{total_texts} ({successful_cleanings/total_texts*100:.1f}%)")
        print(f"Successful validations: {successful_validations}/{total_texts} ({successful_validations/total_texts*100:.1f}%)")
        print(f"Average processing time: {avg_processing_time:.2f}s per text")
        
        # Test 5: Export results
        print("\nTest 5: Exporting results...")
        try:
            results_file = os.path.join(os.path.dirname(__file__), 'llm_cleaning_test_results.json')
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'test_timestamp': time.time(),
                    'total_texts': total_texts,
                    'successful_cleanings': successful_cleanings,
                    'successful_validations': successful_validations,
                    'average_processing_time': avg_processing_time,
                    'results': all_results
                }, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Results exported to: {results_file}")
        except Exception as e:
            print(f"⚠️  Failed to export results: {e}")
        
        # Determine overall success
        success_rate = successful_cleanings / total_texts
        validation_rate = successful_validations / total_texts
        
        if success_rate >= 0.8 and validation_rate >= 0.8:
            print("\n🎉 OVERALL RESULT: SUCCESS")
            print("LLM cleaning pipeline is working correctly!")
            return True
        else:
            print(f"\n⚠️  OVERALL RESULT: PARTIAL SUCCESS")
            print(f"Some issues detected. Success rate: {success_rate*100:.1f}%, Validation rate: {validation_rate*100:.1f}%")
            return False
            
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure all required packages are installed (openai, etc.)")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_environment():
    """Test that the environment is properly configured."""
    print("🔧 Testing environment configuration...")
    
    # Check .env file
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        print(f"✅ Found .env file: {env_file}")
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv(env_file)
        
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key and api_key.startswith('sk-'):
            print("✅ OpenAI API key found in environment")
        else:
            print("❌ OpenAI API key not found or invalid")
            print("Please set OPENAI_API_KEY in the .env file")
            return False
    else:
        print(f"❌ .env file not found: {env_file}")
        return False
    
    # Check required modules
    required_modules = ['openai', 'python-dotenv']
    for module in required_modules:
        try:
            __import__(module.replace('-', '_'))
            print(f"✅ {module} module available")
        except ImportError:
            print(f"❌ {module} module not installed")
            print(f"Run: pip install {module}")
            return False
    
    return True


if __name__ == "__main__":
    print("🚀 LLM Cleaning Pipeline Test")
    print("=" * 60)
    
    # Test environment first
    if not test_environment():
        print("\n❌ Environment test failed. Please fix the issues above.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # Run main test
    if test_llm_cleaning():
        print("\n✅ All tests completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above for details.")
        sys.exit(1)