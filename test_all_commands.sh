#!/bin/bash

# Test script for Local AI Assistant command line options
# This script tests all command line options to ensure they work correctly

echo -e "\n=== Testing Local AI Assistant Command Line Options ===\n"

# Function to run a test
run_test() {
    TEST_NUM=$1
    TEST_NAME=$2
    COMMANDS=$3
    
    echo -e "\n--- Test $TEST_NUM: $TEST_NAME ---\n"
    OUTPUT=$(echo -e "$COMMANDS\n/quit" | python3 main.py)
    
    # Check if there's an error in the output
    if echo "$OUTPUT" | grep -i "error" | grep -v "Test error handling"; then
        echo "❌ Error detected in output"
        echo -e "\nError details:"
        echo "$OUTPUT" | grep -i "error" -A 3 -B 1
    else
        echo "✅ No errors detected"
    fi
    
    echo -e "\nOutput preview:"
    echo "$OUTPUT" | tail -10 | head -5
    echo -e "\n"
}

# Test /help command
run_test 1 "Help Command" "/help"

# Test /models command
run_test 2 "Models Command" "/models"

# Test /docs command
run_test 3 "Docs Command" "/docs"

# Test /memory command
run_test 4 "Memory Command" "/memory"

# Test /status command
run_test 5 "Status Command" "/status"

# Test /thinking command
run_test 6 "Thinking Command" "/thinking on\n/thinking off"

# Test /debug command
run_test 7 "Debug Command" "/debug off\n/debug on"

# Test /use command
run_test 8 "Use Model Command" "/use gemma3:27b"

# Test /load command with test document
run_test 9 "Load Document Command" "/load test_document.rtf"

# Test /clear command
run_test 10 "Clear Command" "/clear"

# Test a question that requires model knowledge
run_test 11 "Question with Model Knowledge" "What is Python programming language?"

# Test a question that may find context in memory
run_test 12 "Question with Memory Context" "What did we just talk about?"

echo -e "\n=== All command tests completed ===\n" 