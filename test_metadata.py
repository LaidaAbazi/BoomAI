#!/usr/bin/env python3
"""
Test script for the metadata service functionality
"""

import os
import sys
import json

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.services.metadata_service import MetadataService

def test_metadata_service():
    """Test the metadata service with sample data"""
    
    # Initialize the metadata service
    metadata_service = MetadataService()
    
    # Sample case study text
    sample_case_study = """
    ACME CORP x TECHSTART: DIGITAL TRANSFORMATION SUCCESS

    HERO STATEMENT
    ACME Corp achieved 40% efficiency improvement through innovative digital transformation.

    INTRODUCTION
    ACME Corp, a leading manufacturing company, faced significant challenges with their legacy systems. Their manual processes were time-consuming and error-prone, leading to delays and customer dissatisfaction.

    RESEARCH AND DEVELOPMENT
    Our team conducted extensive research into ACME Corp's existing workflows and identified key bottlenecks in their production and inventory management systems.

    CLIENT CONTEXT AND CHALLENGES
    ACME Corp was struggling with:
    - Manual inventory tracking causing stockouts
    - Paper-based processes slowing down operations
    - Lack of real-time data visibility
    - Customer complaints about delivery delays

    THE SOLUTION
    We implemented a comprehensive digital transformation solution including:
    - Automated inventory management system
    - Cloud-based workflow automation
    - Real-time dashboard for management
    - Mobile app for field workers

    IMPLEMENTATION & COLLABORATION
    The implementation took 6 months with close collaboration between our teams. We worked side-by-side with ACME Corp's IT department to ensure smooth integration with existing systems.

    RESULTS & IMPACT
    - 40% improvement in operational efficiency
    - 60% reduction in inventory errors
    - 25% faster order processing
    - 95% customer satisfaction rate

    CUSTOMER/CLIENT REFLECTION
    "The transformation exceeded our expectations. We're now more efficient than ever before."

    TESTIMONIAL/PROVIDER REFLECTION
    "Working with ACME Corp was a fantastic experience. Their commitment to change made this project a huge success."

    CALL TO ACTION
    Ready to transform your business? Contact us today for a consultation.

    QUOTES HIGHLIGHTS
    - **Client:** "The new system has revolutionized how we work."
    - **Provider:** "This project showcases the power of digital transformation."
    - **Client:** "We've seen measurable improvements across all departments."
    """

    # Sample client summary
    sample_client_summary = """
    We were initially skeptical about the digital transformation project, but the results have been outstanding. 
    The new system has made our operations much more efficient. We've seen a 40% improvement in productivity 
    and our customer satisfaction has increased significantly. The team was professional and responsive throughout 
    the entire process. We're very happy with the outcome and would definitely recommend their services.
    """

    print("🧪 Testing Metadata Service...")
    print("=" * 50)

    # Test 1: Extract and remove metadata sections
    print("\n1. Testing extract_and_remove_metadata_sections...")
    try:
        main_story, metadata = metadata_service.extract_and_remove_metadata_sections(
            sample_case_study, sample_client_summary
        )
        print("✅ Successfully extracted metadata sections")
        print(f"   Main story length: {len(main_story)} characters")
        print(f"   Metadata keys: {list(metadata.keys())}")
        print(f"   Quote highlights: {len(metadata.get('quote_highlights', ''))} characters")
        print(f"   Corrected conflicts: {len(metadata.get('corrected_conflicts', ''))} characters")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # Test 2: Analyze sentiment
    print("\n2. Testing sentiment analysis...")
    try:
        sentiment = metadata_service.analyze_sentiment(sample_client_summary)
        print("✅ Successfully analyzed sentiment")
        print(f"   Overall sentiment: {sentiment['overall_sentiment']['sentiment']}")
        print(f"   Confidence: {sentiment['overall_sentiment']['confidence']:.2f}")
        print(f"   Score: {sentiment['overall_sentiment']['score']:.2f}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # Test 3: Extract client satisfaction
    print("\n3. Testing client satisfaction analysis...")
    try:
        satisfaction = metadata_service.extract_client_satisfaction(sample_client_summary)
        print("✅ Successfully analyzed client satisfaction")
        print(f"   Category: {satisfaction['category']}")
        print(f"   Statement: {satisfaction['statement'][:100]}...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # Test 4: Extract client takeaways
    print("\n4. Testing client takeaways extraction...")
    try:
        takeaways = metadata_service.extract_client_takeaways(sample_client_summary)
        print("✅ Successfully extracted client takeaways")
        print(f"   Takeaways length: {len(takeaways)} characters")
        print(f"   Preview: {takeaways[:100]}...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # Test 5: Extract quotes
    print("\n5. Testing quote extraction...")
    try:
        quotes = metadata_service.extract_quotes_from_text(sample_case_study)
        print("✅ Successfully extracted quotes")
        print(f"   Number of quotes found: {len(quotes)}")
        for i, quote in enumerate(quotes[:3], 1):
            print(f"   Quote {i}: {quote['text'][:50]}...")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    # Test 6: Generate metadata summary
    print("\n6. Testing metadata summary generation...")
    try:
        metadata_summary = metadata_service.generate_metadata_summary(
            sample_case_study, sample_client_summary
        )
        print("✅ Successfully generated metadata summary")
        print(f"   Metadata keys: {list(metadata_summary.keys())}")
        print(f"   Analysis timestamp: {metadata_summary.get('analysis_timestamp', 'N/A')}")
        print(f"   Text metrics: {metadata_summary.get('text_metrics', {})}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

    print("\n" + "=" * 50)
    print("🎉 Metadata service testing completed!")

if __name__ == "__main__":
    test_metadata_service() 