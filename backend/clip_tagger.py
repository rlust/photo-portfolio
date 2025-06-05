import open_clip
import torch
from PIL import Image
from typing import List, Tuple

# Load model and preprocessing pipeline once at module level for efficiency
MODEL_NAME = "ViT-B-32"
PRETRAINED = "openai"
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess, tokenizer = open_clip.create_model_and_transforms(MODEL_NAME, pretrained=PRETRAINED)
model = model.to(device)

def tag_image_with_clip(image_path: str, candidate_tags: List[str], top_k: int = 5) -> List[Tuple[str, float]]:
    """
    Tags an image using OpenAI CLIP given a list of candidate tags.
    Returns top_k tags with their probabilities.
    """
    image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)
    text = open_clip.tokenize(candidate_tags).to(device)
    with torch.no_grad():
        image_features = model.encode_image(image)
        text_features = model.encode_text(text)
        logits_per_image = (image_features @ text_features.T).squeeze(0)
        probs = logits_per_image.softmax(dim=0).cpu().numpy()
    # Return top_k tags sorted by probability
    sorted_tags = sorted(zip(candidate_tags, probs), key=lambda x: -x[1])
    return sorted_tags[:top_k]

# Example usage (uncomment for quick test):
# tags = ["Florence", "Landscape", "Wildlife", "Nature", "Photography"]
# print(tag_image_with_clip("08de4264_7005919-Edit-Edit.jpg", tags))
