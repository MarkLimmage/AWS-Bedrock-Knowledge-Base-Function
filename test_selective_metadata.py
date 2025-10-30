#!/usr/bin/env python3
"""
Test script to validate selective metadata inclusion in generation prompts.

This test validates Task 5 implementation: ensuring that only relevant metadata
is included in the context to optimize token usage.

Rules:
- Always include: source_uri, created_at_iso
- Only include if used in filter: all other metadata fields
"""
import asyncio
import json
import sys
from unittest.mock import Mock, patch, MagicMock
from aws_bedrock_kb_function import Pipe


async def test_no_filter_only_includes_always_fields():
    """Test that when no filter is used, only always-include fields are shown"""
    print("\n" + "="*80)
    print("Testing: No Filter - Only Always-Include Fields")
    print("="*80)
    
    # Create a mock retrieval response with various metadata fields
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
                    'category': 'technology',
                    'source_uri': 's3://my-bucket/docs/ml-guide.pdf',
                    'like_count': 42,
                    'author_handle': '@john'
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
            
            # Run the query WITHOUT metadata filtering
            await pipe.query_knowledge_base("What is machine learning?", None, "")
            
            # Validate that the prompt was captured
            if captured_prompt is None:
                print("✗ Failed to capture prompt sent to model")
                all_passed = False
            else:
                print("✓ Successfully captured prompt sent to model")
                
                # Check that always-include fields ARE present
                always_include_checks = [
                    ('created_at_iso', '2025-08-15T10:30:00Z'),
                    ('source_uri', 's3://my-bucket/docs/ml-guide.pdf'),
                ]
                
                print("\nChecking always-include fields ARE present:")
                for field, value in always_include_checks:
                    if field in captured_prompt and value in captured_prompt:
                        print(f"  ✓ Found {field}: {value}")
                    else:
                        print(f"  ✗ Missing {field}: {value}")
                        all_passed = False
                
                # Check that non-filter fields are NOT present (by checking their values)
                should_not_include = [
                    ('author_name', 'John Smith'),
                    ('created_at_unix', '1723719000'),
                    ('category', 'technology'),
                    ('like_count', '42'),
                    ('author_handle', '@john'),
                ]
                
                print("\nChecking non-filter fields are NOT present:")
                for field, value in should_not_include:
                    # Check for the metadata entry pattern "  - field: value"
                    metadata_pattern = f"  - {field}: {value}"
                    if metadata_pattern in captured_prompt:
                        print(f"  ✗ Field {field} should not be included but was found")
                        all_passed = False
                    else:
                        print(f"  ✓ Field {field} correctly excluded")
    
    return all_passed


async def test_with_filter_includes_filter_fields():
    """Test that when a filter is used, filter fields are included along with always-include fields"""
    print("\n" + "="*80)
    print("Testing: With Filter - Includes Filter Fields")
    print("="*80)
    
    # Create a mock retrieval response with various metadata fields
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
                    'category': 'technology',
                    'source_uri': 's3://my-bucket/docs/ml-guide.pdf',
                    'like_count': 42,
                    'author_handle': '@john'
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
    
    # Create pipe instance with metadata filtering enabled
    pipe = Pipe()
    pipe.valves.aws_access_key_id = 'test_key'
    pipe.valves.aws_secret_access_key = 'test_secret'
    pipe.valves.aws_region = 'us-east-1'
    pipe.valves.knowledge_base_id = 'test_kb_id'
    pipe.valves.enable_metadata_filtering = True
    
    # Track the prompt sent to invoke_model
    captured_prompt = None
    
    def mock_invoke_model(**kwargs):
        nonlocal captured_prompt
        request_body = json.loads(kwargs['body'])
        captured_prompt = request_body['messages'][0]['content']
        return mock_model_response
    
    # Mock filter generation to return a filter with specific fields
    async def mock_generate_filter(query):
        # Return a filter that uses author_name and like_count
        return {
            "andAll": [
                {
                    "in": {
                        "key": "author_name",
                        "value": ["John Smith"]
                    }
                },
                {
                    "greaterThan": {
                        "key": "like_count",
                        "value": 10
                    }
                }
            ]
        }
    
    # Run test
    all_passed = True
    
    with patch.object(pipe, 'bedrock_agent_client') as mock_agent_client:
        with patch.object(pipe, 'bedrock_client') as mock_bedrock_client:
            with patch.object(pipe, '_generate_metadata_filter', side_effect=mock_generate_filter):
                # Setup mocks
                mock_agent_client.retrieve.return_value = mock_retrieval_response
                mock_bedrock_client.invoke_model.side_effect = mock_invoke_model
                pipe._clients_initialized = True
                
                # Run the query WITH metadata filtering
                await pipe.query_knowledge_base("What is machine learning?", None, "")
                
                # Validate that the prompt was captured
                if captured_prompt is None:
                    print("✗ Failed to capture prompt sent to model")
                    all_passed = False
                else:
                    print("✓ Successfully captured prompt sent to model")
                    
                    # Check that always-include fields ARE present
                    always_include_checks = [
                        ('created_at_iso', '2025-08-15T10:30:00Z'),
                        ('source_uri', 's3://my-bucket/docs/ml-guide.pdf'),
                    ]
                    
                    print("\nChecking always-include fields ARE present:")
                    for field, value in always_include_checks:
                        if field in captured_prompt and value in captured_prompt:
                            print(f"  ✓ Found {field}: {value}")
                        else:
                            print(f"  ✗ Missing {field}: {value}")
                            all_passed = False
                    
                    # Check that filter fields ARE present
                    filter_fields_checks = [
                        ('author_name', 'John Smith'),
                        ('like_count', '42'),
                    ]
                    
                    print("\nChecking filter fields ARE present:")
                    for field, value in filter_fields_checks:
                        if field in captured_prompt and value in captured_prompt:
                            print(f"  ✓ Found {field}: {value}")
                        else:
                            print(f"  ✗ Missing {field}: {value}")
                            all_passed = False
                    
                    # Check that non-filter fields are NOT present (by checking for metadata pattern)
                    should_not_include = [
                        'created_at_unix',
                        'category',
                        'author_handle',
                    ]
                    
                    print("\nChecking non-filter fields are NOT present:")
                    for field in should_not_include:
                        # Check for metadata entry pattern "  - field:"
                        metadata_pattern = f"  - {field}:"
                        if metadata_pattern in captured_prompt:
                            print(f"  ✗ Field {field} should not be included but was found")
                            all_passed = False
                        else:
                            print(f"  ✓ Field {field} correctly excluded")
    
    return all_passed


