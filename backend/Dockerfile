FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pdm

COPY pyproject.toml .
RUN pdm install --prod --no-editable

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]

