# Test script to simulate the title generation process
import os
import requests
import json

# Simulate the AI response that we're getting
test_case_study = """TechYard x Vostro: Lock it up

TRANSFORMING BUSINESS CHALLENGES INTO SUCCESS WITH INNOVATIVE AI SOLUTIONS: THE TECHYARD STORY.

INTRODUCTION

TechYard, a trailblazer in AI development, faced an intricate challenge with their esteemed client, Vostro. The mission was to create a groundbreaking solution for a complex problem, a task that was as demanding as it was exciting. The project, aptly named "Lock it up," was a testament to TechYard's innovative prowess and commitment to exceeding client expectations."""

print("Original AI response:")
print(test_case_study)
print("\n" + "="*50 + "\n")

# Simulate the post-processing logic
lines = test_case_study.split('\n')
if lines:
    first_line = lines[0].strip()
    print(f"🔍 DEBUG: AI generated first line: '{first_line}'")
    
    # If first line looks like old format, replace it with a generic hook
    if (' x ' in first_line and ':' in first_line) or ('X' in first_line and ':' in first_line):
        print(f"🔍 WARNING: AI generated old format title: '{first_line}'")
        # Replace with a generic hook based on the content
        if 'chatbot' in first_line.lower() or 'ai' in first_line.lower():
            lines[0] = "How AI Transformed Customer Service"
        elif 'automation' in first_line.lower():
            lines[0] = "Automation That Changed Everything"
        elif 'lock' in first_line.lower():
            lines[0] = "The Solution That Locked Success"
        else:
            lines[0] = "A Success Story That Transformed Business"
        test_case_study = '\n'.join(lines)
        print(f"🔍 FIXED: Replaced with: '{lines[0]}'")
    else:
        print(f"🔍 OK: Title looks good: '{first_line}'")

print("\nAfter post-processing:")
print(test_case_study)
print("\n" + "="*50 + "\n")

# Extract title for database
lines = test_case_study.split('\n')
title = lines[0].strip() if lines else "Case Study"
print(f"🔍 FINAL TITLE FOR DATABASE: '{title}'") 