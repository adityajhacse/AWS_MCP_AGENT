import os
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

# Load env
load_dotenv()

# Define the root agent
root_agent = LlmAgent(
    name="aws_iam_agent",
    model="gemini-2.0-flash",
    instruction=(
        "You are an AWS assistant. When user asks to 'list IAM users', "
        "call the 'list_iam_users' tool to fetch users from AWS."
    ),
    tools=[
        MCPToolset(
            connection_params=StdioServerParameters(
                command="/app/.venv/bin/python3",
                args=["/app/local_server/server.py"],  # Adjust path as needed
            ),
        )
    ],
)
