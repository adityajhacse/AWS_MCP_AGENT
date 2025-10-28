import os
import shutil
from typing import Dict, List
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


# --- 1. DEFINE AVAILABLE PROFILES ---
AVAILABLE_PROFILES = ["default", "infdev", "dev", "046621545380_AccountUser"]

# --- 2. GET USER SELECTION ---
print("Available AWS Profiles:")
for i, profile in enumerate(AVAILABLE_PROFILES):
    print(f"  [{i+1}] {profile}")

# Loop until a valid choice is made
while True:
    try:
        # Prompt the user for input
        choice = input(f"Select an AWS Profile (1-{len(AVAILABLE_PROFILES)}): ")
        
        # Convert choice to an index (0-based)
        profile_index = int(choice) - 1
        
        # Validate the index
        if 0 <= profile_index < len(AVAILABLE_PROFILES):
            aws_profile = AVAILABLE_PROFILES[profile_index]
            print(f"\nSelected profile: {aws_profile}\n")
            break
        else:
            print("Invalid number. Please select a number from the list.")
    except ValueError:
        print("Invalid input. Please enter a number.")
    except Exception as e:
        # This catches errors like Ctrl+C during input, which might be helpful
        print(f"An unexpected error occurred: {e}")
        exit()

# --- EXISTING CONFIGURATION ---
aws_environment = "dev"
aws_region     = "us-west-2"
# aws_profile is now set by the user's input

def toolset(pkg: str, env: Dict[str, str]) -> MCPToolset:
    # Use shutil.which for portability, fall back to the explicit path if not found in PATH
    uvx = shutil.which("uvx") or "/Users/aditya.jha/.local/bin/uvx" 
    args = [pkg]
    return MCPToolset(
        connection_params=StdioConnectionParams(
            # Increased timeout to prevent initial connection issues
            timeout_s=30.0,
            server_params=StdioServerParameters(
                command=uvx,
                args=args,            
                env=dict(env),       
            )
        )
    )

# Define the environment dictionary using the selected aws_profile
aws_env_config = {
    "AWS_ENVIRONMENT": aws_environment,
    "AWS_REGION": aws_region,
    "AWS_PROFILE": aws_profile, # <-- Uses the user's selected profile
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

# You can now proceed to run the agent with the selected profile
# Example: root_agent.run("What is the current status of the EC2 instance in us-west-2?")