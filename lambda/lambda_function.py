"""
GeekBrain AI Assistant — Lambda Handler (L3: Bedrock Agent)
Invokes Bedrock Agent which orchestrates KB retrieval + tool calling.
"""

import json
import os
import boto3

AGENT_ID = os.environ.get("AGENT_ID", "")
AGENT_ALIAS_ID = os.environ.get("AGENT_ALIAS_ID", "")
AWS_REGION = os.environ.get("AWS_REGION_NAME", "us-east-1")

bedrock_agent_runtime = boto3.client("bedrock-agent-runtime", region_name=AWS_REGION)

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Content-Type": "application/json",
}


def handler(event, context):
    """Lambda handler for API Gateway proxy integration."""
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return {"statusCode": 200, "headers": CORS_HEADERS, "body": ""}

    try:
        body = json.loads(event.get("body", "{}"))
        question = body.get("question", "").strip()
        session_id = body.get("session_id", "default-session")

        if not question:
            return _response(400, {"error": "Missing 'question' field"})

        if not AGENT_ID or not AGENT_ALIAS_ID:
            return _response(500, {"error": "AGENT_ID or AGENT_ALIAS_ID not configured"})

        # Invoke Bedrock Agent — it handles KB retrieval + tool calling + LLM
        answer, trace_info = invoke_agent(question, session_id)

        return _response(200, {
            "answer": answer,
            "session_id": session_id,
            "tools_used": trace_info.get("tools_used", []),
            "sources": trace_info.get("sources", []),
        })

    except Exception as e:
        print(f"Error: {e}")
        return _response(500, {"error": str(e)})


def invoke_agent(question, session_id):
    """Invoke Bedrock Agent and collect the streamed response."""
    response = bedrock_agent_runtime.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=AGENT_ALIAS_ID,
        sessionId=session_id,
        inputText=question,
        enableTrace=True,
    )

    answer = ""
    trace_info = {"tools_used": [], "sources": []}

    for event_stream in response.get("completion", []):
        # Collect answer chunks
        if "chunk" in event_stream:
            chunk_bytes = event_stream["chunk"].get("bytes", b"")
            answer += chunk_bytes.decode("utf-8")

        # Collect trace information (tools used, KB sources)
        if "trace" in event_stream:
            trace = event_stream["trace"].get("trace", {})

            # Check for action group invocations (tool calls)
            orchestration = trace.get("orchestrationTrace", {})
            if "invocationInput" in orchestration:
                inv = orchestration["invocationInput"]
                if "actionGroupInvocationInput" in inv:
                    tool_name = inv["actionGroupInvocationInput"].get("function", "")
                    if tool_name and tool_name not in trace_info["tools_used"]:
                        trace_info["tools_used"].append(tool_name)

            # Check for KB retrieval (source documents)
            if "invocationInput" in orchestration:
                inv = orchestration["invocationInput"]
                if "knowledgeBaseLookupInput" in inv:
                    trace_info["sources"].append("knowledge_base")

    return answer, trace_info


def _response(status_code, body):
    """Build API Gateway proxy response."""
    return {
        "statusCode": status_code,
        "headers": CORS_HEADERS,
        "body": json.dumps(body),
    }
