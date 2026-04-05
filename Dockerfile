FROM python:3.12-slim

WORKDIR /app

RUN pip install uv

COPY agent/pyproject.toml agent/uv.lock* ./
RUN uv sync --no-dev --frozen

COPY agent/ .

ENV PORT=8080
EXPOSE 8080

CMD ["uv", "run", "python", "main.py"]
