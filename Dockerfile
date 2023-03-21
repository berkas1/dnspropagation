# Use the official Python 3.10 image as the base
FROM python:3.10-slim

# Install the dnspropagation package and its dependencies
RUN pip install --no-cache-dir dnspropagation

# Set the entrypoint to the dnspropagation CLI tool
ENTRYPOINT ["dnspropagation"]

# Set the default command to show help
CMD ["--help"]
