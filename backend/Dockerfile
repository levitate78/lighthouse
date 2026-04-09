FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pdm

COPY pyproject.toml .
RUN pdm install --prod --no-editable

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]