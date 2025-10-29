"""AWS Bedrock pipeline for OpenWebUI

This manifold pipeline allows selecting from multiple Knowledge Bases.
Configure the available pipelines using the ``AWS_BEDROCK_KB_IDS`` and
``AWS_BEDROCK_KB_NAMES`` environment variables.
"""

from typing import List, Union, Generator, Iterator
from pydantic import BaseModel, Field
import boto3
import json
import os


class Pipeline:
    class Valves(BaseModel):
        """Configuration options for the pipeline."""

        aws_access_key_id: str = Field(default="", description="AWS Access Key ID")
        aws_secret_access_key: str = Field(default="", description="AWS Secret Access Key")
        aws_region: str = Field(default="eu-central-1", description="AWS Region")
        knowledge_base_ids: str = Field(default="", description="Semicolon separated knowledge base IDs")
        knowledge_base_names: str = Field(default="", description="Semicolon separated knowledge base names")
        model_id: str = Field(default="anthropic.claude-3-5-sonnet-20240620-v1:0", description="Model ID for generation")
        max_tokens: int = Field(default=4096, description="Maximum tokens in response")
        temperature: float = Field(default=0.7, description="Generation temperature")
        top_p: float = Field(default=0.9, description="Top-p sampling")
        number_of_results: int = Field(default=5, description="Number of results to retrieve")
        bedrock_runtime_endpoint_url: str = Field(default="", description="Custom endpoint for bedrock-runtime")
        bedrock_agent_runtime_endpoint_url: str = Field(default="", description="Custom endpoint for bedrock-agent-runtime")
        enable_metadata_filtering: bool = Field(default=False, description="Enable metadata filter generation")
        filter_model_id: str = Field(default="anthropic.claude-3-haiku-20240307-v1:0", description="Model ID for filter generation")
        metadata_definitions: str = Field(default="[]", description="JSON array of metadata field definitions")

    def __init__(self):
        self.type = "manifold"
        self.name = "AWS Bedrock KB: "
        self.valves = self.Valves(
            **{
                "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
                "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
                "aws_region": os.getenv("AWS_REGION", "eu-central-1"),
                "knowledge_base_ids": os.getenv("AWS_BEDROCK_KB_IDS", ""),
                "knowledge_base_names": os.getenv("AWS_BEDROCK_KB_NAMES", ""),
                "model_id": os.getenv("MODEL_ID", "anthropic.claude-3-5-sonnet-20240620-v1:0"),
                "max_tokens": int(os.getenv("MAX_TOKENS", 4096)),
                "temperature": float(os.getenv("TEMPERATURE", 0.7)),
                "top_p": float(os.getenv("TOP_P", 0.9)),
                "number_of_results": int(os.getenv("NUMBER_OF_RESULTS", 5)),
                "bedrock_runtime_endpoint_url": os.getenv("BEDROCK_RUNTIME_ENDPOINT_URL", ""),
                "bedrock_agent_runtime_endpoint_url": os.getenv("BEDROCK_AGENT_RUNTIME_ENDPOINT_URL", ""),
            }
        )
        self._clients_initialized = False
        self.bedrock_client = None
        self.bedrock_agent_client = None
        self.set_pipelines()

    def set_pipelines(self) -> None:
        ids = [i for i in self.valves.knowledge_base_ids.split(";") if i]
        names = [n for n in self.valves.knowledge_base_names.split(";") if n]
        self.pipelines = [
            {"id": kb_id, "name": name} for kb_id, name in zip(ids, names)
        ]
        if not self.pipelines and ids:
            self.pipelines = [{"id": kb_id, "name": kb_id} for kb_id in ids]
        print(f"aws_bedrock_pipeline - knowledge bases: {self.pipelines}")

    async def on_valves_updated(self):
        self.set_pipelines()
        self._clients_initialized = False
        self._initialize_clients()

    async def on_startup(self):
        print(f"on_startup:{__name__}")

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")

    def _initialize_clients(self) -> None:
        if self._clients_initialized:
            return
        session = boto3.Session(
            aws_access_key_id=self.valves.aws_access_key_id,
            aws_secret_access_key=self.valves.aws_secret_access_key,
            region_name=self.valves.aws_region,
        )
        runtime_kwargs = {}
        agent_kwargs = {}
        if self.valves.bedrock_runtime_endpoint_url:
            runtime_kwargs["endpoint_url"] = self.valves.bedrock_runtime_endpoint_url
        if self.valves.bedrock_agent_runtime_endpoint_url:
            agent_kwargs["endpoint_url"] = self.valves.bedrock_agent_runtime_endpoint_url
        self.bedrock_client = session.client("bedrock-runtime", **runtime_kwargs)
        self.bedrock_agent_client = session.client("bedrock-agent-runtime", **agent_kwargs)
        self._clients_initialized = True

    def _format_history(self, messages: List[dict]) -> str:
        history_messages = messages[:-1] if len(messages) > 1 else []
        if not history_messages:
            return ""
        formatted = "Previous conversation:\n\n"
        for msg in history_messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "user":
                formatted += f"User: {content}\n\n"
            elif role == "assistant":
                formatted += f"Assistant: {content}\n\n"
        return formatted + "\n"

    def _generate_metadata_filter(self, query: str) -> Union[dict, None]:
        """Generate metadata filter using a lightweight model."""
        if not self.valves.enable_metadata_filtering:
            return None
        try:
            metadata_defs = json.loads(self.valves.metadata_definitions)
            if not metadata_defs:
                return None
            filter_prompt = f"""Given the following metadata field definitions and user query, generate a metadata filter in JSON format that can be used to filter knowledge base results.

Metadata field definitions:
{json.dumps(metadata_defs, indent=2)}

User query: {query}

Generate a filter object that matches the AWS Bedrock Knowledge Base filter format. The filter should use operators like "equals", "notEquals", "in", "notIn", "greaterThan", "greaterThanOrEquals", "lessThan", "lessThanOrEquals", "stringContains", and logical operators "andAll" and "orAll".

Only generate filters for metadata fields that are clearly relevant to the user query. If no metadata filtering is needed, return an empty object {{}}.

Return ONLY valid JSON with no additional text or explanation.

Generated filter (JSON only):"""
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1024,
                "temperature": 0.1,
                "messages": [{"role": "user", "content": filter_prompt}]
            }
            model_response = self.bedrock_client.invoke_model(
                modelId=self.valves.filter_model_id, body=json.dumps(request_body)
            )
            response_body = json.loads(model_response["body"].read())
            filter_text = response_body["content"][0]["text"].strip()
            if filter_text.startswith("```"):
                filter_text = filter_text.split("```")[1]
                if filter_text.startswith("json"):
                    filter_text = filter_text[4:]
                filter_text = filter_text.strip()
            metadata_filter = json.loads(filter_text)
            if not metadata_filter or metadata_filter == {}:
                return None
            return metadata_filter
        except Exception as e:
            print(f"WARNING - Error generating metadata filter: {str(e)}")
            return None

    def pipe(
        self, user_message: str, model_id: str, messages: List[dict], body: dict
    ) -> Union[str, Generator[str, None, None], Iterator[str]]:
        print(f"pipe:{__name__}")
        self._initialize_clients()
        history = self._format_history(messages)
        try:
            # Generate metadata filter if enabled
            metadata_filter = self._generate_metadata_filter(user_message)
            
            # Build vector search configuration
            vector_search_config = {
                "numberOfResults": self.valves.number_of_results,
                "overrideSearchType": "HYBRID"
            }
            
            # Add filter if generated
            if metadata_filter:
                vector_search_config["filter"] = metadata_filter
            
            retrieve_resp = self.bedrock_agent_client.retrieve(
                knowledgeBaseId=model_id,
                retrievalQuery={"text": user_message},
                retrievalConfiguration={
                    "vectorSearchConfiguration": vector_search_config
                },
            )
            context = ""
            for i, result in enumerate(retrieve_resp.get("retrievalResults", []), 1):
                if "content" in result and "text" in result["content"]:
                    source = ""
                    if "location" in result:
                        source = f" (Source: {result['location'].get('s3Location', {}).get('uri', 'Unknown')})"
                    context += f"[Document {i}{source}]\n{result['content']['text']}\n\n"
            if not context:
                return "I couldn't find any relevant information in the knowledge base."
            prompt = f"""{history}
The following information was retrieved from a knowledge base:

{context}
Based on this information, please answer the following question:
{user_message}
If the information doesn't contain a clear answer, please say so."""
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.valves.max_tokens,
                "temperature": self.valves.temperature,
                "top_p": self.valves.top_p,
                "messages": [{"role": "user", "content": prompt}],
            }
            response = self.bedrock_client.invoke_model(
                modelId=self.valves.model_id, body=json.dumps(request_body)
            )
            resp_body = json.loads(response["body"].read())
            return resp_body["content"][0]["text"]
        except Exception as e:
            return f"Error querying knowledge base: {str(e)}"
