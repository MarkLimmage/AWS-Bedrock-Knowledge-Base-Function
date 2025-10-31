#!/usr/bin/env python3
"""
Manual verification script for citation generation

This script demonstrates the citation feature in action and can be run
with real AWS credentials to test against an actual knowledge base.

Usage:
    python manual_citation_test.py "your query here"
    
Example:
    python manual_citation_test.py "What is machine learning?"
"""
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from aws_bedrock_kb_function import Pipe

def print_section(title, char="="):
    """Print a formatted section header"""
    print("\n" + char*80)
    print(title)
    print(char*80 + "\n")

async def test_citation_generation(query):
    """Test citation generation with a real or mocked knowledge base query"""
    
    print_section("CITATION GENERATION MANUAL VERIFICATION", "=")
    print(f"Query: {query}\n")
    
    # Initialize pipe
    pipe = Pipe()
    
    # Check if AWS credentials are available
    has_credentials = (
        os.getenv('AWS_ACCESS_KEY_ID') and 
        os.getenv('AWS_SECRET_ACCESS_KEY') and 
        os.getenv('KNOWLEDGE_BASE_ID')
    )
    
    if has_credentials:
        print("✓ AWS credentials found - will test with real knowledge base")
        
        # Configure from environment
        pipe.valves.aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
        pipe.valves.aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        pipe.valves.aws_region = os.getenv('AWS_REGION', 'eu-central-1')
        pipe.valves.knowledge_base_id = os.getenv('KNOWLEDGE_BASE_ID')
        pipe.valves.model_id = os.getenv('MODEL_ID', "anthropic.claude-3-5-sonnet-20240620-v1:0")
        pipe.valves.filter_model_id = os.getenv('FILTER_MODEL_ID', "anthropic.claude-3-haiku-20240307-v1:0")
        pipe.valves.number_of_results = int(os.getenv('NUMBER_OF_RESULTS', 5))
        
        # Enable citations
        pipe.valves.enable_citations = True
        
        print(f"Configuration:")
        print(f"  - Region: {pipe.valves.aws_region}")
        print(f"  - Knowledge Base ID: {pipe.valves.knowledge_base_id}")
        print(f"  - Model: {pipe.valves.model_id}")
        print(f"  - Citation Model: {pipe.valves.filter_model_id}")
        print(f"  - Number of Results: {pipe.valves.number_of_results}")
        print(f"  - Citations Enabled: {pipe.valves.enable_citations}")
        
        # Create request body
        body = {
            "messages": [
                {"role": "user", "content": query}
            ]
        }
        
        print_section("Querying Knowledge Base...", "-")
        
        try:
            # Call the pipe
            response = await pipe.pipe(body)
            
            print_section("RESULT", "=")
            
            if isinstance(response, dict) and "error" in response:
                print(f"❌ Error: {response['error']}")
            else:
                print(response)
                
                # Analyze the response
                print_section("Citation Analysis", "-")
                
                has_citations = "**Citations:**" in response
                has_inline_refs = "[1]" in response or "[2]" in response
                
                if has_citations:
                    print("✓ Citation list found in response")
                    # Count citations
                    citation_count = response.count("\n1. ") + response.count("\n2. ") + response.count("\n3. ") + response.count("\n4. ") + response.count("\n5. ")
                    print(f"✓ Found approximately {citation_count} citations")
                else:
                    print("⚠ No citation list found (this is unexpected)")
                
                if has_inline_refs:
                    print("✓ Inline citation markers found in answer")
                else:
                    print("⚠ No inline citation markers found (may indicate no attributable claims)")
                
                # Check citation format
                if "---" in response and "**Citations:**" in response:
                    print("✓ Citation section properly formatted")
                    
                    # Extract and display citations
                    parts = response.split("**Citations:**")
                    if len(parts) > 1:
                        citations = parts[1].strip()
                        print("\nExtracted Citations:")
                        print(citations[:500] + "..." if len(citations) > 500 else citations)
                
        except Exception as e:
            print(f"❌ Error during query: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("⚠ AWS credentials not found - running with mock data")
        print("\nTo test with real AWS knowledge base:")
        print("1. Create a .env file with:")
        print("   AWS_ACCESS_KEY_ID=your_key")
        print("   AWS_SECRET_ACCESS_KEY=your_secret")
        print("   AWS_REGION=your_region")
        print("   KNOWLEDGE_BASE_ID=your_kb_id")
        print("2. Run this script again")
        
        print_section("Mock Citation Example", "-")
        
        # Show what the output would look like
        mock_output = """Machine learning is a subset of artificial intelligence[1] that enables 
computers to learn from data without being explicitly programmed. Deep learning 
uses neural networks[2] to process complex patterns in data.

---
**Citations:**
1. "Machine learning is a subset of artificial intelli..." - [s3://knowledge-base/ml-fundamentals.pdf](s3://knowledge-base/ml-fundamentals.pdf)
2. "Deep learning is a specialized approach that uses ..." - [s3://knowledge-base/deep-learning-guide.pdf](s3://knowledge-base/deep-learning-guide.pdf)"""
        
        print(mock_output)
        print("\n✓ This is an example of how citations appear in the output")

def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python manual_citation_test.py \"your query here\"")
        print("\nExample queries:")
        print("  python manual_citation_test.py \"What is machine learning?\"")
        print("  python manual_citation_test.py \"Explain deep learning\"")
        print("  python manual_citation_test.py \"How do neural networks work?\"")
        sys.exit(1)
    
    query = sys.argv[1]
    asyncio.run(test_citation_generation(query))

if __name__ == "__main__":
    main()
