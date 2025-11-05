Note: WE have build MCP Docker image locally and pushed it to ECR. Now we need to deploy it to ECS.
This usage agent.py to test the MCP server.
and docker file to build the MCP server.

# Use terraform to deploy the MCP server to ECS, ECR and Secrets Manager and networking

# Push ECR Image to ECR using the docker file:
aws ecr get-login-password —region us-west-2 | docker login —username AWS —password-stdin 046621545380.dkr.ecr.us-west-2.amazonaws.com
docker build -t adk-mcp-demo-ecr .
docker tag adk-mcp-demo-ecr:latest 046621545380.dkr.ecr.us-west-2.amazonaws.com/adk-mcp-demo-ecr:latest
docker push 046621545380.dkr.ecr.us-west-2.amazonaws.com/adk-mcp-demo-ecr:latest


# Update Secrets Manager with the secrets:
aws secretsmanager put-secret-value \
  --secret-id adk-mcp-demo-sm \
  --secret-string '{"GOOGLE_API_KEY": "",
    "AWS_REGION": "us-west-2",
    "AWS_ENVIRONMENT": "dev",
    "ADK_MCP_REQUEST_TIMEOUT": "60",
    "GOOGLE_GENAI_USE_VERTEXAI": "0",
    "AWS_ACCESS_KEY_ID": "",
    "AWS_SECRET_ACCESS_KEY": ""}'

# Once Task is Running, you can test the MCP server using : http://54.218.23.11:8000/dev-ui where 54.218.23.11 is the public IP of the ECS instance.


To Test the MCP server locally:
docker build -t adk-tool.
docker run -it adk-tool
# Map container port 8000 to host port 8000
docker run -p 8000:8000 adk-tool

# Example: Pass your exported AWS variables
docker build -t agents .
docker stop aws-agent-container
docker rm aws-agent-container      
docker run  -p 8000:8000  \
    -e GOOGLE_GENAI_USE_VERTEXAI=0 \
    -e GOOGLE_API_KEY="" \
    -e AWS_ACCESS_KEY_ID="" \
    -e AWS_SECRET_ACCESS_KEY="" \
    --name aws-agent-container agents   
docker exec -it aws-agent-container which uvx



