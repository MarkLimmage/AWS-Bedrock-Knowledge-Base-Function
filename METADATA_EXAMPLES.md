# Example Metadata Definitions for AWS Bedrock Knowledge Base

This file contains example metadata definitions that can be used with the metadata filtering feature.

## How to Use

1. Copy the JSON array below
2. In OpenWebUI, paste it into the `metadata_definitions` valve configuration
3. Enable metadata filtering by setting `enable_metadata_filtering` to `true`
4. Configure the `filter_model_id` (default is fine for most cases)

## Example: Social Media Posts Metadata

```json
[
    {
        "key": "created_at_iso",
        "type": "STRING",
        "description": "The timestamp from when the document was created in ISO format, e.g `2025-09-04T06:39:14Z`"
    },
    {
        "key": "created_at_unix",
        "type": "NUMBER",
        "description": "The timestamp from when the document was created in Unix epoch format, e.g. 1725430754"
    },
    {
        "key": "source_uri",
        "type": "STRING",
        "description": "The uri of the post on the platform. This can be used as the source of the post"
    },
    {
        "key": "author_handle",
        "type": "STRING",
        "description": "The handle of the author on the social media platform e.g. `australia.theguardian.com`"
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
        "description": "The role of the person of interest eg `author`, `repost`"
    },
    {
        "key": "author_did",
        "type": "STRING",
        "description": "A unique identifier of the author's profile on the social media platform. e.g. `did:plc:lia4ywzl2c2kt4dn3kzbywog`"
    },
    {
        "key": "role",
        "type": "STRING",
        "description": "Identifies if the post was created by the author or is related to them eg `related` or `author`"
    },
    {
        "key": "reply_count",
        "type": "NUMBER",
        "description": "The number of times the post has been replied to. This is a measure of the post's engagement."
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
```

## Example: Document Management Metadata

```json
[
    {
        "key": "document_type",
        "type": "STRING",
        "description": "The type of document, e.g., 'report', 'presentation', 'email', 'memo'"
    },
    {
        "key": "department",
        "type": "STRING",
        "description": "The department that owns this document, e.g., 'Finance', 'HR', 'Engineering'"
    },
    {
        "key": "created_date",
        "type": "STRING",
        "description": "The date when the document was created in ISO 8601 format, e.g., '2025-01-15T10:30:00Z'"
    },
    {
        "key": "author",
        "type": "STRING",
        "description": "The name of the document author"
    },
    {
        "key": "classification",
        "type": "STRING",
        "description": "Security classification level, e.g., 'public', 'internal', 'confidential', 'secret'"
    },
    {
        "key": "version",
        "type": "NUMBER",
        "description": "The version number of the document"
    },
    {
        "key": "page_count",
        "type": "NUMBER",
        "description": "The total number of pages in the document"
    }
]
```

## Example Queries

When metadata filtering is enabled, the system will automatically:
1. Extract date-time references from your query
2. Convert them to both ISO format and Unix epoch timestamps
3. Generate appropriate filters using Unix epoch fields for numeric comparisons

### Social Media Examples
- "Show me posts from John Smith in August 2025"
  - Extracts "August 2025" and converts to timestamps
  - Generates filters for `author_name` and `created_at_unix` using numeric range operators
- "Find highly engaged posts with more than 100 likes"
  - Generates filter for `like_count` with greaterThan operator
- "Show posts by the Guardian created before September 4, 2025"
  - Extracts "September 4, 2025" and converts to Unix timestamp
  - Generates filters for `author_handle` and `created_at_unix` with lessThan operator

### Document Management Examples
- "Find Finance department reports from Q1 2025"
  - Generates filters for `department` and `created_date`
- "Show confidential documents"
  - Generates filter for `classification`
- "List all presentations authored by Jane Doe"
  - Generates filters for `document_type` and `author`

## Notes

- The filter model will only generate filters for metadata fields that are clearly relevant to the user's query
- If no relevant metadata filtering is needed, the system will proceed with standard semantic search
- Filters are combined with semantic search using the HYBRID search type for optimal results
- The default filter model (`anthropic.claude-3-haiku-20240307-v1:0`) is optimized for low latency and cost
