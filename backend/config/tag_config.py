"""
Tag configuration module for the photo portfolio application.
This module centralizes the tag vocabulary used by CLIP for image tagging.
"""

# Candidate tags for CLIP image tagging
CANDIDATE_TAGS = [
    # Locations
    "Florence", "City", "Urban", "Rural", 
    
    # Landscapes
    "Landscape", "Mountains", "River", "Lake", "Sunset", "Sunrise", 
    "Forest", "Desert", "Beach", "Ocean", "Sky", "Clouds",
    
    # Subjects
    "Wildlife", "Nature", "Animals", "People", "Portrait", "Crowd",
    
    # Activities
    "Travel", "Sports", "Hiking", "Swimming",
    
    # Styles
    "Photography", "Architecture", "Art", "Street", "Night", "Macro",
    "Historical", "Modern", "Abstract", "Minimal", "Colorful", "Black and white"
]

# Default number of top tags to return
DEFAULT_TOP_K = 5
