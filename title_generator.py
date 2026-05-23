"""
Title Generator Module

Generates SEO-optimized English product titles and descriptions from
product folder names. Extracts key attributes from folder names and
combines them with trending keywords for SHEIN listings.
"""

import logging
import random
import re
from typing import Dict, List

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Trending keywords by category
TRENDING_KEYWORDS: Dict[str, List[str]] = {
    "3001": [
        "casual", "streetwear", "graphic tee", "summer", "unisex",
        "comfortable", "breathable", "cotton", "oversized", "trendy",
        "fashion", "daily wear", "soft fabric", "crew neck", "short sleeve",
        "loose fit", "vintage", "aesthetic", "printed", "hip hop",
        "Y2K style", "minimalist", "urban", "everyday essential",
        "gift idea", "funny", "unique design", "statement piece",
        "lightweight", "cool", "classic fit", "wardrobe staple",
    ],
    "8008": [
        "hoodie", "pullover", "warm", "cozy", "winter", "autumn",
        "fleece lined", "streetwear", "oversized", "casual", "unisex",
        "kangaroo pocket", "drawstring hood", "thick", "comfortable",
        "layering", "sporty", "hip hop", "urban style", "soft interior",
        "daily wear", "relaxed fit", "graphic print", "trendy",
        "cold weather", "loungewear", "athleisure", "fashion forward",
    ],
    "ady000": [
        "sweatshirt", "crewneck", "pullover", "warm", "cozy", "casual",
        "fleece", "autumn", "winter", "oversized", "unisex", "comfortable",
        "soft", "relaxed fit", "layering piece", "basic", "essential",
        "streetwear", "minimalist", "daily wear", "cotton blend",
        "graphic print", "trendy", "loungewear", "sporty casual",
        "versatile", "wardrobe essential", "fashion", "aesthetic",
    ],
}

