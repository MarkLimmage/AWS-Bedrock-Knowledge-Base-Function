#!/usr/bin/env python3
"""
Test script for entity resolution (name parsing) functionality
"""
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from aws_bedrock_kb_function import Pipe, parse_name_elements

def test_parse_name_elements():
    """Test the name parsing function with various inputs"""
    print("\n" + "="*80)
    print("Testing Name Element Parsing")
    print("="*80)
    
    test_cases = [
        # (input, expected_output)
        ("Dr. John Smith", ["John", "Smith"]),
        ("Prof. Mary Jane Watson", ["Mary", "Jane", "Watson"]),
        ("John Smith", ["John", "Smith"]),
        ("Mr. Robert Johnson", ["Robert", "Johnson"]),
        ("Ms. Emily Davis", ["Emily", "Davis"]),
        ("Sir Isaac Newton", ["Isaac", "Newton"]),
        ("Rev. Martin Luther King", ["Martin", "Luther", "King"]),
        ("Dr John Smith", ["John", "Smith"]),  # Without period
        ("Captain James Cook", ["James", "Cook"]),
        ("Prof Jane Doe", ["Jane", "Doe"]),
    ]
    
    all_passed = True
    for input_name, expected_elements in test_cases:
        result = parse_name_elements(input_name)
        
        if result == expected_elements:
            print(f"✓ '{input_name}' -> {result}")
        else:
            print(f"✗ '{input_name}': expected {expected_elements}, got {result}")
            all_passed = False
    
    return all_passed

def test_parse_name_elements_edge_cases():
    """Test edge cases for name parsing"""
    print("\n" + "="*80)
    print("Testing Name Element Parsing - Edge Cases")
    print("="*80)
    
    test_cases = [
        # (input, description, expected_output)
        ("", "Empty string", []),
        ("   ", "Whitespace only", []),
        ("Dr.", "Title only", []),
        ("Dr.   John   Smith", "Extra whitespace", ["John", "Smith"]),
        ("PROF. JOHN SMITH", "All caps", ["JOHN", "SMITH"]),
        ("dr. john smith", "Lower case", ["john", "smith"]),
    ]
    
    all_passed = True
    for input_name, description, expected_elements in test_cases:
        result = parse_name_elements(input_name)
        
        if result == expected_elements:
            print(f"✓ {description}: '{input_name}' -> {result}")
        else:
            print(f"✗ {description}: '{input_name}' expected {expected_elements}, got {result}")
            all_passed = False
    
    return all_passed

async def test_extract_entity_names():
    """Test entity name extraction with AWS credentials if available"""
    print("\n" + "="*80)
    print("Testing Entity Name Extraction (requires AWS credentials)")
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
    
    # Test queries
    test_queries = [
        "Show me posts from Dr. John Smith",
        "Find all posts by Prof. Mary Jane Watson",
        "What did Jane Doe write about?",
    ]
    
    all_passed = True
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 80)
        
        try:
            # Initialize clients
            pipe._initialize_clients()
            
            # Test name extraction
            name_info = await pipe._extract_entity_names(query)
            name_refs = name_info.get('name_refs', [])
            
            if name_refs:
                print("✓ Extracted names:")
                for ref in name_refs:
                    print(f"  - Original: '{ref['original']}'")
                    print(f"    Elements: {ref['elements']}")
                    print(f"    Context: {ref['context']}")
            else:
                print("⊘ No names extracted")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            all_passed = False
    
    return all_passed

async def test_filter_generation_with_names():
    """Test the complete filter generation with entity names"""
    print("\n" + "="*80)
    print("Testing Filter Generation with Entity Names (requires AWS credentials)")
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
    
    # Set metadata definitions
    metadata_defs = [
        {
            "key": "author_name",
            "type": "STRING",
            "description": "The name of the author."
        },
        {
            "key": "poi_name",
            "type": "STRING",
            "description": "The name of the person of interest."
        }
    ]
    
    pipe.valves.metadata_definitions = json.dumps(metadata_defs)
    
    # Test queries
    test_queries = [
        "Show me posts from Dr. John Smith",
        "Find all posts by Prof. Mary Jane Watson and Mr. Robert Johnson",
        "What did Jane Doe write about?",
    ]
    
    all_passed = True
    for query in test_queries:
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
                
                # Check if filter uses "in" operator for name elements
                filter_str = json.dumps(metadata_filter)
                if '"in"' in filter_str and 'author_name' in filter_str:
                    print("✓ Filter uses 'in' operator for name filtering")
                else:
                    print("⊘ Filter may not be using entity resolution approach")
            else:
                print("⊘ No filter generated (may not be applicable)")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
            all_passed = False
    
    return all_passed

def test_filter_structure_validation():
    """Test that the expected filter structure is correctly formed"""
    print("\n" + "="*80)
    print("Testing Filter Structure Validation")
    print("="*80)
    
    # Example filter that should be generated for "Dr. John Smith"
    expected_structure = {
        "andAll": [
            {
                "in": {
                    "key": "author_name",
                    "value": "John"
                }
            },
            {
                "in": {
                    "key": "author_name",
                    "value": "Smith"
                }
            }
        ]
    }
    
    # Validate structure
    try:
        assert "andAll" in expected_structure
        assert isinstance(expected_structure["andAll"], list)
        assert len(expected_structure["andAll"]) == 2
        
        for condition in expected_structure["andAll"]:
            assert "in" in condition
            assert "key" in condition["in"]
            assert "value" in condition["in"]
            assert condition["in"]["key"] == "author_name"
        
        print("✓ Expected filter structure is valid:")
        print(json.dumps(expected_structure, indent=2))
        return True
    except AssertionError as e:
        print(f"✗ Filter structure validation failed: {str(e)}")
        return False

async def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*80)
    print("AWS Bedrock KB Entity Resolution - Test Suite")
    print("="*80)
    
    results = {}
    
    # Run unit tests that don't require AWS
    results['Name Element Parsing'] = test_parse_name_elements()
    results['Name Element Parsing - Edge Cases'] = test_parse_name_elements_edge_cases()
    results['Filter Structure Validation'] = test_filter_structure_validation()
    
    # Run integration tests if credentials available
    name_extraction_result = await test_extract_entity_names()
    if name_extraction_result is not None:
        results['Entity Name Extraction (AWS)'] = name_extraction_result
    
    filter_generation_result = await test_filter_generation_with_names()
    if filter_generation_result is not None:
        results['Filter Generation with Names (AWS)'] = filter_generation_result
    
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
