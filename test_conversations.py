#!/usr/bin/env python3
"""
Test script for the Local AI Assistant.
Runs 20 different conversation starters to ensure everything works without errors.
"""

import os
import time
import subprocess
import tempfile
import signal
import random
from pathlib import Path

# Create a temporary file for testing document loading
with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp:
    temp.write("""
# Test Document

This is a test document for the Local AI Assistant.

## Important Information

- The test document contains key information about testing.
- The unique identifier in this document is: TEST123
- This document was created for testing purposes.

## Technical Details

The Local AI Assistant should be able to find information in this document when asked.
    """)
    temp_file_path = temp.name

# List of commands to test
commands = [
    "/help",
    "/thinking on",
    "/thinking off",
    "/debug on",
    "/debug off",
    "/models",
    "/docs",
    f"/load {temp_file_path}",
    "/memory",
    "/status",
    "/clear",
]

# List of 20 conversation starters
conversation_starters = [
    "Hello, how are you today?",
    "What's your name?",
    "What can you do?",
    "Tell me a short joke.",
    "What's the meaning of life?",
    "What day is it today?",
    "What's the capital of France?",
    "How do I make pancakes?",
    "Who invented the internet?",
    "What is machine learning?",
    "Can you summarize the concept of relativity?",
    "How tall is Mount Everest?",
    "What's the difference between a virus and bacteria?",
    "What is the test document about?",
    "What is the unique identifier in the test document?",
    "Tell me three facts about the test document.",
    "What is artificial intelligence?",
    "How does the Local AI Assistant work?",
    "What's your favorite book?",
    "Goodbye!"
]

# Function to run a command and return output
def run_command(command, timeout=30):
    try:
        # Use pexpect or similar for interactive session
        process = subprocess.Popen(
            ["python3", "main.py"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Wait for startup
        time.sleep(3)
        
        # Send command
        process.stdin.write(command + "\n")
        process.stdin.flush()
        
        # Wait for response
        time.sleep(5)
        
        # Send quit command to exit
        process.stdin.write("/quit\n")
        process.stdin.flush()
        
        # Wait for process to complete
        process.wait(timeout=timeout)
        
        # Get output
        stdout, stderr = process.communicate()
        
        return stdout, stderr, process.returncode
        
    except subprocess.TimeoutExpired:
        process.kill()
        return "", "Timeout expired", 1

# Main test function
def run_tests():
    print("Starting Local AI Assistant tests...")
    print(f"Using temporary test file: {temp_file_path}")
    
    # Test commands
    print("\n=== Testing Commands ===")
    for command in commands:
        print(f"Testing command: {command}")
        stdout, stderr, returncode = run_command(command)
        print(f"Return code: {returncode}")
        if returncode != 0:
            print(f"Error: {stderr}")
    
    # Test conversation starters
    print("\n=== Testing Conversation Starters ===")
    
    # First, enable thinking mode
    run_command("/thinking on")
    
    # Test first half of conversation starters with thinking mode ON
    for i, starter in enumerate(conversation_starters[:10]):
        print(f"Testing conversation starter {i+1}/20: '{starter}'")
        stdout, stderr, returncode = run_command(starter)
        print(f"Return code: {returncode}")
        if returncode != 0:
            print(f"Error: {stderr}")
    
    # Turn off thinking mode
    run_command("/thinking off")
    
    # Test second half of conversation starters with thinking mode OFF
    for i, starter in enumerate(conversation_starters[10:]):
        print(f"Testing conversation starter {i+11}/20: '{starter}'")
        stdout, stderr, returncode = run_command(starter)
        print(f"Return code: {returncode}")
        if returncode != 0:
            print(f"Error: {stderr}")
    
    # Clean up temporary file
    try:
        os.unlink(temp_file_path)
        print(f"\nTemporary file {temp_file_path} removed.")
    except:
        print(f"\nFailed to remove temporary file {temp_file_path}")
    
    print("\nTesting completed!")

if __name__ == "__main__":
    run_tests() 