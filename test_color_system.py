#!/usr/bin/env python3
"""
Test script to verify the color assignment system for labels.
This script demonstrates how colors are consistently assigned to labels.
"""

from app.utils.color_utils import ColorUtils

def test_color_consistency():
    """Test that the same label name always gets the same color"""
    print("🎨 Testing Color Assignment System")
    print("=" * 50)
    
    # Test labels
    test_labels = [
        "Startup", "Enterprise", "Digital Transformation", "Success Stories",
        "Healthcare", "Finance", "Education", "Technology", "Consulting",
        "Manufacturing", "Retail", "Real Estate", "Marketing", "Sales",
        "Customer Service", "Product Development", "Research", "Innovation",
        "Sustainability", "Global", "Local", "B2B", "B2C", "SaaS",
        "Mobile App", "Web Platform", "AI/ML", "Blockchain", "Cloud",
        "Cybersecurity"
    ]
    
    print(f"Testing {len(test_labels)} labels...")
    print()
    
    # Test 1: First assignment
    print("📝 First Color Assignment:")
    first_colors = {}
    for label in test_labels[:10]:  # Test first 10
        color = ColorUtils.get_color_for_label(label)
        first_colors[label] = color
        print(f"  {label:25} → {color}")
    
    print()
    
    # Test 2: Consistency check (same labels should get same colors)
    print("🔄 Consistency Check (same labels, same colors):")
    for label in test_labels[:10]:
        color = ColorUtils.get_color_for_label(label)
        expected_color = first_colors[label]
        status = "✅" if color == expected_color else "❌"
        print(f"  {status} {label:25} → {color}")
    
    print()
    
    # Test 3: Show all available colors
    print("🎨 Available Color Palette:")
    all_colors = ColorUtils.get_all_colors()
    print(f"Total colors: {len(all_colors)}")
    print("Colors:", ", ".join(all_colors[:10]) + "...")
    
    print()
    
    # Test 4: Color distribution
    print("📊 Color Distribution Test:")
    color_usage = {}
    for label in test_labels:
        color = ColorUtils.get_color_for_label(label)
        color_usage[color] = color_usage.get(color, 0) + 1
    
    print("Color usage count:")
    for color, count in sorted(color_usage.items()):
        print(f"  {color}: {count} labels")
    
    print()
    print("✅ Color assignment system test completed!")

def test_color_palette_info():
    """Test the color palette information endpoint"""
    print("\n🎨 Testing Color Palette Information")
    print("=" * 50)
    
    palette_info = ColorUtils.get_color_palette_info()
    print(f"Total colors: {palette_info['total_colors']}")
    print(f"Description: {palette_info['description']}")
    print(f"First 5 colors: {palette_info['colors'][:5]}")
    print(f"Last 5 colors: {palette_info['colors'][-5:]}")

if __name__ == "__main__":
    try:
        test_color_consistency()
        test_color_palette_info()
    except Exception as e:
        print(f"❌ Error testing color system: {e}")
        import traceback
        traceback.print_exc() 