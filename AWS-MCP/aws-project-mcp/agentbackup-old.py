import os, shutil
from typing import Dict, List
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


aws_environment = "dev"
aws_region     = "us-west-2"
aws_profile = "046621545380_AccountUser"


def toolset(pkg: str, env: Dict[str, str]) -> MCPToolset:
    uvx = shutil.which("uvx") or "/Users/aditya.jha/.local/bin/uvx"
    args = [pkg]
    return MCPToolset(
        connection_params=StdioConnectionParams(
            # ADD THIS LINE TO INCREASE THE TIMEOUT FOR MCP SERVER
            timeout_s=30.0,
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
    "AWS_PROFILE": aws_profile,
}

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