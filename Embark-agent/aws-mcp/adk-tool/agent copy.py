# import boto3
import os, shutil
from typing import Dict, List
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


aws_environment = "dev"
aws_region     = "us-west-2"
# aws_profile = "046621545380_AccountUser"



def toolset(pkg: str, env: Dict[str, str]) -> McpToolset:
    # uvx = shutil.which("uvx") # or "/Users/aditya.jha/.local/bin/uvx"
    uvx = shutil.which("uvx")
    if uvx is None:
        raise RuntimeError("uvx not found in PATH. Make sure uvx is installed in local or in the Docker container")

    args = [pkg]
    return McpToolset(
        connection_params=StdioConnectionParams(
            # ADD THIS LINE TO INCREASE THE TIMEOUT FOR MCP SERVER
            timeout_s=60.0,
            server_params=StdioServerParameters(
                command=uvx,
                args=args,            
                env=dict(env),       
            )
        )
    )


# Define the environment dictionary
aws_env_config = {
    "AWS_ENVIRONMENT": aws_environment,
    "AWS_REGION": aws_region,
    # "AWS_PROFILE": aws_profile,
}

# Prefer explicit credentials from environment variables
_env_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
_env_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
_env_session_token = os.environ.get("AWS_SESSION_TOKEN")

if _env_access_key and _env_secret_key:
    aws_env_config["AWS_ACCESS_KEY_ID"] = _env_access_key
    aws_env_config["AWS_SECRET_ACCESS_KEY"] = _env_secret_key
    if _env_session_token:
        aws_env_config["AWS_SESSION_TOKEN"] = _env_session_token

tools = [
    toolset("awslabs.cloudwatch-mcp-server@latest",env=aws_env_config),     
    toolset("awslabs.terraform-mcp-server@latest", env=aws_env_config),  
    toolset("awslabs.iam-mcp-server@latest", env=aws_env_config),  
]

root_agent = LlmAgent(
    name="AWS_agent",
    model="gemini-2.5-flash",
    tools=tools,
    description="AWS Agent",
    instruction="You are a helpful assistant that can answer questions about AWS.",
)

