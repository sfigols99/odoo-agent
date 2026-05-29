# Servidor MCP de Odoo (capa externa reutilizable).
# Build:  docker build -t odoo-mcp:1.0 ./odoo_mcp
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY server.py .

EXPOSE 8000
CMD ["python", "server.py"]
