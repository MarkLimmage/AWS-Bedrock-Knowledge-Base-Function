# AWS Bedrock Knowledge Base Function for OpenWebUI

This custom function integrates AWS Bedrock Knowledge Base with OpenWebUI, allowing you to query your knowledge bases and receive AI-generated responses based on your documents.

## Overview

The AWS Bedrock Knowledge Base Function connects OpenWebUI to your AWS Bedrock Knowledge Bases, enabling you to:

- Query your knowledge bases using natural language
- Retrieve relevant information from your documents
- Generate AI responses based on the retrieved information
- Maintain conversation context for more coherent interactions
- Optionally assume an IAM role for authentication
- Support custom VPC endpoints for private access

## Installation

1. Copy the `aws_bedrock_kb_function.py` file to your OpenWebUI functions directory.
2. Restart OpenWebUI or reload the functions.
3. Configure the function with your AWS credentials and Knowledge Base ID.
4. (Optional) Copy `aws_bedrock_pipeline.py` to your OpenWebUI pipelines directory
   if you want to select between multiple Knowledge Bases. Set the `AWS_BEDROCK_KB_IDS`
   and `AWS_BEDROCK_KB_NAMES` environment variables with semicolon-separated values
   to control which pipelines are available.

## Testing

To test the function locally:

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Create a `.env` file with your AWS credentials and configuration:
   ```
   # AWS Credentials
   AWS_ACCESS_KEY_ID=your_access_key_id
   AWS_SECRET_ACCESS_KEY=your_secret_access_key
   AWS_SESSION_TOKEN=placeholder
   AWS_REGION=eu-central-1
   KNOWLEDGE_BASE_ID=your_knowledge_base_id  # required
   DATA_SOURCE_ID=your_data_source_id

   # Optional Model Configuration
  MODEL_ID=anthropic.claude-3-5-sonnet-20240620-v1:0
  NUMBER_OF_RESULTS=10
  # Optional VPC Endpoint configuration
  BEDROCK_RUNTIME_ENDPOINT_URL=https://your-runtime-endpoint # VPC Endpoint for: bedrock-runtime (Custom VPCE - leave empty if you don't work with a vpc)
  BEDROCK_AGENT_RUNTIME_ENDPOINT_URL=https://your-agent-endpoint   # VPC Endpoint for: bedrock-agent-runtime (Custom VPCE - leave empty if you don't work with a vpc)
  # Optional Assume Role configuration
  AWS_ASSUME_ROLE_ARN=placeholder
  AWS_ASSUME_ROLE_SESSION_NAME=bedrock-kb-session
  ```
   Leave `AWS_SESSION_TOKEN` and `AWS_ASSUME_ROLE_ARN` set to `placeholder` if you are not using temporary credentials or role assumption.

3. Run the test script:
   ```
   python test_kb_function.py "your query here"
   ```

   Additional test options:
   - `--list-kbs`: List all knowledge bases in your AWS account
   - `--check-kb`: Check details of the configured knowledge base
   - `--check-ds`: Check details of the configured data source
   - `--debug`: Enable detailed debugging output

## Configuration

The function provides the following configuration options (valves):

