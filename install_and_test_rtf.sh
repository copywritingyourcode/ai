#!/bin/bash

# Install the striprtf package
echo "Installing striprtf package..."
pip install striprtf>=0.0.24

# Create a test RTF file
echo "Creating a test RTF file..."
cat > test_document.rtf << 'EOF'
{\rtf1\ansi\ansicpg1252\cocoartf2709
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 This is a test RTF document for the Local AI Assistant.\
\
**RTF_TEST_DOCUMENT**\
\
This document is used to test the RTF loading functionality.\
}
EOF

# Run the assistant and test RTF loading
echo "Testing RTF loading..."
echo -e "/load test_document.rtf\n/docs\n/quit" | python3 main.py

echo "Test completed." 