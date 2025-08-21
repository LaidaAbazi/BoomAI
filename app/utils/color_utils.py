import hashlib
from typing import List

class ColorUtils:
    """Utility class for consistent color assignment to labels"""
    
    # Pastel rainbow palette with 30 colors (ordered red → orange → yellow → green → blue → indigo → violet)
    PASTEL_COLORS = [
        # Row 1 (Pastel Reds/Oranges)
        "#FAD0D0", "#F7B7B7", "#F9C3B9", "#FAD1C2", "#FCD6B5",
        # Row 2 (Pastel Oranges/Yellows)
        "#FDE0B2", "#FEE9B8", "#FFF1C1", "#FFF5CC", "#FFF7D6",
        # Row 3 (Pastel Yellows/Greens)
        "#FFF9E0", "#FFFBEA", "#EAF8CF", "#DFF5D2", "#D2F0DA",
        # Row 4 (Pastel Greens/Blues)
        "#C8EEDD", "#CDEDEA", "#CBEFF2", "#CFEAF7", "#D4EEFF",
        # Row 5 (Pastel Blues/Indigos)
        "#DAF0FF", "#E0F2FF", "#DAD9FF", "#D7D1FF", "#D9C9FF",
        # Row 6 (Pastel Indigos/Violets)
        "#E0CCFF", "#E8C7FF", "#F0C8F9", "#F6C7EE", "#FAD0F0"
    ]
    
    @classmethod
    def get_color_for_label(cls, label_name: str) -> str:
        """
        Get a consistent color for a label based on its name.
        Uses hash of the name to ensure the same label always gets the same color.
        
        Args:
            label_name (str): The name of the label
            
        Returns:
            str: HEX color code
        """
        # Create a hash of the label name
        hash_object = hashlib.md5(label_name.lower().encode())
        hash_hex = hash_object.hexdigest()
        
        # Convert hash to an integer and use modulo to get index
        hash_int = int(hash_hex[:8], 16)
        color_index = hash_int % len(cls.PASTEL_COLORS)
        
        return cls.PASTEL_COLORS[color_index]
    
    @classmethod
    def get_all_colors(cls) -> List[str]:
        """
        Get all available colors in the palette.
        
        Returns:
            List[str]: List of all HEX color codes
        """
        return cls.PASTEL_COLORS.copy()
    
    @classmethod
    def get_color_palette_info(cls) -> dict:
        """
        Get information about the color palette.
        
        Returns:
            dict: Information about the color palette
        """
        return {
            "total_colors": len(cls.PASTEL_COLORS),
            "description": "Pastel Rainbow Palette - Ordered red → orange → yellow → green → blue → indigo → violet",
            "colors": cls.PASTEL_COLORS
        } 