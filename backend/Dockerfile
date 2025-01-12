FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim
WORKDIR /app
COPY requirements.txt .
RUN uv pip install -r requirements.txt --system
COPY . .
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 5000
CMD ["uv", "run", "python", "app.py"]