async def test_with_datetime_filter():
    """Test that datetime filtering includes the appropriate datetime fields"""
    print("\n" + "="*80)
    print("Testing: With Datetime Filter")
    print("="*80)
    
    # Create a mock retrieval response with datetime fields
    mock_retrieval_response = {
        'retrievalResults': [
            {
                'content': {
                    'text': 'This document discusses recent events.'
                },
                'location': {
                    's3Location': {
                        'uri': 's3://my-bucket/docs/events.pdf'
                    }
                },
                'metadata': {
                    'author_name': 'Jane Doe',
                    'created_at_iso': '2025-08-01T10:00:00Z',
                    'created_at_unix': 1722502800,
                    'source_uri': 's3://my-bucket/docs/events.pdf',
                    'category': 'news'
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
    
    # Track the prompt
    captured_prompt = None
    
    def mock_invoke_model(**kwargs):
        nonlocal captured_prompt
        request_body = json.loads(kwargs['body'])
        captured_prompt = request_body['messages'][0]['content']
        return mock_model_response
    
    # Mock filter generation to return a datetime filter
    async def mock_generate_filter(query):
        return {
            "andAll": [
                {
                    "greaterThanOrEquals": {
                        "key": "created_at_unix",
                        "value": 1722470400
                    }
                },
                {
                    "lessThanOrEquals": {
                        "key": "created_at_unix",
                        "value": 1725148799
                    }
                }
            ]
        }
    
    # Run test
    all_passed = True
    
    with patch.object(pipe, 'bedrock_agent_client') as mock_agent_client:
        with patch.object(pipe, 'bedrock_client') as mock_bedrock_client:
            with patch.object(pipe, '_generate_metadata_filter', side_effect=mock_generate_filter):
                # Setup mocks
                mock_agent_client.retrieve.return_value = mock_retrieval_response
                mock_bedrock_client.invoke_model.side_effect = mock_invoke_model
                pipe._clients_initialized = True
                
                # Run the query
                await pipe.query_knowledge_base("Show me posts from August 2025", None, "")
                
                # Validate
                if captured_prompt is None:
                    print("✗ Failed to capture prompt")
                    all_passed = False
                else:
                    print("✓ Successfully captured prompt")
                    
                    # created_at_iso should always be included
                    if 'created_at_iso' in captured_prompt and '2025-08-01T10:00:00Z' in captured_prompt:
                        print("  ✓ Found created_at_iso (always-include)")
                    else:
                        print("  ✗ Missing created_at_iso")
                        all_passed = False
                    
                    # created_at_unix should be included because it's in the filter
                    if 'created_at_unix' in captured_prompt and '1722502800' in captured_prompt:
                        print("  ✓ Found created_at_unix (used in filter)")
                    else:
                        print("  ✗ Missing created_at_unix")
                        all_passed = False
                    
                    # author_name and category should NOT be included
                    should_not_include = ['author_name', 'category']
                    for field in should_not_include:
                        metadata_pattern = f"  - {field}:"
                        if metadata_pattern in captured_prompt:
                            print(f"  ✗ Field {field} incorrectly included")
                            all_passed = False
                    
                    if not any(f"  - {field}:" in captured_prompt for field in should_not_include):
                        print("  ✓ Non-filter fields correctly excluded")
                    else:
                        print("  ✗ Non-filter fields incorrectly included")
                        all_passed = False
    
    return all_passed


async def test_metadata_absence_handling():
    """Test that the system handles documents without metadata gracefully"""
    print("\n" + "="*80)
    print("Testing: Metadata Absence Handling")
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
    """Run all selective metadata tests"""
    print("\n" + "="*80)
    print("Selective Metadata Inclusion - Test Suite")
    print("="*80)
    
    results = {}
    
    # Run tests
    results['No Filter - Only Always-Include'] = await test_no_filter_only_includes_always_fields()
    results['With Filter - Includes Filter Fields'] = await test_with_filter_includes_filter_fields()
    results['With Datetime Filter'] = await test_with_datetime_filter()
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
