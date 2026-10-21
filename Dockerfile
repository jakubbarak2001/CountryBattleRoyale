# Use an official lightweight Python image
FROM python:3.14

# Set the working directory
WORKDIR /app

# Copy project files into the container
COPY . /app

# Install dependencies
RUN pip install -r requirements.txt  

# Expose port 5000 for Flask
EXPOSE 5000  

# Container runs use production settings, even when a local .env enables debug.
ENV FLASK_DEBUG=0

# Command to run the app
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "backend.app:app"]
