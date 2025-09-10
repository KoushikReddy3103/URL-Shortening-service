# Use Python base image
FROM python:3.10-slim

# Set working directory
WORKDIR /root/url-shortener

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app files
COPY . .

# Expose Flask port
EXPOSE 5000

# Run app
CMD ["python", "app/app.py"]

