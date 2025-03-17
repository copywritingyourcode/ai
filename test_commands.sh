#!/bin/bash
# Test script to interact with the Local AI Assistant

# Send commands to the assistant
echo "Testing status command"
echo "/status" | python3 main.py

echo "Testing help command"
echo "/help" | python3 main.py

echo "Testing document loading"
echo "/load sample_document.txt" | python3 main.py

echo "Testing list documents"
echo "/docs" | python3 main.py

echo "Testing model switching"
echo "/model mistral:7b" | python3 main.py

echo "Testing thinking mode toggle"
echo "/thinking on" | python3 main.py

echo "Testing simple chat interaction"
echo "Tell me about the Local AI Assistant" | python3 main.py 