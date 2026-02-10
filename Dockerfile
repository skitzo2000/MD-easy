FROM python:3.12-slim

WORKDIR /app

ENV DOC_ROOT=/docs
ENV PORT=8765
ENV THEME=default

RUN mkdir -p /docs

COPY src/ .
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8765

# Serve .md from /docs; mount your project docs at runtime
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8765"]
