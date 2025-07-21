ARG BUILD_FROM
FROM ${BUILD_FROM}

ENV LANG C.UTF-8

# Install Python and pip
RUN apk add --no-cache python3 py3-pip

# Install Flask
RUN pip install Flask==2.3.3

# Copy application files
COPY rootfs/app /app

# Ensure correct permissions for the app directory
RUN chmod -R 755 /app

# Expose the port Flask will run on
EXPOSE 8099

# Set the working directory
WORKDIR /app

# Command to run the application (handled by run.sh)
CMD ["/bin/bash", "/run.sh"]
