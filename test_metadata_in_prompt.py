#!/usr/bin/env python3
"""
Test script to validate that metadata is properly included in generation prompts.

This test validates Task 3 implementation: ensuring the generation phase is aware
of the relevance of the retrieved context to the original question by including
metadata explicitly in the prompt.
"""
import asyncio
import json
import sys
from unittest.mock import Mock, patch, MagicMock
from aws_bedrock_kb_function import Pipe


async def test_metadata_extraction_and_prompt_construction():
    """Test that metadata is properly extracted from results and included in prompt"""
    print("\n" + "="*80)
    print("Testing Metadata Extraction and Prompt Construction")
    print("="*80)
    
    # Create a mock retrieval response with metadata
    mock_retrieval_response = {
        'retrievalResults': [
            {
                'content': {
                    'text': 'This document discusses machine learning algorithms.'
                },
                'location': {
                    's3Location': {
                        'uri': 's3://my-bucket/docs/ml-guide.pdf'
                    }
                },
                'metadata': {
                    'author_name': 'John Smith',
                    'created_at_iso': '2025-08-15T10:30:00Z',
                    'created_at_unix': 1723719000,
                    'category': 'technology'
                }
            },
            {
                'content': {
                    'text': 'Deep learning is a subset of machine learning.'
                },
                'location': {
                    's3Location': {
                        'uri': 's3://my-bucket/docs/deep-learning.pdf'
                    }
                },
                'metadata': {
                    'author_name': 'Jane Doe',
                    'created_at_iso': '2025-09-01T14:00:00Z',
                    'created_at_unix': 1725199200,
                    'category': 'AI'
                }
            }
        ]
    }
    
    # Mock the model response
    mock_model_response = {
        'body': MagicMock(read=lambda: json.dumps({
            'content': [{'text': 'This is a test response.'}]
        }).encode())
    }
    
    # Create pipe instance
    pipe = Pipe()
    pipe.valves.aws_access_key_id = 'test_key'
    pipe.valves.aws_secret_access_key = 'test_secret'
    pipe.valves.aws_region = 'us-east-1'
    pipe.valves.knowledge_base_id = 'test_kb_id'
    
    # Track the prompt sent to invoke_model
    captured_prompt = None
    
    def mock_invoke_model(**kwargs):
        nonlocal captured_prompt
        request_body = json.loads(kwargs['body'])
        captured_prompt = request_body['messages'][0]['content']
        return mock_model_response
    
    # Run test
    all_passed = True
    
    with patch.object(pipe, 'bedrock_agent_client') as mock_agent_client:
        with patch.object(pipe, 'bedrock_client') as mock_bedrock_client:
            # Setup mocks
            mock_agent_client.retrieve.return_value = mock_retrieval_response
            mock_bedrock_client.invoke_model.side_effect = mock_invoke_model
            pipe._clients_initialized = True
            
            # Run the query
            await pipe.query_knowledge_base("What is machine learning?", None, "")
            
            # Validate that the prompt was captured
            if captured_prompt is None:
                print("✗ Failed to capture prompt sent to model")
                all_passed = False
            else:
                print("✓ Successfully captured prompt sent to model")
                
                # Check that metadata is included in the prompt
                metadata_checks = [
                    ('author_name', 'John Smith'),
                    ('author_name', 'Jane Doe'),
                    ('created_at_iso', '2025-08-15T10:30:00Z'),
                    ('created_at_iso', '2025-09-01T14:00:00Z'),
                    ('category', 'technology'),
                    ('category', 'AI'),
                ]
                
                print("\nChecking metadata presence in prompt:")
                for field, value in metadata_checks:
                    if field in captured_prompt and value in captured_prompt:
                        print(f"  ✓ Found {field}: {value}")
                    else:
                        print(f"  ✗ Missing {field}: {value}")
                        all_passed = False
                
                # Check that content is included
                content_checks = [
                    'machine learning algorithms',
                    'Deep learning is a subset',
                ]
                
                print("\nChecking content presence in prompt:")
                for content in content_checks:
                    if content in captured_prompt:
                        print(f"  ✓ Found content: '{content}'")
                    else:
                        print(f"  ✗ Missing content: '{content}'")
                        all_passed = False
                
                # Check that source locations are included
                source_checks = [
                    's3://my-bucket/docs/ml-guide.pdf',
                    's3://my-bucket/docs/deep-learning.pdf',
                ]
                
                print("\nChecking source locations in prompt:")
                for source in source_checks:
                    if source in captured_prompt:
                        print(f"  ✓ Found source: {source}")
                    else:
                        print(f"  ✗ Missing source: {source}")
                        all_passed = False
                
                # Check that prompt contains instruction about using metadata
                metadata_instruction_keywords = [
                    'metadata',
                    'consider',
                    'context',
                ]
                
                print("\nChecking metadata usage instructions in prompt:")
                for keyword in metadata_instruction_keywords:
                    if keyword.lower() in captured_prompt.lower():
                        print(f"  ✓ Found keyword: '{keyword}'")
                    else:
                        print(f"  ✗ Missing keyword: '{keyword}'")
                        all_passed = False
                
                # Print the full prompt for inspection
                print("\n" + "-"*80)
                print("Full prompt sent to model:")
                print("-"*80)
                print(captured_prompt)
                print("-"*80)
    
    return all_passed


