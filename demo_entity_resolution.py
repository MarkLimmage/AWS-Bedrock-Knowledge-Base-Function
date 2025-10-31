#!/usr/bin/env python3
"""
Demo script for entity resolution (name parsing) functionality
"""
import json
from aws_bedrock_kb_function import parse_name_elements

def demo_name_parsing():
    """Demonstrate name parsing with various examples"""
    print("="*80)
    print("Demo: Entity Resolution - Name Parsing")
    print("="*80)
    print()
    print("This demo shows how entity resolution handles person names by:")
    print("1. Removing titles (Dr., Prof., Mr., Ms., etc.)")
    print("2. Splitting names into individual elements")
    print("3. Using these elements for flexible metadata filtering")
    print()
    
    examples = [
        "Dr. John Smith",
        "Prof. Mary Jane Watson",
        "Mr. Robert Johnson",
        "Jane Doe",
        "Sir Isaac Newton",
        "Captain James T. Kirk",
    ]
    
    for name in examples:
        elements = parse_name_elements(name)
        print(f"Input:    '{name}'")
        print(f"Output:   {elements}")
        print(f"Filter:   Each element will be matched with 'in' operator")
        print()

def demo_filter_structure():
    """Demonstrate the filter structure for entity resolution"""
    print("="*80)
    print("Demo: Entity Resolution - Filter Structure")
    print("="*80)
    print()
    print("For a query like: 'Show me posts from Dr. John Smith'")
    print()
    print("Traditional approach (exact match):")
    traditional_filter = {
        "in": {
            "key": "author_name",
            "value": ["Dr. John Smith"]
        }
    }
    print(json.dumps(traditional_filter, indent=2))
    print()
    print("Problem: This won't match variations like:")
    print("  - 'John Smith' (no title)")
    print("  - 'Smith, John' (reversed order)")
    print("  - 'Mr. John Smith' (different title)")
    print()
    print("-" * 80)
    print()
    print("Entity Resolution approach (element matching):")
    entity_resolution_filter = {
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
    print(json.dumps(entity_resolution_filter, indent=2))
    print()
    print("Benefit: This WILL match all variations:")
    print("  ✓ 'John Smith'")
    print("  ✓ 'Smith, John'")
    print("  ✓ 'Mr. John Smith'")
    print("  ✓ 'Dr. John Smith'")
    print("  ✓ 'John Q. Smith'")
    print("  ✓ 'Smith, John Q.'")
    print()

def demo_multiple_names():
    """Demonstrate filtering with multiple names"""
    print("="*80)
    print("Demo: Entity Resolution - Multiple Names")
    print("="*80)
    print()
    print("For a query like: 'Show me posts from John Smith or Jane Doe'")
    print()
    
    # Parse both names
    name1 = "John Smith"
    name2 = "Jane Doe"
    
    elements1 = parse_name_elements(name1)
    elements2 = parse_name_elements(name2)
    
    print(f"Name 1: '{name1}' -> {elements1}")
    print(f"Name 2: '{name2}' -> {elements2}")
    print()
    
    multiple_names_filter = {
        "orAll": [
            {
                "andAll": [
                    {"in": {"key": "author_name", "value": "John"}},
                    {"in": {"key": "author_name", "value": "Smith"}}
                ]
            },
            {
                "andAll": [
                    {"in": {"key": "author_name", "value": "Jane"}},
                    {"in": {"key": "author_name", "value": "Doe"}}
                ]
            }
        ]
    }
    
    print("Generated filter:")
    print(json.dumps(multiple_names_filter, indent=2))
    print()
    print("This filter will match documents where author_name contains:")
    print("  - Both 'John' AND 'Smith' (in any order)")
    print("  - OR Both 'Jane' AND 'Doe' (in any order)")
    print()

def demo_combined_filters():
    """Demonstrate combining name and date filters"""
    print("="*80)
    print("Demo: Entity Resolution - Combined with Date Filters")
    print("="*80)
    print()
    print("For a query like: 'Show me posts from Dr. John Smith in August 2025'")
    print()
    
    combined_filter = {
        "andAll": [
            {
                "greaterThanOrEquals": {
                    "key": "created_at_unix",
                    "value": 1754006400
                }
            },
            {
                "lessThanOrEquals": {
                    "key": "created_at_unix",
                    "value": 1756684799
                }
            },
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
    
    print("Generated combined filter:")
    print(json.dumps(combined_filter, indent=2))
    print()
    print("This filter ensures:")
    print("  1. Date is in August 2025 (using Unix timestamps)")
    print("  2. Author name contains 'John'")
    print("  3. Author name contains 'Smith'")
    print()

def demo_title_variations():
    """Demonstrate handling of various titles"""
    print("="*80)
    print("Demo: Entity Resolution - Title Handling")
    print("="*80)
    print()
    print("Entity resolution removes common titles automatically:")
    print()
    
    titles = [
        ("Dr. John Smith", ["John", "Smith"]),
        ("Doctor John Smith", ["John", "Smith"]),
        ("Prof. John Smith", ["John", "Smith"]),
        ("Professor John Smith", ["John", "Smith"]),
        ("Mr. John Smith", ["John", "Smith"]),
        ("Mrs. John Smith", ["John", "Smith"]),
        ("Ms. John Smith", ["John", "Smith"]),
        ("Sir John Smith", ["John", "Smith"]),
        ("Rev. John Smith", ["John", "Smith"]),
        ("Capt. John Smith", ["John", "Smith"]),
    ]
    
    for name, expected in titles:
        actual = parse_name_elements(name)
        match = "✓" if actual == expected else "✗"
        print(f"{match} '{name:30}' -> {actual}")
    print()

if __name__ == "__main__":
    demo_name_parsing()
    print()
    demo_filter_structure()
    print()
    demo_multiple_names()
    print()
    demo_combined_filters()
    print()
    demo_title_variations()
    
    print("="*80)
    print("Demo Complete!")
    print("="*80)
    print()
    print("Key Benefits of Entity Resolution:")
    print("  1. Handles name variations (title, order, middle names)")
    print("  2. More flexible than exact string matching")
    print("  3. Reduces false negatives in metadata filtering")
    print("  4. Works seamlessly with existing date/time filters")
    print()
