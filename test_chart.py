#!/usr/bin/env python3
"""
Test script to verify matplotlib chart generation
"""

import os
import sys
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend
import matplotlib.pyplot as plt
import uuid

def test_chart_generation():
    """Test basic matplotlib chart generation"""
    
    print("🧪 Testing Chart Generation...")
    print("=" * 50)
    
    try:
        # Test 1: Basic chart creation
        print("\n1. Testing basic chart creation...")
        fig, ax = plt.subplots(figsize=(4, 1.5))
        ax.barh(['Test'], [5], color='green')
        ax.set_xlim(0, 10)
        ax.set_xlabel('Score (0-10)')
        ax.set_title('Test Chart')
        plt.tight_layout()
        
        print("✅ Chart created successfully")
        
        # Test 2: Save chart to file
        print("\n2. Testing chart saving...")
        os.makedirs("generated_pdfs", exist_ok=True)
        filename = f"test_chart_{uuid.uuid4().hex}.png"
        filepath = os.path.join("generated_pdfs", filename)
        
        plt.savefig(filepath)
        plt.close(fig)
        
        print(f"✅ Chart saved to: {filepath}")
        
        # Test 3: Check if file exists
        if os.path.exists(filepath):
            print(f"✅ File exists and size: {os.path.getsize(filepath)} bytes")
        else:
            print("❌ File does not exist")
            
        # Test 4: Test with sentiment score
        print("\n3. Testing sentiment chart generation...")
        sentiment_score = 6.0
        fig, ax = plt.subplots(figsize=(4, 1.5))
        color = 'green' if sentiment_score > 6 else 'yellow' if sentiment_score > 4 else 'red'
        ax.barh(['Sentiment'], [sentiment_score], color=color)
        ax.set_xlim(0, 10)
        ax.set_xlabel('Score (0-10)')
        ax.set_title('Sentiment Score')
        plt.tight_layout()
        
        filename = f"sentiment_test_{uuid.uuid4().hex}.png"
        filepath = os.path.join("generated_pdfs", filename)
        
        plt.savefig(filepath)
        plt.close(fig)
        
        print(f"✅ Sentiment chart saved to: {filepath}")
        if os.path.exists(filepath):
            print(f"✅ Sentiment chart file exists and size: {os.path.getsize(filepath)} bytes")
        else:
            print("❌ Sentiment chart file does not exist")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chart_generation() 