async def test_metadata_absence_handling():
    """Test that the system handles documents without metadata gracefully"""
    print("\n" + "="*80)
    print("Testing Metadata Absence Handling")
    print("="*80)
    
    # Create a mock retrieval response without metadata
    mock_retrieval_response = {
        'retrievalResults': [
            {
                'content': {
                    'text': 'Document without metadata.'
                },
                'location': {
                    's3Location': {
                        'uri': 's3://my-bucket/docs/no-metadata.pdf'
                    }
                }
                # Note: No metadata field
            }
        ]
    }
    
    # Mock the model response
    mock_model_response = {
        'body': MagicMock(read=lambda: json.dumps({
            'content': [{'text': 'Response for document without metadata.'}]
        }).encode())
    }
    
    # Create pipe instance
    pipe = Pipe()
    pipe.valves.aws_access_key_id = 'test_key'
    pipe.valves.aws_secret_access_key = 'test_secret'
    pipe.valves.aws_region = 'us-east-1'
    pipe.valves.knowledge_base_id = 'test_kb_id'
    
    # Track the prompt
    captured_prompt = None
    
    def mock_invoke_model(**kwargs):
        nonlocal captured_prompt
        request_body = json.loads(kwargs['body'])
        captured_prompt = request_body['messages'][0]['content']
        return mock_model_response
    
    # Run test
    all_passed = True
    
    with patch.object(pipe, 'bedrock_agent_client') as mock_agent_client:
        with patch.object(pipe, 'bedrock_client') as mock_bedrock_client:
            # Setup mocks
            mock_agent_client.retrieve.return_value = mock_retrieval_response
            mock_bedrock_client.invoke_model.side_effect = mock_invoke_model
            pipe._clients_initialized = True
            
            # Run the query
            result = await pipe.query_knowledge_base("Test query", None, "")
            
            # Validate that it didn't crash
            if result and not result.startswith("Error"):
                print("✓ System handled documents without metadata gracefully")
            else:
                print(f"✗ System failed with: {result}")
                all_passed = False
            
            # Check that content is still included
            if captured_prompt and 'Document without metadata' in captured_prompt:
                print("✓ Document content is still included in prompt")
            else:
                print("✗ Document content is missing from prompt")
                all_passed = False
            
            # Check that source is still included
            if captured_prompt and 's3://my-bucket/docs/no-metadata.pdf' in captured_prompt:
                print("✓ Source location is still included in prompt")
            else:
                print("✗ Source location is missing from prompt")
                all_passed = False
    
    return all_passed


async def run_all_tests():
    """Run all metadata-in-prompt tests"""
    print("\n" + "="*80)
    print("Metadata in Prompt - Test Suite")
    print("="*80)
    
    results = {}
    
    # Run tests
    results['Metadata Extraction'] = await test_metadata_extraction_and_prompt_construction()
    results['Metadata Absence Handling'] = await test_metadata_absence_handling()
    
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
