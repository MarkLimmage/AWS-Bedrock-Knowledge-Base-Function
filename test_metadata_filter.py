#!/usr/bin/env python3
"""
Test script for metadata filter generation functionality
"""
import asyncio
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from aws_bedrock_kb_function import Pipe

async def test_filter_generation():
    """Test the metadata filter generation"""
    print("Testing metadata filter generation...")
    
    pipe = Pipe()
    
    # Configure the pipe with test credentials (won't actually call AWS for this test)
    pipe.valves.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID', 'test_key')
    pipe.valves.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY', 'test_secret')
    pipe.valves.aws_region = os.getenv('AWS_REGION', 'us-east-1')
    pipe.valves.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID', 'test_kb_id')
    
    # Enable metadata filtering
    pipe.valves.enable_metadata_filtering = True
    pipe.valves.filter_model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    
    # Set metadata definitions from the problem statement
    metadata_defs = [
        {
            "key": "created_at",
            "type": "STRING",
            "description": "The timestamp from when the document was created, e.g `2025-09-04T06:39:14Z` "
        },
        {
            "key": "source_uri",
            "type": "STRING",
            "description": "The uri of the post on the platform. This can be used as the source of the post"
        },
        {
            "key": "author_handle",
            "type": "STRING",
            "description": "The handle of the author on the social media platform e.g. `australia.theguardian.com` "
        },
        {
            "key": "author_name",
            "type": "STRING",
            "description": "The name of the author."
        },
        {
            "key": "poi_name",
            "type": "STRING",
            "description": "The name of the person of interest."
        },
        {
            "key": "poi_role",
            "type": "STRING",
            "description": "The role of the person of inteerst eg `author`, `repost` "
        },
        {
            "key": "author_did",
            "type": "STRING",
            "description": "A unique identifier of the author's profile on the social media platform. e.g. `did:plc:lia4ywzl2c2kt4dn3kzbywog` "
        },
        {
            "key": "role",
            "type": "STRING",
            "description": "Identifies if the post was created by the author or is related to them eg `related` or `author` "
        },
        {
            "key": "reply_count",
            "type": "NUMBER",
            "description": "The number of times the post has been replied to.  This is a measure of the post's engagement."
        },
        {
            "key": "repost_count",
            "type": "NUMBER",
            "description": "The number of times the post has been reposted by other users. This is a measure of the post's reach."
        },
        {
            "key": "like_count",
            "type": "NUMBER",
            "description": "The number of times the post has been liked by other users. This is a measure of how much the post resonates with the community."
        }
    ]
    
    pipe.valves.metadata_definitions = json.dumps(metadata_defs)
    
    # Test queries
    test_queries = [
        "Show me posts from John Smith created in August 2025",
        "Find all posts by the author",
        "What are the most popular posts?",
        "Show recent updates"
    ]
    
    print("\n" + "="*80)
    print("Testing Filter Generation (requires AWS credentials)")
    print("="*80)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        print("-" * 80)
        
        # Only test filter generation if credentials are available
        if os.getenv('AWS_ACCESS_KEY_ID'):
            try:
                # Initialize clients
                pipe._initialize_clients()
                
                # Test filter generation
                metadata_filter = await pipe._generate_metadata_filter(query)
                
                if metadata_filter:
                    print("Generated filter:")
                    print(json.dumps(metadata_filter, indent=2))
                else:
                    print("No filter generated (either not applicable or disabled)")
            except Exception as e:
                print(f"Error testing filter generation: {str(e)}")
        else:
            print("Skipping - AWS credentials not configured")
    
    print("\n" + "="*80)
    print("Configuration Validation Tests")
    print("="*80)
    
    # Test 1: Verify valves are properly set
    print("\n1. Checking configuration valves:")
    print(f"   - enable_metadata_filtering: {pipe.valves.enable_metadata_filtering}")
    print(f"   - filter_model_id: {pipe.valves.filter_model_id}")
    print(f"   - metadata_definitions set: {len(pipe.valves.metadata_definitions) > 2}")
    
    # Test 2: Verify metadata definitions can be parsed
    print("\n2. Validating metadata definitions:")
    try:
        parsed_defs = json.loads(pipe.valves.metadata_definitions)
        print(f"   ✓ Successfully parsed {len(parsed_defs)} metadata field definitions")
        for field_def in parsed_defs:
            print(f"     - {field_def['key']} ({field_def['type']}): {field_def['description'][:50]}...")
    except json.JSONDecodeError as e:
        print(f"   ✗ Failed to parse metadata definitions: {str(e)}")
    
    # Test 3: Test with filtering disabled
    print("\n3. Testing with filtering disabled:")
    pipe.valves.enable_metadata_filtering = False
    filter_result = await pipe._generate_metadata_filter("test query")
    if filter_result is None:
        print("   ✓ Correctly returns None when filtering is disabled")
    else:
        print("   ✗ Should return None when filtering is disabled")
    
    print("\n" + "="*80)
    print("Tests complete!")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(test_filter_generation())
