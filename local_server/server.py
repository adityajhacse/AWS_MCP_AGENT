import asyncio
import json
import logging
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from mcp import types as mcp_types
from mcp.server.lowlevel import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
from google.adk.tools.function_tool import FunctionTool
from google.adk.tools.mcp_tool.conversion_utils import adk_to_mcp_tool_type

# -----------------------------------------------------------
# Load environment
# -----------------------------------------------------------
load_dotenv()  # Load .env if present

# -----------------------------------------------------------
# Logging
# -----------------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------
# Tool: List IAM Users
# -----------------------------------------------------------
def list_iam_users() -> dict:
    """Fetch and display IAM users in a formatted table."""
    try:
        iam_client = boto3.client(
            "iam",
            region_name=os.getenv("AWS_REGION", "us-west-2"),
        )

        paginator = iam_client.get_paginator("list_users")
        users = []
        for page in paginator.paginate():
            for user in page["Users"]:
                users.append({
                    "UserName": user["UserName"],
                    "UserId": user["UserId"],
                    "CreateDate": str(user["CreateDate"])[:19],
                })

        if not users:
            return {"message": "🚫 No IAM users found in this AWS account."}

        max_name = max(len(u["UserName"]) for u in users)
        max_id = max(len(u["UserId"]) for u in users)
        max_date = max(len(u["CreateDate"]) for u in users)

        separator = f"+{'-'*(max_name+2)}+{'-'*(max_id+2)}+{'-'*(max_date+2)}+"
        header = (
            f"| {'User Name'.ljust(max_name)} "
            f"| {'User ID'.ljust(max_id)} "
            f"| {'Created On'.ljust(max_date)} |"
        )

        rows = "\n".join(
            f"| {u['UserName'].ljust(max_name)} "
            f"| {u['UserId'].ljust(max_id)} "
            f"| {u['CreateDate'].ljust(max_date)} |"
            for u in users
        )

        table = f"{separator}\n{header}\n{separator}\n{rows}\n{separator}"

        total_users = len(users)
        region = os.getenv("AWS_REGION", "us-west-2")

        summary_box = (
            f"\n📋 **Summary:**\n"
            f"```\n"
            f"Region       : {region}\n"
            f"Total Users  : {total_users}\n"
            f"```\n"
        )

        formatted_output = (
            f"👥 **AWS IAM Users Summary**\n\n"
            f"```text\n{table}\n```\n"
            f"{summary_box}"
            f"✅ Successfully retrieved IAM users from AWS."
        )

        return {"markdown": formatted_output, "TotalUsers": total_users}

    except (NoCredentialsError, PartialCredentialsError):
        return {"error": "❌ AWS credentials not found. Please configure using `aws configure` or set environment variables."}
    except Exception as e:
        logger.error("Error listing IAM users: %s", e)
        return {"error": str(e)}

# -----------------------------------------------------------
# MCP Server Setup
# -----------------------------------------------------------
app = Server("aws-iam-mcp-server")

LIST_IAM_USERS_TOOL = FunctionTool(func=list_iam_users)

# -----------------------------------------------------------
# List Tools
# -----------------------------------------------------------
@app.list_tools()
async def list_tools() -> list[mcp_types.Tool]:
    return [adk_to_mcp_tool_type(LIST_IAM_USERS_TOOL)]

# -----------------------------------------------------------
# Call Tool
# -----------------------------------------------------------
@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name != LIST_IAM_USERS_TOOL.name:
        return [mcp_types.TextContent(type="text", text=json.dumps({"error": "Tool not found"}))]

    result = await LIST_IAM_USERS_TOOL.run_async(args=arguments, tool_context=None)
    return [mcp_types.TextContent(type="text", text=json.dumps(result, indent=2))]

# -----------------------------------------------------------
# Run MCP Server
# -----------------------------------------------------------
async def run_mcp_server():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logging.info("🚀 Starting AWS IAM MCP server...")
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=app.name,
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(run_mcp_server())
