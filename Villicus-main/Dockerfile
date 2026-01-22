FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy repository
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set working dir to the website folder
WORKDIR "/app/Villicus Website"

# Expose the port used by uvicorn
EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
