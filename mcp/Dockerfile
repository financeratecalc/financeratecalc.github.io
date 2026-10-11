# FinanceRateCalc MCP server (stdio). Build from the repository root:
#   docker build -f mcp/Dockerfile -t frc-mcp .
#   docker run -i frc-mcp
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir mcp
COPY mcp/frc_mcp.py mcp/frc_data.json mcp/claims.json ./
CMD ["python", "frc_mcp.py"]
