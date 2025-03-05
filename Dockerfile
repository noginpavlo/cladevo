FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Install ClustalW and dependencies
RUN apt-get update && apt-get install -y clustalw && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . /app/

# Set the working directory to where manage.py is located
WORKDIR /app/cladevo

# Create the STATIC_ROOT directory before running collectstatic
RUN mkdir -p /app/cladevo/staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port Django runs on
EXPOSE 8000

# Set the default command to run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
