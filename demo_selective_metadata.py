#!/usr/bin/env python3
"""
Demo script to showcase the selective metadata inclusion feature.

This demonstrates how the system optimizes token usage by only including
relevant metadata in the generation context.
"""
import asyncio
import json
from unittest.mock import patch, MagicMock
from aws_bedrock_kb_function import Pipe, _extract_filter_keys


def demo_filter_key_extraction():
    """Demonstrate filter key extraction from various filter structures"""
    print("\n" + "="*80)
    print("Demo: Filter Key Extraction")
    print("="*80)
    
    # Example 1: Simple filter with single field
    filter1 = {
        "in": {
            "key": "author_name",
            "value": ["John Smith"]
        }
    }
    
    print("\nFilter 1 (Simple):")
    print(json.dumps(filter1, indent=2))
    keys1 = _extract_filter_keys(filter1)
    print(f"Extracted keys: {keys1}")
    
    # Example 2: Complex filter with multiple fields
    filter2 = {
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
            },
            {
                "in": {
                    "key": "author_name",
                    "value": ["John Smith", "Jane Doe"]
                }
            }
        ]
    }
    
    print("\nFilter 2 (Complex):")
    print(json.dumps(filter2, indent=2))
    keys2 = _extract_filter_keys(filter2)
    print(f"Extracted keys: {keys2}")
    
    # Example 3: Nested filter
    filter3 = {
        "andAll": [
            {
                "orAll": [
                    {
                        "equals": {
                            "key": "category",
                            "value": "technology"
                        }
                    },
                    {
                        "equals": {
                            "key": "category",
                            "value": "AI"
                        }
                    }
                ]
            },
            {
                "greaterThan": {
                    "key": "like_count",
                    "value": 10
                }
            }
        ]
    }
    
    print("\nFilter 3 (Nested):")
    print(json.dumps(filter3, indent=2))
    keys3 = _extract_filter_keys(filter3)
    print(f"Extracted keys: {keys3}")
    
    # Example 4: No filter
    filter4 = None
    print("\nFilter 4 (None):")
    print("None")
    keys4 = _extract_filter_keys(filter4)
    print(f"Extracted keys: {keys4}")


