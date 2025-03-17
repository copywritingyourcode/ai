#!/bin/bash
# Individual test script for Local AI Assistant
# Tests each command individually to better identify issues

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

# Commands to test
declare -a commands=(
    "/help"
    "/thinking on" 
    "/thinking off"
    "/debug on"
    "/debug off"
    "/models"
    "/docs"
    "/load test_document.txt"
    "/status"
    "/memory"
)

# Queries to test
declare -a queries=(
    "Hello, how are you today?"
    "What can you do?"
    "Tell me a short joke."
    "What's the meaning of life?"
    "What is the unique identifier in the test document?"
    "What is the test document about?"
    "What's the capital of France?"
    "How does the Local AI Assistant work?"
    "What day is it today?"
    "Goodbye!"
)

# Test commands
echo "Testing commands..."
for cmd in "${commands[@]}"; do
    echo "Testing: $cmd"
    echo "$cmd" | python3 main.py > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "  ✓ Success"
    else
        echo "  ✗ Failed"
    fi
done

# Test queries with thinking mode off
echo "Testing queries with thinking mode off..."
echo "/thinking off" | python3 main.py > /dev/null 2>&1
for query in "${queries[@]:0:5}"; do
    echo "Testing: $query"
    echo "$query" | python3 main.py > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "  ✓ Success"
    else
        echo "  ✗ Failed"
    fi
done

# Test queries with thinking mode on
echo "Testing queries with thinking mode on..."
echo "/thinking on" | python3 main.py > /dev/null 2>&1
for query in "${queries[@]:5:5}"; do
    echo "Testing: $query"
    echo "$query" | python3 main.py > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "  ✓ Success"
    else
        echo "  ✗ Failed"
    fi
done

# Test document-related queries
echo "Testing document-related queries..."
(echo "/load test_document.txt"; echo "What is the unique identifier in the test document?") | python3 main.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "  ✓ Document query success"
else
    echo "  ✗ Document query failed"
fi

echo "All tests completed." 