# General keywords applicable to all categories
GENERAL_KEYWORDS: List[str] = [
    "SHEIN", "new arrival", "best seller", "hot sale", "popular",
    "high quality", "affordable", "plus size available", "all seasons",
    "gift for him", "gift for her", "matching outfit", "couple wear",
    "family matching", "party wear", "holiday", "festival",
    "back to school", "work from home", "weekend casual",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _parse_folder_name(folder_name: str) -> Dict[str, str]:
    """
    Parse a product folder name to extract key attributes.

    Example folder name: 'Black Dad Dope Black Father Fathers Day T-Shirt _ SHEIN USA'

    Args:
        folder_name: The product subfolder name.

    Returns:
        Dict with extracted attributes: theme, occasion, style, color, product_type.
    """
    # Remove the SHEIN suffix if present
    cleaned = re.sub(r'\s*[_|]\s*SHEIN\s*(USA|UK|EUR|CA)?\s*$', '', folder_name, flags=re.IGNORECASE)
    cleaned = cleaned.strip()

    attributes: Dict[str, str] = {
        "raw_name": cleaned,
        "theme": "",
        "occasion": "",
        "style": "",
        "color": "",
        "product_type": "",
    }

    # Extract color
    color_patterns = ["black", "white", "red", "blue", "green", "pink",
                      "purple", "yellow", "orange", "gray", "grey", "navy"]
    for color in color_patterns:
        if color.lower() in cleaned.lower():
            attributes["color"] = color.capitalize()
            break

    # Extract occasion
    occasion_patterns = ["fathers day", "mothers day", "christmas", "halloween",
                         "birthday", "valentine", "easter", "thanksgiving",
                         "new year", "graduation", "wedding", "anniversary"]
    for occasion in occasion_patterns:
        if occasion.lower() in cleaned.lower():
            attributes["occasion"] = occasion.title()
            break

    # Extract product type
    type_patterns = ["t-shirt", "tee", "hoodie", "sweatshirt", "pullover",
                     "crewneck", "tank top", "long sleeve"]
    for ptype in type_patterns:
        if ptype.lower() in cleaned.lower():
            attributes["product_type"] = ptype.title()
            break

    # The rest is the theme/style
    attributes["theme"] = cleaned

    return attributes


def generate_title(folder_name: str, category_code: str) -> str:
    """
    Generate an SEO-optimized English product title (~150 words) from
    a folder name and category code.

    Args:
        folder_name: The product subfolder name containing product info.
        category_code: The category code (e.g. '3001', '8008').

    Returns:
        A string containing the SEO title of approximately 150 words.
    """
    attributes = _parse_folder_name(folder_name)

    # Get category-specific keywords
    category_keywords = TRENDING_KEYWORDS.get(category_code, TRENDING_KEYWORDS["3001"]).copy()
    general_kws = GENERAL_KEYWORDS.copy()

    # Shuffle for variety
    random.shuffle(category_keywords)
    random.shuffle(general_kws)

    # Build the title from components
    parts: List[str] = []

    # Start with the product name/theme
    parts.append(attributes["raw_name"])

    # Add category-specific descriptors
    if attributes["product_type"]:
        parts.append(f"- {attributes['product_type']}")

    # Add occasion if found
    if attributes["occasion"]:
        parts.append(f"Perfect for {attributes['occasion']}")
        parts.append(f"Great {attributes['occasion']} Gift Idea")

    # Add color descriptor
    if attributes["color"]:
        parts.append(f"{attributes['color']} Color Design")

    # Add trending keyword phrases
    keyword_phrases = [
        f"Trendy {category_keywords[0]} style for men and women",
        f"Features {category_keywords[1]} design with {category_keywords[2]} appeal",
        f"Perfect for {category_keywords[3]} and {category_keywords[4]} occasions",
        f"Made with {category_keywords[5]} materials for ultimate comfort",
        f"This {category_keywords[6]} piece combines {category_keywords[7]} aesthetics",
        f"Ideal for {category_keywords[8]} looks and {category_keywords[9]} vibes",
        f"A must-have {category_keywords[10]} item for your wardrobe",
        f"Suitable for {category_keywords[11]} and everyday styling",
        f"Embrace the {category_keywords[12]} trend with this unique piece",
        f"High quality {category_keywords[13]} garment with attention to detail",
    ]
    parts.extend(keyword_phrases)

    # Add general keywords
    general_phrases = [
        f"{general_kws[0]} exclusive collection",
        f"Shop {general_kws[1]} items at unbeatable prices",
        f"This {general_kws[2]} item is flying off the shelves",
        f"Rated as {general_kws[3]} by thousands of happy customers",
        f"{general_kws[4]} craftsmanship and {general_kws[5]} pricing",
        f"Available in {general_kws[6]} options for everyone",
        f"Perfect across {general_kws[7]} with versatile styling options",
        f"Makes an excellent {general_kws[8]} or {general_kws[9]} present",
    ]
    parts.extend(general_phrases)

    # Join all parts
    title = " ".join(parts)

    # Ensure approximately 150 words - trim or pad
    words = title.split()
    if len(words) > 160:
        words = words[:155]
        title = " ".join(words)
    elif len(words) < 140:
        # Pad with more keywords
        extra_keywords = category_keywords + general_kws
        idx = 0
        while len(words) < 150 and idx < len(extra_keywords):
            words.append(extra_keywords[idx])
            idx += 1
        title = " ".join(words)

    logger.info(f"生成标题: 共 {len(title.split())} 个单词")
    return title


def generate_description(folder_name: str, category_code: str) -> str:
    """
    Generate an SEO-optimized English product description from a folder
    name and category code.

    Args:
        folder_name: The product subfolder name containing product info.
        category_code: The category code (e.g. '3001', '8008').

    Returns:
        A string containing the product description.
    """
    attributes = _parse_folder_name(folder_name)
    category_keywords = TRENDING_KEYWORDS.get(category_code, TRENDING_KEYWORDS["3001"]).copy()
    random.shuffle(category_keywords)

    description_parts: List[str] = [
        f"Discover this amazing {attributes['raw_name']}.",
        f"This {category_keywords[0]} piece features a stunning design that combines "
        f"{category_keywords[1]} style with {category_keywords[2]} comfort.",
    ]

    if attributes["occasion"]:
        description_parts.append(
            f"Perfect gift for {attributes['occasion']}. "
            f"Show your appreciation with this thoughtful and stylish present."
        )

    if attributes["color"]:
        description_parts.append(
            f"The {attributes['color'].lower()} colorway adds a classic touch "
            f"that pairs well with any outfit."
        )

    description_parts.extend([
        f"Made with premium {category_keywords[3]} materials for a {category_keywords[4]} feel. "
        f"The {category_keywords[5]} construction ensures long-lasting durability.",
        f"Whether you are going for a {category_keywords[6]} look or keeping it "
        f"{category_keywords[7]}, this piece has you covered.",
        f"Available in sizes S through XXXL to fit all body types comfortably.",
        "Order now and elevate your wardrobe with this must-have item!",
    ])

    description = " ".join(description_parts)
    logger.info(f"生成描述: 共 {len(description.split())} 个单词")
    return description


if __name__ == "__main__":
    # Demo usage
    test_folder = "Black Dad Dope Black Father Fathers Day T-Shirt _ SHEIN USA"
    title = generate_title(test_folder, "3001")
    print(f"Title ({len(title.split())} words):")
    print(title)
    print()
    desc = generate_description(test_folder, "3001")
    print(f"Description ({len(desc.split())} words):")
    print(desc)
