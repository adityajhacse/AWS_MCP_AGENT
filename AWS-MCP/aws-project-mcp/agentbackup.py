import os, shutil
import sys
import configparser
from os import path
from typing import Dict, List
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters


aws_environment = "dev"
aws_region     = "us-west-2"

# Hardcoded profiles to present during prompt; extend this list as needed
HARDCODED_AWS_PROFILES: List[str] = [
    "046621545380_AccountUser",
    "infssdev",
]

# Default profile to use when none is provided via environment and no prompt occurs
aws_profile_default: str = HARDCODED_AWS_PROFILES[0]



def load_available_aws_profiles() -> List[str]:
    """Return a list of available AWS profile names from ~/.aws/credentials and ~/.aws/config."""
    profiles: List[str] = []
    credentials_path = path.expanduser("~/.aws/credentials")
    config_path = path.expanduser("~/.aws/config")

    parser = configparser.ConfigParser()

    if path.exists(credentials_path):
        try:
            parser.read(credentials_path)
            for section in parser.sections():
                if section not in profiles:
                    profiles.append(section)
        except Exception:
            pass

    # Separate parser for config to avoid section bleed
    config_parser = configparser.ConfigParser()
    if path.exists(config_path):
        try:
            config_parser.read(config_path)
            for section in config_parser.sections():
                # Sections in config are often like: "profile myprofilename"
                name = section.replace("profile ", "") if section.startswith("profile ") else section
                if name not in profiles:
                    profiles.append(name)
        except Exception:
            pass

    return profiles


def prompt_for_aws_profile(default_profile: str, choices: List[str]) -> str:
    """Prompt the user to choose an AWS CLI profile from a provided list.

    Returns the selected profile or the default if input is empty/invalid.
    Does not read profiles from local files.
    """
    # Non-interactive environments: honor pre-set AWS_PROFILE or fall back immediately
    env_profile = os.environ.get("AWS_PROFILE")
    if env_profile:
        return env_profile
    if not sys.stdin.isatty():
        return default_profile

    available = list(dict.fromkeys(choices))  # de-duplicate while preserving order
    if not available:
        return default_profile

    print("\nSelect an AWS profile (press Enter for default):")
    for idx, name in enumerate(available, start=1):
        print(f"  {idx}. {name}")
    print(f"Default: {default_profile}")

    user_input = input("Profile name or number: ").strip()
    if user_input == "":
        return default_profile

    # Allow numeric selection
    if user_input.isdigit():
        try:
            index = int(user_input) - 1
            if 0 <= index < len(available):
                return available[index]
        except Exception:
            pass

    # Fallback to validating by name
    if user_input in available:
        return user_input

    print("Unrecognized profile; using default.")
    return default_profile


def build_agent_with_profile(profile_name: str) -> LlmAgent:
    """Construct and return an LlmAgent configured with the provided AWS profile."""
    env_config = {
        "AWS_ENVIRONMENT": aws_environment,
        "AWS_REGION": aws_region,
        "AWS_PROFILE": profile_name,
    }

    # Ensure environment variables are also set for child processes
    os.environ.update(env_config)

    configured_tools = [
        toolset("awslabs.cloudwatch-mcp-server@latest", env=env_config),
        toolset("awslabs.terraform-mcp-server@latest", env=env_config),
        toolset("awslabs.iam-mcp-server@latest", env=env_config),
    ]

    return LlmAgent(
        name="AWS_agent",
        model="gemini-2.5-flash",
        tools=configured_tools,
        description="AWS Agent",
        instruction="You are a helpful assistant that can answer questions about AWS.",
    )


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

def _resolve_initial_profile() -> str:
    env_profile = os.environ.get("AWS_PROFILE")
    return env_profile if isinstance(env_profile, str) and env_profile else aws_profile_default

# Build a default agent at import time using a string profile (env or default)
root_agent = build_agent_with_profile(_resolve_initial_profile())


def main() -> None:
    """Prompt for AWS profile and rebuild the agent with the selected profile."""
    selected = prompt_for_aws_profile(aws_profile_default, HARDCODED_AWS_PROFILES)
    agent = build_agent_with_profile(selected)
    # Keep the exported name consistent for callers that expect root_agent
    global root_agent
    root_agent = agent
    print(f"Using AWS profile: {selected}")


if __name__ == "__main__":
    main()