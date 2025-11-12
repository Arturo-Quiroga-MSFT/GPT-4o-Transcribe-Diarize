#!/bin/bash

# Script to compile and run the .NET test for Azure OpenAI diarization

echo "Compiling .NET code..."
dotnet run --project . || csc test.cs

if [ $? -eq 0 ]; then
    echo ""
    echo "Running transcription test..."
    echo ""
    if [ -f "test.exe" ]; then
        mono test.exe
    else
        ./test
    fi
else
    echo "Compilation failed. Please check for errors."
fi
