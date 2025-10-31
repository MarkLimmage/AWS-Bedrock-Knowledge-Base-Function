#!/usr/bin/env python3
"""
Demo script for citation generation functionality

This script demonstrates how the citation generation feature works
by showing the citation attribution process and the final formatted output.
"""
import asyncio
import json
from unittest.mock import Mock, MagicMock

from aws_bedrock_kb_function import Pipe

def print_section(title):
    """Print a section header"""
    print("\n" + "="*80)
    print(title)
    print("="*80 + "\n")

async def demo_basic_citations():
    """Demonstrate basic citation generation"""
    print_section("Demo 1: Basic Citation Generation")
    
    pipe = Pipe()
    pipe.valves.enable_citations = True
    pipe._clients_initialized = True
    pipe.bedrock_client = Mock()
    
    # Simulate a generated answer about machine learning
    answer = """Machine learning is a subset of artificial intelligence that enables 
computers to learn from data. Deep learning is a specialized approach that uses 
neural networks with multiple layers. These techniques are widely used in image 
recognition and natural language processing."""
    
    # Simulate retrieved chunks from the knowledge base
    retrieved_results = [
        {
            'content': {'text': 'Machine learning is a subset of artificial intelligence that focuses on developing algorithms that can learn from and make predictions based on data.'},
            'metadata': {'source_uri': 's3://knowledge-base/ml-fundamentals.pdf'},
            'location': {'s3Location': {'uri': 's3://knowledge-base/ml-fundamentals.pdf'}}
        },
        {
            'content': {'text': 'Deep learning is a specialized subset of machine learning that uses artificial neural networks with multiple layers (hence "deep") to progressively extract higher-level features from raw input.'},
            'metadata': {'source_uri': 's3://knowledge-base/deep-learning-intro.pdf'},
            'location': {'s3Location': {'uri': 's3://knowledge-base/deep-learning-intro.pdf'}}
        },
        {
            'content': {'text': 'Deep learning techniques have revolutionized computer vision tasks such as image recognition, object detection, and image segmentation.'},
            'metadata': {'source_uri': 's3://knowledge-base/dl-applications.pdf'},
            'location': {'s3Location': {'uri': 's3://knowledge-base/dl-applications.pdf'}}
        }
    ]
    
    # Mock the citation attribution response
    mock_citation_response = {
        "citations": [
            {
                "answer_text": "Machine learning is a subset of artificial intelligence",
                "chunk_ids": [1]
            },
            {
                "answer_text": "Deep learning is a specialized approach that uses neural networks with multiple layers",
                "chunk_ids": [2]
            },
            {
                "answer_text": "widely used in image recognition",
                "chunk_ids": [3]
            }
        ]
    }
    
    mock_response_body = {
        'content': [{'text': json.dumps(mock_citation_response)}]
    }
    
    mock_response = MagicMock()
    mock_response.__getitem__.return_value.read.return_value = json.dumps(mock_response_body)
    pipe.bedrock_client.invoke_model.return_value = mock_response
    
    print("Original Answer:")
    print("-" * 80)
    print(answer)
    
    print("\n\nRetrieved Source Chunks:")
    print("-" * 80)
    for i, result in enumerate(retrieved_results, 1):
        content = result['content']['text']
        source = result['location']['s3Location']['uri']
        print(f"{i}. {content[:80]}...")
        print(f"   Source: {source}\n")
    
    # Generate citations
    result = await pipe._generate_citations(answer, retrieved_results)
    
    print("\n\nAnswer with Citations:")
    print("-" * 80)
    print(result)

async def demo_citation_disabled():
    """Demonstrate behavior when citations are disabled"""
    print_section("Demo 2: Citations Disabled")
    
    pipe = Pipe()
    pipe.valves.enable_citations = False
    
    answer = "This is a test answer without citations."
    retrieved_results = [
        {
            'content': {'text': 'Test content'},
            'metadata': {'source_uri': 's3://bucket/doc.pdf'}
        }
    ]
    
    result = await pipe._generate_citations(answer, retrieved_results)
    
    print("Original Answer:")
    print("-" * 80)
    print(answer)
    
    print("\n\nResult (citations disabled):")
    print("-" * 80)
    print(result)
    print("\n✓ Answer returned unchanged when citations are disabled")

async def demo_multiple_sources():
    """Demonstrate citation with multiple sources supporting one statement"""
    print_section("Demo 3: Multiple Sources for One Statement")
    
    pipe = Pipe()
    pipe.valves.enable_citations = True
    pipe._clients_initialized = True
    pipe.bedrock_client = Mock()
    
    answer = "Neural networks are inspired by biological neurons and are the foundation of deep learning."
    
    retrieved_results = [
        {
            'content': {'text': 'Artificial neural networks are computational models inspired by the structure and function of biological neural networks in animal brains.'},
            'metadata': {'source_uri': 's3://kb/neural-networks.pdf'},
            'location': {'s3Location': {'uri': 's3://kb/neural-networks.pdf'}}
        },
        {
            'content': {'text': 'Deep learning relies heavily on neural networks as its foundational architecture, using layers of connected nodes to process information.'},
            'metadata': {'source_uri': 's3://kb/dl-basics.pdf'},
            'location': {'s3Location': {'uri': 's3://kb/dl-basics.pdf'}}
        }
    ]
    
    # Mock citation response with multiple sources for one statement
    mock_citation_response = {
        "citations": [
            {
                "answer_text": "Neural networks are inspired by biological neurons and are the foundation of deep learning",
                "chunk_ids": [1, 2]
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
    
    print("Answer with Multiple Source Citations:")
    print("-" * 80)
    print(result)
    print("\n✓ Single statement can reference multiple sources [1,2]")

async def demo_long_chunk_truncation():
    """Demonstrate truncation of long chunk previews"""
    print_section("Demo 4: Long Chunk Preview Truncation")
    
    pipe = Pipe()
    pipe.valves.enable_citations = True
    pipe._clients_initialized = True
    pipe.bedrock_client = Mock()
    
    answer = "This demonstrates truncation."
    
    # Create a very long chunk text (realistic content to demonstrate truncation)
    long_text = "Natural language processing (NLP) is a subfield of linguistics, computer science, and artificial intelligence concerned with the interactions between computers and human language, in particular how to program computers to process and analyze large amounts of natural language data."
    
    retrieved_results = [
        {
            'content': {'text': long_text},
            'metadata': {'source_uri': 's3://kb/long-document.pdf'},
            'location': {'s3Location': {'uri': 's3://kb/long-document.pdf'}}
        }
    ]
    
    mock_citation_response = {
        "citations": [
            {
                "answer_text": "This demonstrates truncation",
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
    
    print(f"Original chunk length: {len(long_text)} characters")
    print("\nCitation with Truncated Preview:")
    print("-" * 80)
    print(result)
    print("\n✓ Long chunks are truncated to 50 characters + '...'")

async def main():
    """Run all demos"""
    print("\n" + "="*80)
    print("CITATION GENERATION DEMONSTRATION")
    print("="*80)
    
    await demo_basic_citations()
    await demo_citation_disabled()
    await demo_multiple_sources()
    await demo_long_chunk_truncation()
    
    print("\n" + "="*80)
    print("All demos completed successfully!")
    print("="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