| Parameter | Description | Default |
|-----------|-------------|---------|
| `aws_access_key_id` | Your AWS Access Key ID | "" |
| `aws_secret_access_key` | Your AWS Secret Access Key | "" |
| `aws_session_token` | AWS Session Token (ignored if set to `placeholder`) | "placeholder" |
| `aws_region` | AWS Region where your Knowledge Base is located | "eu-central-1" |
| `knowledge_base_id` | ID of your AWS Bedrock Knowledge Base (required) | "" |
| `model_id` | AWS Bedrock model ID to use for generating responses | "anthropic.claude-3-5-sonnet-20240620-v1:0" |
| `max_tokens` | Maximum number of tokens in the response | 4096 |
| `temperature` | Temperature for model generation (0.0-1.0) | 0.7 |
| `top_p` | Top-p sampling parameter (0.0-1.0) | 0.9 |
| `number_of_results` | Number of knowledge base results to retrieve | 5 |
| `use_conversation_history` | Whether to include conversation history for context | true |
| `max_history_messages` | Maximum number of previous messages to include in history | 10 |
| `emit_interval` | Interval in seconds between status emissions | 2.0 |
| `enable_status_indicator` | Enable or disable status indicator emissions | true |
| `assume_role_arn` | IAM role ARN to assume (ignored if set to `placeholder`) | "placeholder" |
| `assume_role_session_name` | Session name to use when assuming the IAM role | "bedrock-kb-session" |
| `bedrock_runtime_endpoint_url` | VPC Endpoint for: bedrock-runtime (Custom VPCE - leave empty if you don't work with a VPC) | "" |
| `bedrock_agent_runtime_endpoint_url` | VPC Endpoint for: bedrock-agent-runtime (Custom VPCE - leave empty if you don't work with a VPC) | "" |
| `enable_metadata_filtering` | Enable metadata filter generation for knowledge base queries | false |
| `filter_model_id` | Lightweight model ID to use for metadata filter generation | "anthropic.claude-3-haiku-20240307-v1:0" |
| `metadata_definitions` | JSON array of metadata field definitions for filter generation | "[]" |

### Using VPC Endpoints

If your environment requires private connectivity, create VPC interface endpoints for
`bedrock-runtime` and `bedrock-agent-runtime` and specify their URLs:

```bash
BEDROCK_RUNTIME_ENDPOINT_URL=https://vpce-xxxxxxxxxxxx.your-region.vpce.amazonaws.com
BEDROCK_AGENT_RUNTIME_ENDPOINT_URL=https://vpce-yyyyyyyyyyyy.your-region.vpce.amazonaws.com
```

All Bedrock API calls will be routed through these endpoints.

### Assuming an IAM Role

To use a cross-account role, provide the role ARN and an optional session name:

```bash
AWS_ASSUME_ROLE_ARN=arn:aws:iam::111122223333:role/BedrockKbRole
AWS_ASSUME_ROLE_SESSION_NAME=kb-session
```

The function will call STS to obtain temporary credentials before creating the clients.

### Metadata Filtering and Generation Awareness

The function supports automatic metadata filter generation to refine knowledge base queries based on metadata. When enabled, the function uses a lightweight model to analyze the user's query and generate appropriate filters based on your metadata field definitions.

**Important:** The metadata from retrieved documents is **automatically included** in the generation prompt. This ensures the LLM is aware of important context like:
- Document author and creation dates
- Document categories and tags
- Custom metadata fields from your knowledge base

This metadata awareness allows the LLM to:
- Verify document relevance to specific query requirements (e.g., "documents from John Smith")
- Provide more accurate responses based on temporal or authorship context
- Better understand the relationship between retrieved chunks and the original question

To enable metadata filtering:

1. Set `enable_metadata_filtering` to `true`
2. Configure `filter_model_id` (default: `anthropic.claude-3-haiku-20240307-v1:0`)
3. Define your metadata fields in `metadata_definitions` as a JSON array

Example metadata definitions:
```json
[
    {
        "key": "created_at",
        "type": "STRING",
        "description": "The timestamp from when the document was created, e.g `2025-09-04T06:39:14Z`"
    },
    {
        "key": "author_name",
        "type": "STRING",
        "description": "The name of the author."
    },
    {
        "key": "like_count",
        "type": "NUMBER",
        "description": "The number of times the post has been liked by other users."
    }
]
```

The filter generation model will automatically create filters like:
```json
{
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
```

These filters are then applied to the knowledge base retrieval using the `HYBRID` search type, combining both semantic search and metadata filtering for more precise results. The metadata from filtered results is then explicitly presented to the LLM in the generation prompt for better context awareness.


## Required AWS Permissions

To use this function, your AWS credentials must have the following permissions:

- `bedrock:InvokeModel` - For generating responses with Bedrock models
- `bedrock-agent:Retrieve` - For querying Knowledge Bases

## Usage

1. In OpenWebUI, select "AWS Bedrock Knowledge Base" from the model dropdown.
2. Enter your query in the chat input.
3. The function will:
   - Retrieve relevant information from your Knowledge Base
   - Generate a response based on the retrieved information
   - Display the response in the chat

## Example Prompts

- "What information do we have about our company's vacation policy?"
- "Summarize the quarterly financial report from Q1 2024."
- "What are the key points from the latest product documentation?"

## Troubleshooting

### Common Errors

- **AWS credentials are not configured**: Ensure you've set your AWS Access Key ID and Secret Access Key in the function settings.
- **Knowledge Base ID is not configured**: Make sure you've entered your Knowledge Base ID in the function settings.
- **Access denied to AWS Bedrock**: Verify that your AWS credentials have the necessary permissions to access Bedrock and Knowledge Bases.
- **Knowledge Base ID not found**: Double-check that the Knowledge Base ID is correct and that the Knowledge Base exists in the specified AWS region.

### Debugging Tips

1. Check the OpenWebUI logs for detailed error messages.
2. Verify your AWS credentials and permissions.
3. Ensure your Knowledge Base is properly set up and contains indexed documents.
4. Try a simple query to test if the basic functionality is working.

## License

This function is provided under the MIT License.
