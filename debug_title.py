# Debug script to test title processing
import re

def test_title_processing():
    # Test cases
    test_cases = [
        "TechYard x Vostro: Lock it up",
        "Securex x Ford: AI chatbots", 
        "Lenovo x Jabra: HST (High Definition System Technology)",
        "How AI Transformed Customer Service",
        "The Chatbot That Changed Everything"
    ]
    
    for test_title in test_cases:
        print(f"\nTesting: '{test_title}'")
        
        # Check if it looks like old format
        is_old_format = (' x ' in test_title and ':' in test_title) or ('X' in test_title and ':' in test_title)
        print(f"  Is old format: {is_old_format}")
        
        if is_old_format:
            # Replace with appropriate hook
            if 'chatbot' in test_title.lower() or 'ai' in test_title.lower():
                new_title = "How AI Transformed Customer Service"
            elif 'automation' in test_title.lower():
                new_title = "Automation That Changed Everything"
            elif 'lock' in test_title.lower():
                new_title = "The Solution That Locked Success"
            elif 'hst' in test_title.lower():
                new_title = "The Technology That Transformed Everything"
            else:
                new_title = "A Success Story That Transformed Business"
            print(f"  Would replace with: '{new_title}'")
        else:
            print(f"  Title looks good: '{test_title}'")

if __name__ == "__main__":
    test_title_processing() 