#!/bin/bash

# Test script for the Local AI Assistant
# Tests several questions to ensure the assistant responds properly

echo -e "\n=== Testing Local AI Assistant Responses ===\n"

# Function to run a test
run_test() {
    TEST_NUM=$1
    QUESTION=$2
    EXPECTED_RESULT=$3
    
    echo -e "\n--- Test $TEST_NUM: $QUESTION ---\n"
    RESPONSE=$(echo -e "$QUESTION\n/quit" | python3 main.py)
    
    # Check if the response contains the expected text
    if echo "$RESPONSE" | grep -q "AI:"; then
        echo "✅ Got a response from the AI"
    else
        echo "❌ No AI response found"
    fi
    
    echo -e "\nResponse preview:"
    echo "$RESPONSE" | grep -A 2 "AI:" | head -3
    echo -e "\n"
}

# Basic test cases
run_test 1 "What is the meaning of life?" "None"
run_test 2 "Tell me about AI" "None"
run_test 3 "How does the vector store work?" "None"
run_test 4 "What is your model?" "None"
run_test 5 "Can you help me with programming?" "None"
run_test 6 "Explain quantum computing" "None"
run_test 7 "What is the weather like today?" "None"
run_test 8 "How do embeddings work?" "None"
run_test 9 "Tell me a joke" "None"
run_test 10 "Can you summarize a document for me?" "None"

echo -e "\n=== Testing commands ===\n"

# Test commands
echo -e "/help\n/quit" | python3 main.py
echo -e "/thinking on\n/quit" | python3 main.py
echo -e "/models\n/quit" | python3 main.py

echo -e "\n=== All tests completed ===\n" 