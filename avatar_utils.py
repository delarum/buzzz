import secrets
import string
from typing import Optional, Literal

# Available DiceBear avatar styles
AVATAR_STYLES = [
    # Popular styles (shown first)
    "adventurer",
    "adventurer-neutral", 
    "avataaars",
    "avataaars-neutral",
    "big-ears",
    "big-ears-neutral",
    "big-smile",
    "bottts",
    "bottts-neutral",
    "croodles",
    "croodles-neutral",
    "dylan",
    "fun-emoji",
    "glass",
    "icons",
    "identicon",
    "initials",
    "lorelei",
    "lorelei-neutral",
    "micah",
    "miniavs",
    "notionists",
    "notionists-neutral",
    "open-peeps",
    "personas",
    "pixel-art",
    "pixel-art-neutral",
    "rings",
    "shapes",
    "thumbs",
]

# Popular styles subset for quick selection
POPULAR_STYLES = [
    "adventurer",
    "avataaars", 
    "big-ears",
    "big-smile",
    "bottts",
    "fun-emoji",
    "lorelei",
    "micah",
    "notionists",
    "open-peeps",
    "personas",
    "pixel-art",
]


def generate_random_seed(length: int = 12) -> str:
    """Generate a random seed string for avatar generation."""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))


def get_avatar_url(
    seed: str,
    style: str = "adventurer",
    size: Optional[int] = None,
    background_color: Optional[str] = None,
    radius: Optional[int] = None,
) -> str:
    """
    Generate a DiceBear avatar URL.
    
    Args:
        seed: Unique identifier (username, user_id, or random string)
        style: DiceBear style name (default: "adventurer")
        size: Avatar size in pixels (optional)
        background_color: Hex color without # (optional, e.g., "b6e3f4")
        radius: Border radius 0-50 (optional)
    
    Returns:
        Full URL to the avatar SVG
    
    Example:
        >>> get_avatar_url("john_doe", "avataaars")
        'https://api.dicebear.com/7.x/avataaars/svg?seed=john_doe'
    """
    if style not in AVATAR_STYLES:
        style = "adventurer"
    
    base_url = f"https://api.dicebear.com/7.x/{style}/svg?seed={seed}"
    
    params = []
    if size:
        params.append(f"size={size}")
    if background_color:
        params.append(f"backgroundColor={background_color}")
    if radius is not None:
        params.append(f"radius={radius}")
    
    if params:
        base_url += "&" + "&".join(params)
    
    return base_url


def get_avatar_url_png(
    seed: str,
    style: str = "adventurer", 
    size: int = 128
) -> str:
    """
    Generate a DiceBear avatar URL in PNG format.
    Useful for contexts where SVG isn't supported.
    """
    if style not in AVATAR_STYLES:
        style = "adventurer"
    
    return f"https://api.dicebear.com/7.x/{style}/png?seed={seed}&size={size}"


def create_avatar_for_user(username: str, style: str = "adventurer") -> dict:
    """
    Create avatar data for a new user.
    
    Returns a dict with all avatar-related fields for database storage.
    """
    seed = generate_random_seed()
    
    return {
        "avatar_seed": seed,
        "avatar_style": style,
        "avatar_url": get_avatar_url(seed, style),
    }


# For backwards compatibility with your existing schema
def get_avatar_data_for_db(seed: str, style: str) -> dict:
    """
    Get avatar data formatted for your existing database schema.
    Maps to avatar_icon, avatar_color, avatar_bg columns.
    """
    return {
        "avatar_icon": style,           # Store the style name
        "avatar_color": seed,           # Store the seed 
        "avatar_bg": get_avatar_url(seed, style),  # Store the full URL
    }