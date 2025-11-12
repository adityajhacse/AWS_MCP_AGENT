import os
import shutil
from typing import Dict
import boto3
from datetime import datetime, timezone
from google.adk.agents import Agent
from google.adk.tools.agent_tool import AgentTool
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# ----------------------------
# AWS Environment Configuration
# ----------------------------
aws_environment = "dev"
aws_region = "us-west-2"
aws_profile = "your-profile"

aws_env_config = {
    "AWS_ENVIRONMENT": aws_environment,
    "AWS_REGION": aws_region,
    "AWS_PROFILE": aws_profile,
}

# ----------------------------
# MCP Toolset Helper
# ----------------------------
def toolset(pkg: str, env: Dict[str, str]) -> MCPToolset:
    """Creates MCP tool connection using uvx."""
    uvx = shutil.which("uvx") or os.path.expanduser("~/.local/bin/uvx")
    if not shutil.which("uvx"):
        raise RuntimeError("❌ 'uvx' not found. Please install it with: pip install uv")

    print(f"🔧 Initializing MCP tool: {pkg}")
    tool = MCPToolset(
        connection_params=StdioConnectionParams(
            timeout_s=120.0,
            server_params=StdioServerParameters(
                command=uvx,
                args=[pkg],
                env=env
            )
        )
    )
    tool.description = f"Provides AWS IAM or Terraform capabilities using {pkg}."
    return tool

# ----------------------------
# IAM Key Validation Function
# ----------------------------
iam = boto3.client("iam")

def validate_iam_access_keys(age_threshold: int = 100) -> str:
    """
    Validates IAM user access keys and lists any keys older than the given threshold (in days).
    """
    print(f"🔍 Tool executed: Validating IAM access keys older than {age_threshold} days...")

    now = datetime.now(timezone.utc)
    old_keys = []

    try:
        user_paginator = iam.get_paginator("list_users")
        for user_page in user_paginator.paginate():
            for user in user_page["Users"]:
                username = user["UserName"]
                key_paginator = iam.get_paginator("list_access_keys")
                for key_page in key_paginator.paginate(UserName=username):
                    for key in key_page["AccessKeyMetadata"]:
                        key_age_days = (now - key["CreateDate"]).days
                        if key_age_days > age_threshold:
                            old_keys.append({
                                "UserName": username,
                                "AccessKeyId": key["AccessKeyId"],
                                "Status": key["Status"],
                                "KeyAgeDays": key_age_days
                            })
    except Exception as e:
        return f"Error during IAM validation: {str(e)}"

    if not old_keys:
        return f" All IAM access keys are within {age_threshold} days. No action needed."

    message_lines = [
        f"Found {len(old_keys)} IAM access keys older than {age_threshold} days:",
        "------------------------------------------------------------"
    ]
    for item in old_keys:
        message_lines.append(
            f"- {item['UserName']} | {item['AccessKeyId']} | {item['Status']} | {item['KeyAgeDays']} days old"
        )

    return "\n".join(message_lines)

# ----------------------------
# IAM Validation Agent
# ----------------------------
iam_access_key_validate_agent = Agent(
    name="iam_access_key_validate_agent",
    model="gemini-2.5-flash",
    description="Agent specialized in validating AWS IAM access keys and auditing their ages.",
    instruction="""
    You are an IAM access key validation assistant.

    Responsibilities:
    - Use the `validate_iam_access_keys` tool when the user requests to
      check or audit IAM access keys.
    - Report IAM users whose access keys are older than a specified threshold (default 100 days).
    - Present results clearly with username, access key ID, status, and key age in days.

    You do not perform unrelated tasks like event planning or infrastructure deployment.
    """,
    tools=[validate_iam_access_keys]
)

# ----------------------------
# Event Planner Agent (AWS MCP)
# ----------------------------
def create_event_planner_agent():
    """Create event planner agent integrated with AWS MCP tools"""
    print(" Creating Event Planner Agent with MCP integrations...")
    return Agent(
        name="event_planner_agent",
        model="gemini-2.5-flash",
        description="Agent specialized in generating event plans and integrating with AWS MCP servers.",
        instruction="""
        You are an expert event planner and AWS operator.

        Tasks:
        - Suggest event themes or venues if asked.
        - For AWS-related queries:
          - Use the `awslabs.iam-mcp-server@latest` tool to list IAM users, roles, or permissions.
          - Use the `awslabs.terraform-mcp-server@latest` tool to manage Terraform resources.

        Examples:
        - If user says "List all IAM users" → call the IAM MCP server tool.
        - If user says "Show Terraform state" → call the Terraform MCP server tool.

        Do not respond yourself — always delegate the actual AWS operations to the corresponding MCP tool.
        """,
        tools=[
            toolset("awslabs.iam-mcp-server@latest", env=aws_env_config),
            toolset("awslabs.terraform-mcp-server@latest", env=aws_env_config),
        ]
    )

event_planner_agent = create_event_planner_agent()
print(f" Agent '{event_planner_agent.name}' created and ready to use!")

# ----------------------------
# Root Orchestrator Agent
# ----------------------------
event_planner_agent= AgentTool(agent=event_planner_agent)
iam_validator_tool = AgentTool(agent=iam_access_key_validate_agent)

root_orchestrator_agent = Agent(
    name="root_orchestrator_agent",
    model="gemini-2.5-flash",
    description="The orchestrator that routes user queries to the correct specialist agent.",
    instruction="""
    You are the root orchestrator managing user requests.

    - If the user asks for IAM user details, AWS account info, or infrastructure actions,
      use the `event_planner_agent`.

    - If the user asks for IAM access key validation, expired key reports, or key audits,
      use the `iam_validator_tool`.

    Do not answer user queries directly — always delegate to the proper tool.
    Log every delegation clearly to track which tool handled the query.
    """,
    tools=[event_planner_agent, iam_validator_tool]
)

root_agent = root_orchestrator_agent
print(" Root Orchestrator Agent initialized successfully!")

