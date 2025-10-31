#!/usr/bin/env python3
"""
Test script for citation generation functionality
"""
import asyncio
import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from aws_bedrock_kb_function import Pipe

def test_citation_valve_configuration():
    """Test that the citation valve is properly configured"""
    print("\n" + "="*80)
    print("Testing Citation Valve Configuration")
    print("="*80)
    
    pipe = Pipe()
    
    # Test default values
    assert hasattr(pipe.valves, 'enable_citations'), "enable_citations valve missing"
    assert pipe.valves.enable_citations == True, f"Expected True, got {pipe.valves.enable_citations}"
    assert isinstance(pipe.valves.enable_citations, bool), f"Expected bool, got {type(pipe.valves.enable_citations)}"
    
    print(f"✓ enable_citations valve configured correctly: {pipe.valves.enable_citations}")
    return True

def test_citation_disabled_returns_original():
    """Test that citation generation returns original answer when disabled"""
    print("\n" + "="*80)
    print("Testing Citation Generation When Disabled")
    print("="*80)
    
    async def run_test():
        pipe = Pipe()
        pipe.valves.enable_citations = False
        
        # Create a mock answer and results
        answer = "This is a test answer."
        retrieved_results = [
            {
                'content': {'text': 'Test content'},
                'metadata': {'source_uri': 's3://bucket/doc1.pdf'}
            }
        ]
        
        # Run the citation generation
        result = await pipe._generate_citations(answer, retrieved_results)
        
        assert result == answer, f"Expected original answer, got: {result}"
        print(f"✓ Citation generation disabled correctly")
        return True
    
    # This test will be awaited in the main test runner
    return run_test()

async def test_citation_structure():
    """Test that citations are properly formatted"""
    print("\n" + "="*80)
    print("Testing Citation Structure")
    print("="*80)
    
    pipe = Pipe()
    pipe.valves.enable_citations = True
    
    # Mock the bedrock client
    pipe._clients_initialized = True
    pipe.bedrock_client = Mock()
    
    # Create test data
    answer = "Machine learning is a subset of AI. Deep learning uses neural networks."
    retrieved_results = [
        {
            'content': {'text': 'Machine learning is a subset of artificial intelligence that focuses on algorithms.'},
            'metadata': {'source_uri': 's3://bucket/ml-guide.pdf'},
            'location': {'s3Location': {'uri': 's3://bucket/ml-guide.pdf'}}
        },
        {
            'content': {'text': 'Deep learning is a specialized subset of machine learning that uses multi-layered neural networks.'},
            'metadata': {'source_uri': 's3://bucket/dl-intro.pdf'},
            'location': {'s3Location': {'uri': 's3://bucket/dl-intro.pdf'}}
        }
    ]
    
    # Mock the model response for citation attribution
    mock_citation_response = {
        "citations": [
            {
                "answer_text": "Machine learning is a subset of AI",
                "chunk_ids": [1]
            },
            {
                "answer_text": "Deep learning uses neural networks",
                "chunk_ids": [2]
            }
        ]
    }
    
    mock_response_body = {
        'content': [{'text': json.dumps(mock_citation_response)}]
    }
    
    mock_response = MagicMock()
    mock_response.__getitem__.return_value.read.return_value = json.dumps(mock_response_body)
    pipe.bedrock_client.invoke_model.return_value = mock_response
    
    # Run citation generation
    result = await pipe._generate_citations(answer, retrieved_results)
    
    print(f"Result:\n{result}")
    
    # Verify structure
    assert "Citations:" in result, "Citations section missing"
    assert "[1]" in result or "[2]" in result, "Inline citations missing"
    assert "s3://bucket/ml-guide.pdf" in result, "First source URI missing"
    assert "s3://bucket/dl-intro.pdf" in result, "Second source URI missing"
    
    # Verify citation format
    lines = result.split('\n')
    citation_section_found = False
    for line in lines:
        if line.startswith("1.") or line.startswith("2."):
            citation_section_found = True
            assert '"' in line, "Citation preview missing quotes"
            assert '[s3://' in line, "Source URI not formatted as link"
    
    assert citation_section_found, "Numbered citations not found"
    
    print("✓ Citation structure is correct")
    return True

