#!/bin/bash

# Create directories required by the Local AI Assistant
echo "Creating required directories..."
mkdir -p data/memory data/documents logs tmp

# Set permissions
echo "Setting permissions..."
chmod -R 755 data logs tmp

echo "Setup complete. The following directories have been created:"
echo "- data/memory: For storing conversation memory"
echo "- data/documents: For storing document data"
echo "- logs: For application logs"
echo "- tmp: For temporary files"

echo "You can now run the assistant with:"
echo "./run_assistant.sh" 