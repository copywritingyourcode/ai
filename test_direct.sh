#!/bin/bash
# Direct test script for Local AI Assistant
# This sends multiple commands to the AI in a single session

# Create a test document
echo "Creating test document..."
cat > test_document.txt << EOF
# Test Document

This is a test document for the Local AI Assistant.

## Important Information

- The test document contains key information about testing.
- The unique identifier in this document is: TEST123
- This document was created for testing purposes.

## Technical Details

The Local AI Assistant should be able to find information in this document when asked.
EOF

# Create a file with all the commands
echo "Creating command file..."
cat > test_commands.txt << EOF
/help
/thinking on
Hello, how are you today?
What can you do?
Tell me a short joke.
/load test_document.txt
What is the unique identifier in the test document?
What is the test document about?
/thinking off
/status
/debug on
What's the capital of France?
How do I make pancakes?
Who invented the internet?
What is machine learning?
/models
/docs
/debug off
What's the meaning of life?
What day is it today?
/memory
How does the Local AI Assistant work?
What's your favorite book?
Goodbye!
/quit
EOF

# Run the AI assistant with the commands
echo "Running test commands through Local AI Assistant..."
cat test_commands.txt | python3 main.py | tee test_output.log

echo "Test completed. Check test_output.log for detailed output." 