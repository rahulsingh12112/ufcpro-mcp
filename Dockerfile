FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    flask gunicorn boto3 \
    langchain-mcp-adapters langchain-aws langgraph

COPY mcp_server.py auth.py chat_app.py chat.html ./

EXPOSE 8800

CMD ["gunicorn", "--bind", "0.0.0.0:8800", "--workers", "2", "--timeout", "120", "chat_app:app"]
