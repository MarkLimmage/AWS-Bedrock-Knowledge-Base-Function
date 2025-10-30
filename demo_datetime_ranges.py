#!/usr/bin/env python3
"""
Demonstration script for Task 4 datetime range parsing functionality.

This script demonstrates how datetime references are now extracted as ranges
based on the level of detail (granularity) in the user's query.
"""
import json
from aws_bedrock_kb_function import parse_datetime_range


def demonstrate_range_parsing():
    """Demonstrate datetime range parsing with various examples"""
    print("\n" + "="*80)
    print("Task 4: DateTime Range Parsing Demonstration")
    print("="*80)
    print("\nProblem: Previously, datetime references were extracted as single points.")
    print("Solution: Now they are extracted as ranges based on granularity.\n")
    
    examples = [
        {
            "query": "Show me posts from August 2025",
            "granularity": "MONTH",
            "range": "from 2025-08-01T00:00:00Z to 2025-08-31T23:59:59Z",
            "description": "Full month - from first day 00:00:00 to last day 23:59:59"
        },
        {
            "query": "Find posts from September 4th, 2025",
            "granularity": "DAY",
            "range": "from 2025-09-04T00:00:00Z to 2025-09-04T23:59:59Z",
            "description": "Full day - from 00:00:00 to 23:59:59"
        },
        {
            "query": "What was posted on Sept 4, 2025 at 6:39 AM?",
            "granularity": "MINUTE",
            "range": "from 2025-09-04T06:39:00Z to 2025-09-04T06:39:59Z",
            "description": "One minute - from XX:39:00 to XX:39:59"
        },
        {
            "query": "Show me everything from 2025",
            "granularity": "YEAR",
            "range": "from 2025-01-01T00:00:00Z to 2025-12-31T23:59:59Z",
            "description": "Full year - from Jan 1 00:00:00 to Dec 31 23:59:59"
        },
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{'-'*80}")
        print(f"Example {i}: {example['granularity']} granularity")
        print(f"{'-'*80}")
        print(f"User Query: \"{example['query']}\"")
        print(f"\nExtracted Range:")
        print(f"  {example['range']}")
        print(f"\nExplanation: {example['description']}")
        
        # Parse the range to show Unix timestamps
        start_iso, start_unix, end_iso, end_unix = parse_datetime_range(example['range'])
        
        if start_iso and end_iso:
            duration_seconds = end_unix - start_unix
            print(f"\nParsed Values:")
            print(f"  Start: {start_iso} (Unix: {start_unix})")
            print(f"  End:   {end_iso} (Unix: {end_unix})")
            print(f"  Duration: {duration_seconds:,} seconds")
            
            # Show how this would be used in a filter
            print(f"\nGenerated Filter Condition:")
            print(f"  {{")
            print(f"    \"andAll\": [")
            print(f"      {{\"greaterThanOrEquals\": {{\"key\": \"created_at_unix\", \"value\": {start_unix}}}}},")
            print(f"      {{\"lessThanOrEquals\": {{\"key\": \"created_at_unix\", \"value\": {end_unix}}}}}")
            print(f"    ]")
            print(f"  }}")


def compare_old_vs_new():
    """Show the difference between old (single point) and new (range) approach"""
    print("\n" + "="*80)
    print("Before vs After Comparison")
    print("="*80)
    
    example = "Show me posts from March 2025"
    
    print(f"\nUser Query: \"{example}\"")
    
    print(f"\n{'BEFORE (Task 3)':-^80}")
    print("Single datetime point extracted:")
    print(json.dumps({
        "original": "March 2025",
        "iso": "2025-03-01T00:00:00Z",
        "unix": 1740787200
    }, indent=2))
    print("\nProblem: Filter would use a single greaterThan or equals condition,")
    print("not capturing the full month range implied by 'March 2025'")
    
    print(f"\n{'AFTER (Task 4)':-^80}")
    print("Datetime range extracted:")
    range_str = "from 2025-03-01T00:00:00Z to 2025-03-31T23:59:59Z"
    start_iso, start_unix, end_iso, end_unix = parse_datetime_range(range_str)
    print(json.dumps({
        "original": "March 2025",
        "start_iso": start_iso,
        "start_unix": start_unix,
        "end_iso": end_iso,
        "end_unix": end_unix
    }, indent=2))
    print("\nSolution: Filter uses BOTH greaterThanOrEquals (start) and lessThanOrEquals (end),")
    print("properly capturing the entire month range from March 1st to March 31st.")


def show_filter_example():
    """Show a complete filter generation example"""
    print("\n" + "="*80)
    print("Complete Filter Generation Example")
    print("="*80)
    
    print("\nScenario: User asks 'Show me posts from John Smith in August 2025'")
    
    print("\n1. Datetime extraction (new behavior):")
    range_str = "from 2025-08-01T00:00:00Z to 2025-08-31T23:59:59Z"
    start_iso, start_unix, end_iso, end_unix = parse_datetime_range(range_str)
    print(f"   'August 2025' -> Range:")
    print(f"     Start: {start_iso} (Unix: {start_unix})")
    print(f"     End:   {end_iso} (Unix: {end_unix})")
    
    print("\n2. Enhanced query sent to filter model:")
    print('   "Show me posts from John Smith in August 2025"')
    print(f'   "(from {start_iso} to {end_iso})"')
    
    print("\n3. Context provided to filter model:")
    print("   Extracted date-time ranges:")
    print(f"   - 'August 2025' -> from {start_iso} (Unix: {start_unix})")
    print(f"                      to {end_iso} (Unix: {end_unix})")
    
    print("\n4. Generated metadata filter:")
    filter_obj = {
        "andAll": [
            {
                "greaterThanOrEquals": {
                    "key": "created_at_unix",
                    "value": start_unix
                }
            },
            {
                "lessThanOrEquals": {
                    "key": "created_at_unix",
                    "value": end_unix
                }
            },
            {
                "in": {
                    "key": "author_name",
                    "value": ["John Smith"]
                }
            }
        ]
    }
    print(json.dumps(filter_obj, indent=2))
    
    print("\n5. Result:")
    print("   ✓ Documents are filtered to ONLY include those created during August 2025")
    print("   ✓ Documents are further filtered to ONLY include those by John Smith")
    print("   ✓ The range ensures all posts from August 1st to August 31st are included")


def main():
    """Run all demonstrations"""
    print("\n" + "="*80)
    print("TASK 4 IMPLEMENTATION DEMONSTRATION")
    print("Datetime Range Parsing for Metadata Filtering")
    print("="*80)
    
    demonstrate_range_parsing()
    compare_old_vs_new()
    show_filter_example()
    
    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    print("\nKey improvements in Task 4:")
    print("  1. ✓ Datetime references are extracted as RANGES, not single points")
    print("  2. ✓ Ranges are based on granularity (year, month, day, hour, minute)")
    print("  3. ✓ Filter generation uses greaterThanOrEquals + lessThanOrEquals")
    print("  4. ✓ Properly captures the time period implied by the user's query")
    print("\nBenefits:")
    print("  - More accurate filtering based on user intent")
    print("  - Handles implicit ranges (e.g., 'August 2025' means the whole month)")
    print("  - Works with various granularities (year, month, day, hour, minute)")
    print("  - Generates proper range conditions in metadata filters")
    print("\n" + "="*80 + "\n")


if __name__ == "__main__":
    main()