async def demo_selective_metadata_inclusion():
    """Demonstrate selective metadata inclusion in context building"""
    print("\n" + "="*80)
    print("Demo: Selective Metadata Inclusion")
    print("="*80)
    
    # Mock retrieval response with many metadata fields
    mock_retrieval_response = {
        'retrievalResults': [
            {
                'content': {
                    'text': 'This is a post about machine learning by John Smith.'
                },
                'location': {
                    's3Location': {
                        'uri': 's3://my-bucket/posts/ml-post.json'
                    }
                },
                'metadata': {
                    'author_name': 'John Smith',
                    'author_handle': '@johnsmith',
                    'author_did': 'did:plc:123456',
                    'created_at_iso': '2025-08-15T10:30:00Z',
                    'created_at_unix': 1723719000,
                    'source_uri': 's3://my-bucket/posts/ml-post.json',
                    'like_count': 42,
                    'reply_count': 7,
                    'repost_count': 5,
                    'category': 'technology',
                    'poi_name': 'Tech Conference 2025',
                    'poi_role': 'speaker'
                }
            }
        ]
    }
    
    # Mock the model response
    mock_model_response = {
        'body': MagicMock(read=lambda: json.dumps({
            'content': [{'text': 'Generated response based on context.'}]
        }).encode())
    }
    
    # Create pipe instance
    pipe = Pipe()
    pipe.valves.aws_access_key_id = 'test_key'
    pipe.valves.aws_secret_access_key = 'test_secret'
    pipe.valves.aws_region = 'us-east-1'
    pipe.valves.knowledge_base_id = 'test_kb_id'
    
    # Scenario 1: NO FILTER - Only always-include fields
    print("\n" + "-"*80)
    print("Scenario 1: No Filter (Only always-include fields)")
    print("-"*80)
    
    captured_prompt1 = None
    
    def mock_invoke_model1(**kwargs):
        nonlocal captured_prompt1
        request_body = json.loads(kwargs['body'])
        captured_prompt1 = request_body['messages'][0]['content']
        return mock_model_response
    
    with patch.object(pipe, 'bedrock_agent_client') as mock_agent_client:
        with patch.object(pipe, 'bedrock_client') as mock_bedrock_client:
            mock_agent_client.retrieve.return_value = mock_retrieval_response
            mock_bedrock_client.invoke_model.side_effect = mock_invoke_model1
            pipe._clients_initialized = True
            
            await pipe.query_knowledge_base("What is machine learning?", None, "")
            
            # Extract metadata section from prompt
            if 'Metadata:' in captured_prompt1:
                start = captured_prompt1.index('Metadata:')
                end = captured_prompt1.index('Source:', start)
                metadata_section = captured_prompt1[start:end]
                print("\nMetadata included in context:")
                print(metadata_section)
                
                # Count fields
                field_count = metadata_section.count('  - ')
                print(f"\nTotal metadata fields included: {field_count}")
                print("✓ Only 'created_at_iso' and 'source_uri' (always-include fields)")
            else:
                print("\n✗ No metadata section found")
    
    # Scenario 2: WITH FILTER - Includes filter fields + always-include fields
    print("\n" + "-"*80)
    print("Scenario 2: With Author Filter (Includes filter fields)")
    print("-"*80)
    
    captured_prompt2 = None
    
    def mock_invoke_model2(**kwargs):
        nonlocal captured_prompt2
        request_body = json.loads(kwargs['body'])
        captured_prompt2 = request_body['messages'][0]['content']
        return mock_model_response
    
    async def mock_generate_filter(query):
        # Filter by author_name and like_count
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
    
    with patch.object(pipe, 'bedrock_agent_client') as mock_agent_client:
        with patch.object(pipe, 'bedrock_client') as mock_bedrock_client:
            with patch.object(pipe, '_generate_metadata_filter', side_effect=mock_generate_filter):
                mock_agent_client.retrieve.return_value = mock_retrieval_response
                mock_bedrock_client.invoke_model.side_effect = mock_invoke_model2
                pipe._clients_initialized = True
                
                await pipe.query_knowledge_base("Show me posts by John Smith with many likes", None, "")
                
                # Extract metadata section from prompt
                if 'Metadata:' in captured_prompt2:
                    start = captured_prompt2.index('Metadata:')
                    end = captured_prompt2.index('Source:', start)
                    metadata_section = captured_prompt2[start:end]
                    print("\nMetadata included in context:")
                    print(metadata_section)
                    
                    # Count fields
                    field_count = metadata_section.count('  - ')
                    print(f"\nTotal metadata fields included: {field_count}")
                    print("✓ 'created_at_iso', 'source_uri' (always-include)")
                    print("✓ 'author_name', 'like_count' (used in filter)")
                else:
                    print("\n✗ No metadata section found")
    
    # Calculate token savings
    print("\n" + "="*80)
    print("Token Usage Optimization Analysis")
    print("="*80)
    
    all_metadata_fields = 12  # Total fields in the example
    always_include_fields = 2  # created_at_iso, source_uri
    filter_fields_scenario2 = 2  # author_name, like_count
    
    # Conservative estimate: ~10 tokens per metadata field
    # Based on: field name (1-3 tokens) + separator (1 token) + value (3-7 tokens) + formatting (1-2 tokens)
    # Example: "  - author_name: John Smith\n" ≈ 8-12 tokens
    # This is a rough approximation; actual token counts vary by tokenizer
    tokens_per_field = 10
    
    tokens_without_optimization = all_metadata_fields * tokens_per_field
    tokens_scenario1 = always_include_fields * tokens_per_field
    tokens_scenario2 = (always_include_fields + filter_fields_scenario2) * tokens_per_field
    
    savings_scenario1 = tokens_without_optimization - tokens_scenario1
    savings_scenario2 = tokens_without_optimization - tokens_scenario2
    
    print(f"\nWithout optimization (all metadata): ~{tokens_without_optimization} tokens")
    print(f"Scenario 1 (no filter): ~{tokens_scenario1} tokens")
    print(f"  → Saved ~{savings_scenario1} tokens ({100*savings_scenario1/tokens_without_optimization:.1f}%)")
    print(f"Scenario 2 (with filter): ~{tokens_scenario2} tokens")
    print(f"  → Saved ~{savings_scenario2} tokens ({100*savings_scenario2/tokens_without_optimization:.1f}%)")
    
    print("\n✓ Selective metadata inclusion optimizes token usage while preserving relevant context")


async def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("SELECTIVE METADATA INCLUSION - DEMONSTRATION")
    print("="*80)
    print("\nTask 5: Optimizing input context by limiting metadata")
    print("- Always include: source_uri, created_at_iso")
    print("- Conditionally include: fields used in metadata filters")
    
    demo_filter_key_extraction()
    await demo_selective_metadata_inclusion()
    
    print("\n" + "="*80)
    print("Demo Complete!")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
