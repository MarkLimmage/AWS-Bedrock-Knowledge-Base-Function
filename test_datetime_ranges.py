#!/usr/bin/env python3
"""
Test script for datetime range parsing functionality (Task 4)
"""
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from aws_bedrock_kb_function import Pipe, parse_datetime_range


def test_parse_datetime_range():
    """Test the datetime range parsing function"""
    print("\n" + "="*80)
    print("Testing DateTime Range Parsing Function")
    print("="*80)
    
    test_cases = [
        # (input_range, expected_start_iso, expected_end_iso)
        (
            "from 2025-08-01T00:00:00Z to 2025-08-31T23:59:59Z",
            "2025-08-01T00:00:00Z",
            "2025-08-31T23:59:59Z"
        ),
        (
            "from 2025-09-04T06:39:00Z to 2025-09-04T06:39:59Z",
            "2025-09-04T06:39:00Z",
            "2025-09-04T06:39:59Z"
        ),
        (
            "from 2025-01-01T00:00:00Z to 2025-12-31T23:59:59Z",
            "2025-01-01T00:00:00Z",
            "2025-12-31T23:59:59Z"
        ),
        (
            "from 2025-03-15T00:00:00Z to 2025-03-15T23:59:59Z",
            "2025-03-15T00:00:00Z",
            "2025-03-15T23:59:59Z"
        ),
    ]
    
    all_passed = True
    for input_range, expected_start_iso, expected_end_iso in test_cases:
        start_iso, start_unix, end_iso, end_unix = parse_datetime_range(input_range)
        
        # Check if parsing succeeded
        if start_iso is None or end_iso is None:
            print(f"✗ Failed to parse: {input_range}")
            all_passed = False
            continue
        
        # Check if values match expected
        if start_iso == expected_start_iso and end_iso == expected_end_iso:
            print(f"✓ Parsed range correctly:")
            print(f"  Input: {input_range}")
            print(f"  Start: {start_iso} (Unix: {start_unix})")
            print(f"  End:   {end_iso} (Unix: {end_unix})")
        else:
            print(f"✗ Mismatch for '{input_range}':")
            print(f"  Expected start: {expected_start_iso}, got: {start_iso}")
            print(f"  Expected end: {expected_end_iso}, got: {end_iso}")
            all_passed = False
    
    return all_passed


def test_range_format_validation():
    """Test that invalid range formats are handled gracefully"""
    print("\n" + "="*80)
    print("Testing Range Format Validation")
    print("="*80)
    
    invalid_cases = [
        "2025-08-01T00:00:00Z",  # Not a range
        "invalid range format",
        "",
        "from X to Y",
    ]
    
    all_passed = True
    for invalid_input in invalid_cases:
        start_iso, start_unix, end_iso, end_unix = parse_datetime_range(invalid_input)
        
        if start_iso is None and end_iso is None:
            print(f"✓ Correctly rejected invalid input: '{invalid_input}'")
        else:
            print(f"✗ Should have rejected: '{invalid_input}'")
            all_passed = False
    
    return all_passed


