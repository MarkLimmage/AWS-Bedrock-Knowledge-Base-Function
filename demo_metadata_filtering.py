#!/usr/bin/env python3
"""
Demonstration script for metadata filter generation feature.

This script shows how to configure and use the metadata filtering functionality
in the AWS Bedrock Knowledge Base function.
"""
import json
from aws_bedrock_kb_function import Pipe

def demonstrate_configuration():
    """Demonstrate how to configure metadata filtering"""
    print("="*80)
    print("AWS Bedrock KB Metadata Filter - Configuration Demo")
    print("="*80)
    
    # Initialize the pipe
    pipe = Pipe()
    
    print("\n1. Default Configuration:")
    print(f"   - enable_metadata_filtering: {pipe.valves.enable_metadata_filtering}")
    print(f"   - filter_model_id: {pipe.valves.filter_model_id}")
    print(f"   - metadata_definitions: {pipe.valves.metadata_definitions}")
    
    print("\n2. Enabling Metadata Filtering:")
    pipe.valves.enable_metadata_filtering = True
    print(f"   ✓ Enabled: {pipe.valves.enable_metadata_filtering}")
    
    print("\n3. Setting Metadata Definitions:")
    # Define metadata fields (example for social media posts)
    metadata_defs = [
        {
            "key": "created_at",
            "type": "STRING",
            "description": "The timestamp from when the document was created"
        },
        {
            "key": "author_name",
            "type": "STRING",
            "description": "The name of the author"
        },
        {
            "key": "like_count",
            "type": "NUMBER",
            "description": "Number of likes the post received"
        }
    ]
    
    pipe.valves.metadata_definitions = json.dumps(metadata_defs, indent=2)
    print(f"   ✓ Configured {len(metadata_defs)} metadata fields")
    
    print("\n4. Metadata Field Details:")
    for field in metadata_defs:
        print(f"   - {field['key']} ({field['type']})")
        print(f"     Description: {field['description']}")
    
    print("\n5. Example Filter Structure:")
    example_filter = {
        "andAll": [
            {
                "lessThan": {
                    "key": "created_at",
                    "value": "2025-09-04T23:59:59Z"
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
    print("   Expected filter format:")
    print(json.dumps(example_filter, indent=6))
    
    print("\n6. Integration with Knowledge Base Query:")
    print("   When a user asks: 'Show me posts from John Smith in August 2025'")
    print("   The system will:")
    print("   a. Extract the query intent")
    print("   b. Generate appropriate metadata filters")
    print("   c. Apply HYBRID search (semantic + metadata)")
    print("   d. Return filtered results")
    
    print("\n" + "="*80)
    print("Configuration complete!")
    print("="*80)
    
    return pipe

def show_query_examples():
    """Show example queries that benefit from metadata filtering"""
    print("\n" + "="*80)
    print("Example Queries That Use Metadata Filtering")
    print("="*80)
    
    examples = [
        {
            "query": "Show me posts from John Smith created in August 2025",
            "expected_filters": ["author_name", "created_at"],
            "description": "Filters by specific author and date range"
        },
        {
            "query": "Find highly engaged posts with more than 100 likes",
            "expected_filters": ["like_count"],
            "description": "Filters by numeric engagement metric"
        },
        {
            "query": "What are the latest updates?",
            "expected_filters": ["created_at"],
            "description": "Filters by recency"
        },
        {
            "query": "Show all posts by the author",
            "expected_filters": ["author_name"],
            "description": "Filters by author name"
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\nExample {i}:")
        print(f"  Query: '{example['query']}'")
        print(f"  Expected Filters: {', '.join(example['expected_filters'])}")
        print(f"  Description: {example['description']}")
    
    print("\n" + "="*80)

def show_benefits():
    """Show the benefits of using metadata filtering"""
    print("\n" + "="*80)
    print("Benefits of Metadata Filtering")
    print("="*80)
    
    benefits = [
        "🎯 More Precise Results: Combine semantic search with metadata constraints",
        "⚡ Improved Performance: Filter at the database level before semantic ranking",
        "📊 Better Context: Leverage structured metadata alongside document content",
        "🔍 Enhanced Control: Allow users to specify exact criteria (dates, authors, etc.)",
        "🤝 Hybrid Approach: Best of both semantic understanding and structured filtering"
    ]
    
    for benefit in benefits:
        print(f"\n  {benefit}")
    
    print("\n" + "="*80)

def main():
    """Run the demonstration"""
    print("\n" + "="*80)
    print("AWS Bedrock Knowledge Base - Metadata Filtering Demo")
    print("="*80)
    
    # Show configuration
    pipe = demonstrate_configuration()
    
    # Show example queries
    show_query_examples()
    
    # Show benefits
    show_benefits()
    
    print("\n" + "="*80)
    print("Demo Complete!")
    print("="*80)
    print("\nTo use this feature:")
    print("1. Configure your AWS credentials")
    print("2. Enable metadata filtering in the function valves")
    print("3. Define your metadata schema")
    print("4. Start querying with natural language!")
    print("\nFor more examples, see METADATA_EXAMPLES.md")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
