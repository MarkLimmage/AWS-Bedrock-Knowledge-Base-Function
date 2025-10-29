"""
title: AWS Bedrock Knowledge Base Function
author: Aaron Bolton
author_url: https://github.com/d3v0ps-cloud/AWS-Bedrock-Knowledge-Base-Function
version: 0.1.3
description: Integration with AWS Bedrock Knowledge Base for OpenWebUI only support for Claude 3 models.
This module defines a Pipe class that utilizes AWS Bedrock Knowledge Base for retrieving information
from your documents and providing AI-generated responses.
"""
from typing import Optional, Callable, Awaitable, List, Dict, Any, Tuple, Union
from pydantic import BaseModel, Field, validator
import os
import time
import json
import boto3
from botocore.exceptions import ClientError
from enum import Enum
from datetime import datetime, timezone
import re

# Constants for model families
class ModelFamily(str, Enum):
    CLAUDE3 = "anthropic.claude-3"

def extract_event_info(event_emitter) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract chat_id and message_id from event emitter closure.
    
    Args:
        event_emitter: The event emitter function with closure containing request info
        
    Returns:
        Tuple containing chat_id and message_id, both can be None if not found
    """
    if not event_emitter or not event_emitter.__closure__:
        return None, None
    for cell in event_emitter.__closure__:
        if isinstance(request_info := cell.cell_contents, dict):
            chat_id = request_info.get("chat_id")
            message_id = request_info.get("message_id")
            return chat_id, message_id
    return None, None

def parse_datetime_to_formats(datetime_str: str) -> Tuple[Optional[str], Optional[int]]:
    """
    Parse a datetime string to both ISO format and Unix epoch timestamp.
    
    Args:
        datetime_str: A datetime string in various formats
        
    Returns:
        Tuple of (iso_format_string, unix_timestamp) or (None, None) if parsing fails
        
    Note:
        If the input datetime does not have timezone information, UTC is assumed
        for consistent timestamp conversion.
    """
    try:
        # Try common datetime formats
        formats = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%m/%d/%Y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%Y-%m-%dT%H:%M:%S%z",
        ]
        
        dt = None
        for fmt in formats:
            try:
                dt = datetime.strptime(datetime_str, fmt)
                break
            except ValueError:
                continue
        
        if dt is None:
            return None, None
            
        # Ensure UTC timezone for consistent timestamp conversion
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
            
        # Convert to ISO format and Unix timestamp
        iso_format = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        unix_timestamp = int(dt.timestamp())
        
        return iso_format, unix_timestamp
        
    except Exception as e:
        print(f"DEBUG - Failed to parse datetime '{datetime_str}': {str(e)}")
        return None, None

def _remove_markdown_code_blocks(text: str) -> str:
    """
    Remove markdown code blocks from text if present.
    
    Args:
        text: Text that may contain markdown code blocks
        
    Returns:
        Text with markdown code blocks removed
    """
    text = text.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
    return text

class Pipe:
    class Valves(BaseModel):
        aws_access_key_id: str = Field(
            default="", description="AWS Access Key ID"
        )
        aws_secret_access_key: str = Field(
            default="", description="AWS Secret Access Key"
        )
        aws_session_token: str = Field(
            default="placeholder", description="AWS Session Token (optional, ignored if set to 'placeholder')"
        )
        aws_region: str = Field(
            default="eu-central-1", description="AWS Region"
        )
        knowledge_base_id: str = Field(
            default="", description="AWS Bedrock Knowledge Base ID"
        )
        model_id: str = Field(
            default="anthropic.claude-3-5-sonnet-20240620-v1:0",
            description="Model ID to use for retrieval"
        )
        max_tokens: int = Field(
            default=4096, description="Maximum number of tokens in the response"
        )
        temperature: float = Field(
            default=0.7, description="Temperature for model generation"
        )
        top_p: float = Field(
            default=0.9, description="Top-p sampling parameter"
        )
        number_of_results: int = Field(
            default=5, description="Number of knowledge base results to retrieve"
        )
        use_conversation_history: bool = Field(
            default=True, description="Whether to include conversation history for context"
        )
        max_history_messages: int = Field(
            default=10, description="Maximum number of previous messages to include in history"
        )
        emit_interval: float = Field(
            default=2.0, description="Interval in seconds between status emissions"
        )
        enable_status_indicator: bool = Field(
            default=True, description="Enable or disable status indicator emissions"
        )
        assume_role_arn: str = Field(
            default="placeholder",
            description="Optional IAM role ARN to assume (ignored if set to 'placeholder')",
        )
        assume_role_session_name: str = Field(
            default="bedrock-kb-session",
            description="Session name when assuming the IAM role",
        )
        bedrock_runtime_endpoint_url: str = Field(
            default="",
            description="Custom endpoint URL for bedrock-runtime (VPC Endpoint support)",
        )
        bedrock_agent_runtime_endpoint_url: str = Field(
            default="",
            description="Custom endpoint URL for bedrock-agent-runtime (VPC Endpoint support)",
        )
        enable_metadata_filtering: bool = Field(
            default=False, description="Enable metadata filter generation for knowledge base queries"
        )
        filter_model_id: str = Field(
            default="anthropic.claude-3-haiku-20240307-v1:0",
            description="Lightweight model ID to use for metadata filter generation"
        )
        metadata_definitions: str = Field(
            default="[]",
            description="JSON array of metadata field definitions for filter generation"
        )
        
        @validator('temperature')
        def validate_temperature(cls, v):
            if v < 0 or v > 1:
                raise ValueError('Temperature must be between 0 and 1')
            return v
            
        @validator('top_p')
        def validate_top_p(cls, v):
            if v < 0 or v > 1:
                raise ValueError('Top-p must be between 0 and 1')
            return v
            
        @validator('number_of_results')
        def validate_number_of_results(cls, v):
            if v < 1 or v > 100:
                raise ValueError('Number of results must be between 1 and 100')
            return v

    def __init__(self):
        """Initialize the AWS Bedrock Knowledge Base pipe"""
        self.type = "pipe"
        self.id = "aws_bedrock_kb"
        self.name = "AWS Bedrock Knowledge Base"
        self.valves = self.Valves()
        self.last_emit_time = 0
        self.bedrock_client = None
        self.bedrock_agent_client = None
        self._clients_initialized = False

    def _initialize_clients(self) -> None:
        """
        Initialize AWS Bedrock clients with credentials.
        
        This method creates boto3 clients for Bedrock Runtime and Bedrock Agent Runtime
        using the configured AWS credentials. It only initializes the clients if they
        haven't been initialized already.
        
        Raises:
            Exception: If client initialization fails
        """
        if not self._clients_initialized:
            session_kwargs = {
                'aws_access_key_id': self.valves.aws_access_key_id,
                'aws_secret_access_key': self.valves.aws_secret_access_key,
                'region_name': self.valves.aws_region
            }
            
            # Add session token if provided and not placeholder
            if self.valves.aws_session_token and self.valves.aws_session_token != "placeholder":
                session_kwargs['aws_session_token'] = self.valves.aws_session_token
                
            session = boto3.Session(**session_kwargs)

            # If an assume role ARN is provided and not placeholder, assume the role to obtain temporary credentials
            if self.valves.assume_role_arn and self.valves.assume_role_arn != "placeholder":
                try:
                    sts_client = session.client('sts')
                    assumed = sts_client.assume_role(
                        RoleArn=self.valves.assume_role_arn,
                        RoleSessionName=self.valves.assume_role_session_name,
                    )
                    credentials = assumed['Credentials']
                    session = boto3.Session(
                        aws_access_key_id=credentials['AccessKeyId'],
                        aws_secret_access_key=credentials['SecretAccessKey'],
                        aws_session_token=credentials['SessionToken'],
                        region_name=self.valves.aws_region,
                    )
                except Exception as e:
                    raise Exception(f"Failed to assume role: {str(e)}")

            try:
                runtime_kwargs = {}
                agent_kwargs = {}
                if self.valves.bedrock_runtime_endpoint_url:
                    runtime_kwargs['endpoint_url'] = self.valves.bedrock_runtime_endpoint_url
                if self.valves.bedrock_agent_runtime_endpoint_url:
                    agent_kwargs['endpoint_url'] = self.valves.bedrock_agent_runtime_endpoint_url

                self.bedrock_client = session.client('bedrock-runtime', **runtime_kwargs)
                self.bedrock_agent_client = session.client('bedrock-agent-runtime', **agent_kwargs)
                self._clients_initialized = True
            except Exception as e:
                self._clients_initialized = False
                raise Exception(f"Failed to initialize AWS clients: {str(e)}")

    async def emit_status(
        self,
        __event_emitter__: Optional[Callable[[dict], Awaitable[None]]],
        level: str,
        message: str,
        done: bool,
    ) -> None:
        """
        Emit status updates to the UI.
        
        Args:
            __event_emitter__: Callable function to emit events
            level: Status level (info, warning, error)
            message: Status message to display
            done: Whether this is the final status update
        """
        if not __event_emitter__:
            return
            
        current_time = time.time()
        if (
            self.valves.enable_status_indicator
            and (
                current_time - self.last_emit_time >= self.valves.emit_interval or done
            )
        ):
            await __event_emitter__(
                {
                    "type": "status",
                    "data": {
                        "status": "complete" if done else "in_progress",
                        "level": level,
                        "description": message,
                        "done": done,
                    },
                }
            )
            self.last_emit_time = current_time

    def _format_conversation_history(self, messages: List[Dict[str, str]]) -> str:
        """
        Format conversation history for context.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content' keys
            
        Returns:
            Formatted conversation history as a string
        """
        if not self.valves.use_conversation_history or not messages:
            return ""
            
        # Get the last N messages (excluding the current question)
        history_messages = messages[:-1] if len(messages) > 1 else []
        if len(history_messages) > self.valves.max_history_messages:
            history_messages = history_messages[-self.valves.max_history_messages:]
            
        if not history_messages:
            return ""
            
        formatted_history = "Previous conversation:\n\n"
        for msg in history_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                formatted_history += f"User: {content}\n\n"
            elif role == "assistant":
                formatted_history += f"Assistant: {content}\n\n"
                
        return formatted_history + "\n"

    def _get_model_family(self) -> ModelFamily:
        """
        Determine the model family from the model ID.
        
        Returns:
            ModelFamily enum representing the model family
        
        Raises:
            ValueError: If the model ID doesn't match any known family
        """
        model_id = self.valves.model_id.lower()
        
        if ModelFamily.CLAUDE3.value in model_id:
            return ModelFamily.CLAUDE3
                
        raise ValueError(f"Unsupported model ID: {model_id}. Only Claude 3 models are supported.")
    
    def _get_model_request_body(self, prompt: str) -> Dict[str, Any]:
        """
        Format the request body according to the model's requirements.
        
        Args:
            prompt: The prompt text to send to the model
            
        Returns:
            Dictionary containing the formatted request body
            
        Raises:
            ValueError: If the model ID is not supported
        """
        # Base parameters for Claude 3 models
        base_params = {
            "max_tokens": self.valves.max_tokens,
            "temperature": self.valves.temperature,
            "top_p": self.valves.top_p,
        }
        
        # Verify we're using a Claude 3 model
        model_family = self._get_model_family()
        
        if model_family == ModelFamily.CLAUDE3:
            return {
                "anthropic_version": "bedrock-2023-05-31",
                **base_params,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
        else:
            # This should never happen due to the check in _get_model_family
            raise ValueError(f"Unsupported model ID: {self.valves.model_id}. Only Claude 3 models are supported.")
            
    def _parse_model_response(self, response_body: Dict[str, Any]) -> str:
        """
        Parse the response body based on the model family.
        
        Args:
            response_body: The parsed JSON response from the model
            
        Returns:
            Extracted text from the model response
            
        Raises:
            ValueError: If the model ID is not supported
        """
        model_family = self._get_model_family()
        
        if model_family == ModelFamily.CLAUDE3:
            return response_body['content'][0]['text']
        else:
            # This should never happen due to the check in _get_model_family
            raise ValueError(f"Unsupported model ID: {self.valves.model_id}. Only Claude 3 models are supported.")

    async def _extract_datetime_references(self, query: str) -> Dict[str, Any]:
        """
        Extract date-time references from the user query using an LLM.
        
        Args:
            query: The user's question to extract date-time references from
            
        Returns:
            Dictionary containing extracted date-time information with ISO and Unix formats
        """
        try:
            # Create a prompt for extracting date-time references
            extraction_prompt = f"""Extract any date or time references from the following user query and convert them to a structured format.