async def test_extraction_with_ranges():
    """Test the datetime extraction with range support"""
    print("\n" + "="*80)
    print("Testing DateTime Extraction with Ranges (requires AWS credentials)")
    print("="*80)
    
    if not os.getenv('AWS_ACCESS_KEY_ID'):
        print("⊘ Skipping - AWS credentials not configured")
        return None
    
    pipe = Pipe()
    
    # Configure the pipe with credentials
    pipe.valves.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    pipe.valves.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    pipe.valves.aws_region = os.getenv('AWS_REGION', 'us-east-1')
    pipe.valves.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID', 'test_kb_id')
    
    # Test queries with different granularities
    test_queries = [
        ("Show me posts from August 2025", "month"),
        ("Find posts from September 4th, 2025", "day"),
        ("What was posted on March 15, 2025 at 6:39 AM?", "minute"),
        ("Show me posts from 2025", "year"),
    ]
    
    all_passed = True
    for query, granularity in test_queries:
        print(f"\nQuery: {query}")
        print(f"Expected granularity: {granularity}")
        print("-" * 80)
        
        try:
            # Initialize clients
            pipe._initialize_clients()
            
            # Test datetime extraction
            datetime_info = await pipe._extract_datetime_references(query)
            datetime_refs = datetime_info.get('datetime_refs', [])
            
            if datetime_refs:
                print(f"✓ Extracted {len(datetime_refs)} range(s):")
                for ref in datetime_refs:
                    print(f"  Original: {ref['original']}")
                    print(f"  Start: {ref['start_iso']} (Unix: {ref['start_unix']})")
                    print(f"  End:   {ref['end_iso']} (Unix: {ref['end_unix']})")
                    
                    # Verify it's a proper range (end > start)
                    if ref['end_unix'] > ref['start_unix']:
                        print(f"  ✓ Valid range (duration: {ref['end_unix'] - ref['start_unix']} seconds)")
                    else:
                        print(f"  ✗ Invalid range (end <= start)")
                        all_passed = False
            else:
                print("⊘ No datetime references extracted")
                all_passed = False
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            all_passed = False
    
    return all_passed


async def test_filter_generation_with_ranges():
    """Test that filter generation uses ranges properly"""
    print("\n" + "="*80)
    print("Testing Filter Generation with Ranges (requires AWS credentials)")
    print("="*80)
    
    if not os.getenv('AWS_ACCESS_KEY_ID'):
        print("⊘ Skipping - AWS credentials not configured")
        return None
    
    pipe = Pipe()
    
    # Configure the pipe with credentials
    pipe.valves.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
    pipe.valves.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
    pipe.valves.aws_region = os.getenv('AWS_REGION', 'us-east-1')
    pipe.valves.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID', 'test_kb_id')
    
    # Enable metadata filtering
    pipe.valves.enable_metadata_filtering = True
    pipe.valves.filter_model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    
    # Set metadata definitions with Unix timestamp support
    metadata_defs = [
        {
            "key": "created_at_unix",
            "type": "NUMBER",
            "description": "The timestamp from when the document was created in Unix epoch format"
        },
        {
            "key": "author_name",
            "type": "STRING",
            "description": "The name of the author."
        }
    ]
    
    pipe.valves.metadata_definitions = json.dumps(metadata_defs)
    
    # Test query with month granularity
    query = "Show me posts from August 2025"
    
    print(f"\nQuery: {query}")
    print("-" * 80)
    
    try:
        # Initialize clients
        pipe._initialize_clients()
        
        # Test filter generation
        metadata_filter = await pipe._generate_metadata_filter(query)
        
        if metadata_filter:
            print("✓ Generated filter:")
            print(json.dumps(metadata_filter, indent=2))
            
            # Check if the filter uses range conditions (greaterThanOrEquals and lessThanOrEquals)
            filter_str = json.dumps(metadata_filter)
            has_gte = "greaterThanOrEquals" in filter_str or "greaterThan" in filter_str
            has_lte = "lessThanOrEquals" in filter_str or "lessThan" in filter_str
            
            if has_gte and has_lte:
                print("✓ Filter uses range conditions (start and end)")
                return True
            else:
                print("✗ Filter does not use proper range conditions")
                return False
        else:
            print("⊘ No filter generated")
            return None
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*80)
    print("AWS Bedrock KB DateTime Range Parsing - Test Suite (Task 4)")
    print("="*80)
    
    results = {}
    
    # Run unit tests that don't require AWS
    results['Parse DateTime Range'] = test_parse_datetime_range()
    results['Range Format Validation'] = test_range_format_validation()
    
    # Run integration tests if credentials available
    extraction_result = await test_extraction_with_ranges()
    if extraction_result is not None:
        results['DateTime Extraction with Ranges (AWS)'] = extraction_result
    
    filter_result = await test_filter_generation_with_ranges()
    if filter_result is not None:
        results['Filter Generation with Ranges (AWS)'] = filter_result
    
    # Print summary
    print("\n" + "="*80)
    print("Test Results Summary")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print("-" * 80)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
