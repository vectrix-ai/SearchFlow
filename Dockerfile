# Use an official Python runtime as the base image
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Set the working directory in the container
WORKDIR /app

# Install the required packages
RUN pip install --no-cache-dir vectrix

# Copy the project files into the container
COPY src/ ./src/

# Set the environment variable for Streamlit to run in headless mode
ENV STREAMLIT_SERVER_HEADLESS=true

# Expose the port Streamlit runs on
EXPOSE 8501

# Set the command to run the Streamlit app
CMD ["streamlit", "run", "src/streamlit_app/main.py"]