User query: {query}

If the query contains date or time references, extract them and provide:
1. The original date/time expression as it appears in the query
2. The parsed date/time in ISO 8601 format (e.g., "2025-09-04T06:39:14Z")

Return ONLY valid JSON with no additional text. If no date/time references are found, return an empty array.

Example format:
[
    {{
        "original": "August 2025",
        "parsed": "2025-08-01T00:00:00Z"
    }},
    {{
        "original": "September 4th, 2025 at 6:39 AM",
        "parsed": "2025-09-04T06:39:00Z"
    }}
]

Extracted date-time references (JSON only):"""

            # Use the filter model for extraction
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 512,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": extraction_prompt
                    }
                ]
            }
            
            print(f"DEBUG - Extracting datetime references with model {self.valves.filter_model_id}")
            
            model_response = self.bedrock_client.invoke_model(
                modelId=self.valves.filter_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(model_response['body'].read())
            extraction_text = response_body['content'][0]['text'].strip()
            
            print(f"DEBUG - Extracted datetime text: {extraction_text}")
            
            # Remove markdown code blocks if present
            extraction_text = _remove_markdown_code_blocks(extraction_text)
            
            datetime_refs = json.loads(extraction_text)
            
            # Process each extracted datetime to add Unix timestamps
            processed_refs = []
            for ref in datetime_refs:
                iso_str = ref.get('parsed')
                if iso_str:
                    iso_format, unix_timestamp = parse_datetime_to_formats(iso_str)
                    if iso_format and unix_timestamp:
                        processed_refs.append({
                            'original': ref.get('original', ''),
                            'iso': iso_format,
                            'unix': unix_timestamp
                        })
            
            print(f"DEBUG - Processed datetime references: {json.dumps(processed_refs, indent=2)}")
            
            return {'datetime_refs': processed_refs}
            
        except json.JSONDecodeError as e:
            print(f"WARNING - Failed to parse datetime extraction: {str(e)}")
            return {'datetime_refs': []}
        except Exception as e:
            print(f"WARNING - Error extracting datetime references: {str(e)}")
            return {'datetime_refs': []}

    async def _generate_metadata_filter(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Generate metadata filters using a lightweight model based on the user query.
        
        Args:
            query: The user's question to generate filters from
            
        Returns:
            Dictionary containing the metadata filter, or None if filtering is disabled or generation fails
        """
        if not self.valves.enable_metadata_filtering:
            return None
            
        try:
            # Parse metadata definitions
            metadata_defs = json.loads(self.valves.metadata_definitions)
            if not metadata_defs:
                return None
            
            # Extract datetime references from the query
            datetime_info = await self._extract_datetime_references(query)
            datetime_refs = datetime_info.get('datetime_refs', [])
            
            # Build enhanced query with Unix timestamps and datetime context
            enhanced_query = query
            datetime_context = ""
            
            if datetime_refs:
                datetime_context = "\n\nExtracted date-time information:\n"
                for ref in datetime_refs:
                    datetime_context += f"- '{ref['original']}' -> ISO: {ref['iso']}, Unix: {ref['unix']}\n"
                    # Replace original datetime references with both formats in query (only first occurrence)
                    enhanced_query = enhanced_query.replace(
                        ref['original'], 
                        f"{ref['original']} (ISO: {ref['iso']}, Unix epoch: {ref['unix']})",
                        1
                    )
            
            # Create a prompt for the filter generation model
            filter_prompt = f"""Given the following metadata field definitions and user query, generate a metadata filter in JSON format that can be used to filter knowledge base results.

Metadata field definitions:
{json.dumps(metadata_defs, indent=2)}

User query: {enhanced_query}{datetime_context}

IMPORTANT INSTRUCTIONS FOR DATE/TIME FILTERING:
1. When filtering by date/time fields, check if the metadata definitions include both ISO format (STRING type) and Unix epoch (NUMBER type) fields.
2. For Unix epoch timestamp fields (NUMBER type with names like *_unix, *_timestamp, *_epoch):
   - Use numeric comparison operators: greaterThan, greaterThanOrEquals, lessThan, lessThanOrEquals
   - Use the Unix epoch value (integer) from the extracted date-time information above
   - Example: {{"greaterThan": {{"key": "created_at_unix", "value": 1725430754}}}}
3. For ISO format date fields (STRING type with names like *_iso, *_date, created_at):
   - Use string comparison operators if needed, but prefer Unix epoch fields when both are available
   - Use the ISO format string from the extracted date-time information
4. Unix epoch fields provide better performance for numeric range queries.

Generate a filter object that matches the AWS Bedrock Knowledge Base filter format. The filter should use operators like "equals", "notEquals", "in", "notIn", "greaterThan", "greaterThanOrEquals", "lessThan", "lessThanOrEquals", "stringContains", and logical operators "andAll" and "orAll".

Only generate filters for metadata fields that are clearly relevant to the user query. If no metadata filtering is needed, return an empty object {{}}.

Return ONLY valid JSON with no additional text or explanation. Example format:
{{
    "andAll": [
        {{
            "lessThan": {{
                "key": "created_at_unix",
                "value": 1725494399
            }}
        }},
        {{
            "in": {{
                "key": "author_name",
                "value": ["John Smith"]
            }}
        }}
    ]
}}

Generated filter (JSON only):"""

            # Use the filter model to generate the filter
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "temperature": 0.1,  # Low temperature for more consistent output
                "messages": [
                    {
                        "role": "user",
                        "content": filter_prompt
                    }
                ]
            }
            
            print(f"DEBUG - Generating metadata filter with model {self.valves.filter_model_id}")
            
            model_response = self.bedrock_client.invoke_model(
                modelId=self.valves.filter_model_id,
                body=json.dumps(request_body)
            )
            
            # Parse response
            response_body = json.loads(model_response['body'].read())
            filter_text = response_body['content'][0]['text'].strip()
            
            print(f"DEBUG - Generated filter text: {filter_text}")
            
            # Parse the JSON filter
            # Remove markdown code blocks if present
            filter_text = _remove_markdown_code_blocks(filter_text)
            
            metadata_filter = json.loads(filter_text)
            
            # Return None if empty filter
            if not metadata_filter or metadata_filter == {}:
                return None
                
            print(f"DEBUG - Parsed metadata filter: {json.dumps(metadata_filter, indent=2)}")
            return metadata_filter
            
        except json.JSONDecodeError as e:
            print(f"WARNING - Failed to parse metadata filter: {str(e)}")
            return None
        except Exception as e:
            print(f"WARNING - Error generating metadata filter: {str(e)}")
            return None

    async def query_knowledge_base(self, query: str, chat_id: Optional[str], conversation_history: str = "") -> str:
        """
        Query the AWS Bedrock Knowledge Base and generate a response.
        
        Args:
            query: The user's question to query the knowledge base with
            chat_id: The chat ID for context tracking (optional)
            conversation_history: Formatted conversation history for context (optional)
            
        Returns:
            Generated response based on knowledge base results
            
        Raises:
            ClientError: For AWS-specific errors
            Exception: For general errors during the query process
        """
        self._initialize_clients()
        
        try:
            # Generate metadata filter if enabled
            metadata_filter = await self._generate_metadata_filter(query)
            
            # Build vector search configuration
            vector_search_config = {
                'numberOfResults': self.valves.number_of_results,
                'overrideSearchType': 'HYBRID'
            }
            
            # Add filter if generated
            if metadata_filter:
                vector_search_config['filter'] = metadata_filter
            
            # Query the knowledge base
            response = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=self.valves.knowledge_base_id,
                retrievalQuery={
                    'text': query
                },
                retrievalConfiguration={
                    'vectorSearchConfiguration': vector_search_config
                }
            )
            
            # Extract retrieved passages
            retrieved_results = response.get('retrievalResults', [])
            context = ""
            
            # Add source information to each result
            for i, result in enumerate(retrieved_results, 1):
                if 'content' in result and 'text' in result['content']:
                    content = result['content']['text']
                    source = ""
                    if 'location' in result:
                        source = f" (Source: {result['location'].get('s3Location', {}).get('uri', 'Unknown')})"
                    context += f"[Document {i}{source}]\n{content}\n\n"
            
            # If no results were found
            if not context:
                return "I couldn't find any relevant information in the knowledge base."
            
            # Generate a response using the retrieved context and conversation history
            prompt = f"""
            {conversation_history}
            
            The following information was retrieved from a knowledge base:
            
            {context}
            
            Based on this information, please answer the following question:
            {query}
            
            If the information doesn't contain a clear answer, please say so.
            """
            
            try:
                request_body = self._get_model_request_body(prompt)
                print(f"DEBUG - Sending request to model {self.valves.model_id}: {json.dumps(request_body)}")
                
                model_response = self.bedrock_client.invoke_model(
                    modelId=self.valves.model_id,
                    body=json.dumps(request_body)
                )

                # Parse response using our helper method
                response_body = json.loads(model_response['body'].read())
                print(f"DEBUG - Raw response from model: {json.dumps(response_body)}")
                
                return self._parse_model_response(response_body)
                
            except ClientError as e:
                error_message = str(e)
                print(f"DEBUG - AWS Bedrock ClientError: {error_message}")
                
                if "AccessDeniedException" in error_message:
                    return "Error: Access denied to AWS Bedrock. Please check your AWS credentials and permissions."
                elif "ValidationException" in error_message:
                    # Error handling for validation exceptions
                    return f"Error: Invalid request to AWS Bedrock. Please check your model ID and parameters. Details: {error_message}"
                elif "ThrottlingException" in error_message:
                    return "Error: AWS Bedrock request was throttled. Please try again later."
                elif "ServiceQuotaExceededException" in error_message:
                    return "Error: AWS Bedrock service quota exceeded. Please try again later or request a quota increase."
                else:
                    return f"AWS Bedrock error: {error_message}"
                    
        except ClientError as e:
            if "ResourceNotFoundException" in str(e):
                return f"Error: Knowledge Base ID '{self.valves.knowledge_base_id}' not found. Please check your Knowledge Base ID."
            elif "AccessDeniedException" in str(e):
                return "Error: Access denied to AWS Bedrock Knowledge Base. Please check your AWS credentials and permissions."
            elif "ValidationException" in str(e):
                return "Error: Invalid request to AWS Bedrock Knowledge Base. Please check your parameters."
            else:
                return f"AWS Bedrock Knowledge Base error: {str(e)}"
        except Exception as e:
            error_message = f"Error querying knowledge base: {str(e)}"
            return error_message

    async def pipe(
        self,
        body: Dict[str, Any],
        user: Optional[Dict[str, Any]] = None,
        __event_emitter__: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
        __event_call__: Optional[Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = None,
    ) -> Union[str, Dict[str, str]]:
        """
        Main pipe function that processes the input and returns a response.
        
        This is the entry point for the AWS Bedrock Knowledge Base integration.
        It processes the input message, queries the knowledge base, and returns
        a response based on the retrieved information.
        
        Args:
            body: The request body containing messages
            user: User information (optional)
            __event_emitter__: Function to emit events for status updates
            __event_call__: Function to make event calls (not used in this implementation)
            
        Returns:
            Either the generated response as a string or an error dictionary
        """
        await self.emit_status(
            __event_emitter__, "info", "Querying AWS Bedrock Knowledge Base...", False
        )
        
        chat_id, _ = extract_event_info(__event_emitter__)
        messages = body.get("messages", [])
        
        # Verify a message is available
        if messages:
            question = messages[-1]["content"]
            try:
                # Check if AWS credentials are provided
                if not self.valves.aws_access_key_id or not self.valves.aws_secret_access_key:
                    error_message = "AWS credentials are not configured. Please set aws_access_key_id and aws_secret_access_key in the function settings."
                    await self.emit_status(__event_emitter__, "error", error_message, True)
                    body["messages"].append({"role": "assistant", "content": error_message})
                    return {"error": error_message}
                    
                # Check if Knowledge Base ID is provided
                if not self.valves.knowledge_base_id:
                    error_message = "Knowledge Base ID is not configured. Please set knowledge_base_id in the function settings."
                    await self.emit_status(__event_emitter__, "error", error_message, True)
                    body["messages"].append({"role": "assistant", "content": error_message})
                    return {"error": error_message}
                
                # Format conversation history if enabled
                conversation_history = ""
                if self.valves.use_conversation_history:
                    await self.emit_status(
                        __event_emitter__, "info", "Processing conversation history...", False
                    )
                    conversation_history = self._format_conversation_history(messages)
                
                # Query the knowledge base
                await self.emit_status(
                    __event_emitter__, "info", "Retrieving information from Knowledge Base...", False
                )
                
                kb_response = await self.query_knowledge_base(question, chat_id, conversation_history)
                
                # Set assistant message with response
                body["messages"].append({"role": "assistant", "content": kb_response})
                
                await self.emit_status(__event_emitter__, "info", "Complete", True)
                return kb_response
                
            except Exception as e:
                error_message = f"Error during knowledge base query: {str(e)}"
                await self.emit_status(
                    __event_emitter__,
                    "error",
                    error_message,
                    True,
                )
                body["messages"].append(
                    {
                        "role": "assistant",
                        "content": error_message,
                    }
                )
                return {"error": error_message}
        # If no message is available alert user
        else:
            error_message = "No messages found in the request body"
            await self.emit_status(
                __event_emitter__,
                "error",
                error_message,
                True,
            )
            body["messages"].append(
                {
                    "role": "assistant",
                    "content": error_message,
                }
            )
            return {"error": error_message}