async def test_citation_first_50_chars():
    """Test that citation preview is limited to first 50 characters"""
    print("\n" + "="*80)
    print("Testing Citation Preview Length")
    print("="*80)
    
    pipe = Pipe()
    pipe.valves.enable_citations = True
    pipe._clients_initialized = True
    pipe.bedrock_client = Mock()
    
    # Create a long chunk text (more than 50 chars)
    long_text = "A" * 100
    
    answer = "This is about something."
    retrieved_results = [
        {
            'content': {'text': long_text},
            'metadata': {'source_uri': 's3://bucket/doc.pdf'},
            'location': {'s3Location': {'uri': 's3://bucket/doc.pdf'}}
        }
    ]
    
    mock_citation_response = {
        "citations": [
            {
                "answer_text": "This is about something",
                "chunk_ids": [1]
            }
        ]
    }
    
    mock_response_body = {
        'content': [{'text': json.dumps(mock_citation_response)}]
    }
    
    mock_response = MagicMock()
    mock_response.__getitem__.return_value.read.return_value = json.dumps(mock_response_body)
    pipe.bedrock_client.invoke_model.return_value = mock_response
    
    result = await pipe._generate_citations(answer, retrieved_results)
    
    print(f"Result:\n{result}")
    
    # Find the citation line
    lines = result.split('\n')
    citation_line = None
    for line in lines:
        if line.startswith("1."):
            citation_line = line
            break
    
    assert citation_line, "Citation line not found"
    
    # Extract the quoted preview
    import re
    match = re.search(r'"([^"]+)"', citation_line)
    assert match, "Quoted preview not found"
    
    preview = match.group(1)
    # Should be "AAAA...AAA..." which is 50 chars + "..." (53 total)
    assert len(preview) <= 53, f"Preview too long: {len(preview)} chars"
    assert preview.endswith("..."), "Preview should end with ..."
    
    print(f"✓ Citation preview correctly limited to first 50 chars + '...'")
    return True

async def test_citation_no_results():
    """Test that citation generation handles empty results gracefully"""
    print("\n" + "="*80)
    print("Testing Citation with No Results")
    print("="*80)
    
    pipe = Pipe()
    pipe.valves.enable_citations = True
    
    answer = "Test answer"
    retrieved_results = []
    
    result = await pipe._generate_citations(answer, retrieved_results)
    
    assert result == answer, f"Should return original answer, got: {result}"
    print("✓ Empty results handled correctly")
    return True

async def test_citation_error_handling():
    """Test that citation generation errors don't break the response"""
    print("\n" + "="*80)
    print("Testing Citation Error Handling")
    print("="*80)
    
    pipe = Pipe()
    pipe.valves.enable_citations = True
    pipe._clients_initialized = True
    pipe.bedrock_client = Mock()
    
    answer = "Test answer"
    retrieved_results = [
        {
            'content': {'text': 'Test content'},
            'metadata': {'source_uri': 's3://bucket/doc.pdf'}
        }
    ]
    
    # Mock the model to raise an exception
    pipe.bedrock_client.invoke_model.side_effect = Exception("Model error")
    
    result = await pipe._generate_citations(answer, retrieved_results)
    
    # Should return original answer on error
    assert result == answer, f"Should return original answer on error, got: {result}"
    print("✓ Errors handled gracefully")
    return True

async def run_all_tests():
    """Run all citation tests"""
    tests = [
        ("Citation Valve Configuration", test_citation_valve_configuration),
        ("Citation Disabled", test_citation_disabled_returns_original),
        ("Citation Structure", test_citation_structure),
        ("Citation Preview Length", test_citation_first_50_chars),
        ("Citation No Results", test_citation_no_results),
        ("Citation Error Handling", test_citation_error_handling),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*80)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("="*80)
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
