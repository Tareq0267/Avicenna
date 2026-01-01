"""
Malaysian Food Recognition using CLIP
Zero-shot classification for Malaysian cuisine
"""

import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel
import urllib.request
import json

# Top 100 Malaysian Foods
MALAYSIAN_FOODS = [
    # Main Dishes & Rice
    'nasi lemak', 'nasi goreng', 'nasi kerabu', 'nasi dagang', 'nasi campur',
    'nasi ayam', 'nasi kandar', 'nasi tomato', 'nasi briyani', 'nasi goreng kampung',
    
    # Noodles
    'char kway teow', 'laksa', 'curry laksa', 'asam laksa', 'penang laksa',
    'curry mee', 'mee goreng', 'mee rebus', 'hokkien mee', 'wonton mee',
    'pan mee', 'char kway teow', 'mee kolok', 'kolo mee', 'mee hoon goreng',
    'loh mee', 'mee jawa', 'mee sup', 'mee bandung', 'maggi goreng',
    
    # Bread & Roti
    'roti canai', 'roti telur', 'roti bom', 'roti tissue', 'roti john',
    'roti planta', 'murtabak', 'roti jala', 'naan', 'chapati',
    
    # Satay & Grilled
    'satay', 'satay ayam', 'satay kambing', 'satay daging', 'ayam percik',
    'ikan bakar', 'sotong bakar', 'ayam golek',
    
    # Curries & Stews
    'rendang', 'rendang ayam', 'rendang daging', 'curry chicken', 'curry fish',
    'kari ayam', 'kari kambing', 'kurma ayam', 'gulai ayam', 'gulai ikan',
    'masak lemak', 'asam pedas', 'sambal udang', 'sambal sotong',
    
    # Soups
    'bak kut teh', 'tom yam', 'soto ayam', 'sup tulang', 'sup ekor',
    'cendawan soup', 'laksa johor', 'mee rebus', 'laksam',
    
    # Dim Sum & Dumplings
    'dim sum', 'har gow', 'siew mai', 'char siew pau', 'pau',
    'wonton', 'dumpling', 'gyoza', 'xiao long bao',
    
    # Fried & Snacks
    'ayam goreng', 'ikan goreng', 'udang goreng', 'cempedak goreng',
    'pisang goreng', 'keropok lekor', 'cucur udang', 'rempeyek',
    'curry puff', 'karipap', 'popiah', 'spring roll', 'onde onde',
    'kuih', 'apam balik', 'roti bakar', 'kaya toast',
    
    # Desserts & Sweets
    'cendol', 'ais kacang', 'abc', 'bubur cha cha', 'sago gula melaka',
    'kuih lapis', 'kuih talam', 'kuih seri muka', 'kuih dadar', 'dodol',
    'pandan cake', 'durian', 'rojak buah',
    
    # Drinks
    'teh tarik', 'teh ais', 'kopi', 'milo', 'air bandung',
    'sirap bandung', 'limau ais', 'teh o', 'kopi o',
]

# Simplified nutrition database (per 100g serving)
NUTRITION_DB = {
    'nasi lemak': {'calories': 350, 'protein': 7, 'carbs': 45, 'fat': 15},
    'nasi goreng': {'calories': 180, 'protein': 5, 'carbs': 28, 'fat': 5},
    'char kway teow': {'calories': 300, 'protein': 12, 'carbs': 35, 'fat': 13},
    'roti canai': {'calories': 310, 'protein': 6, 'carbs': 42, 'fat': 13},
    'satay': {'calories': 165, 'protein': 20, 'carbs': 3, 'fat': 8},
    'laksa': {'calories': 250, 'protein': 12, 'carbs': 30, 'fat': 10},
    'rendang': {'calories': 280, 'protein': 22, 'carbs': 8, 'fat': 18},
    'bak kut teh': {'calories': 120, 'protein': 15, 'carbs': 2, 'fat': 6},
    'curry mee': {'calories': 280, 'protein': 10, 'carbs': 35, 'fat': 12},
    'nasi kandar': {'calories': 400, 'protein': 15, 'carbs': 50, 'fat': 15},
    'mee goreng': {'calories': 220, 'protein': 8, 'carbs': 32, 'fat': 7},
    'ayam goreng': {'calories': 290, 'protein': 27, 'carbs': 0, 'fat': 20},
    'roti john': {'calories': 350, 'protein': 15, 'carbs': 38, 'fat': 16},
    'murtabak': {'calories': 380, 'protein': 18, 'carbs': 35, 'fat': 19},
    'cendol': {'calories': 180, 'protein': 2, 'carbs': 35, 'fat': 5},
    'ais kacang': {'calories': 150, 'protein': 2, 'carbs': 32, 'fat': 3},
    'teh tarik': {'calories': 110, 'protein': 3, 'carbs': 18, 'fat': 3},
    'pisang goreng': {'calories': 250, 'protein': 2, 'carbs': 40, 'fat': 10},
    'nasi kerabu': {'calories': 320, 'protein': 12, 'carbs': 48, 'fat': 10},
    'asam pedas': {'calories': 150, 'protein': 18, 'carbs': 8, 'fat': 6},
}

def load_clip_model():
    """Load CLIP model for zero-shot classification"""
    print("Loading CLIP model...")
    print("(First time will download ~600MB, subsequent runs use cache)")
    
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    
    print("✓ Model loaded successfully")
    return model, processor

def predict_malaysian_food(model, processor, image_path, top_k=5):
    """
    Predict Malaysian food using CLIP zero-shot classification
    """
    # Load image
    image = Image.open(image_path).convert('RGB')
    
    # Create text prompts - adding context helps CLIP
    text_prompts = [f"a photo of {food}, Malaysian food" for food in MALAYSIAN_FOODS]
    
    # Process inputs
    inputs = processor(
        text=text_prompts,
        images=image,
        return_tensors="pt",
        padding=True
    )
    
    # Get predictions
    with torch.no_grad():
        outputs = model(**inputs)
        logits_per_image = outputs.logits_per_image
        probs = logits_per_image.softmax(dim=1)
    
    # Get top predictions
    top_probs, top_indices = torch.topk(probs[0], top_k)
    
    results = []
    for prob, idx in zip(top_probs, top_indices):
        food_name = MALAYSIAN_FOODS[idx.item()]
        confidence = prob.item() * 100
        
        results.append({
            'food': food_name,
            'confidence': confidence,
            'nutrition': NUTRITION_DB.get(food_name, None)
        })
    
    return results

def download_sample_image(url, save_path='test_malaysian_food.jpg'):
    """Download a sample food image"""
    print(f"Downloading sample image...")
    urllib.request.urlretrieve(url, save_path)
    print(f"✓ Image saved to {save_path}")
    return save_path

def main():
    print("=" * 70)
    print("Malaysian Food Recognition with CLIP")
    print("=" * 70)
    print(f"\nRecognizing {len(MALAYSIAN_FOODS)} Malaysian foods")
    print()
    
    # Load model
    model, processor = load_clip_model()
    
    print()
    print("-" * 70)
    print("Testing with sample image...")
    print("-" * 70)
    
    # Option 1: Use your own image
    # Uncomment and provide path:
    image_path = 'C:\\Users\\Asus\\PycharmProjects\\Avicenna\\scripts\\char_kueh_teow_ss5_1.jpg'
    
    # Option 2: Download sample images for testing
    # Sample URLs for Malaysian food:
    sample_urls = {
        'nasi_lemak': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSb9AIqcmZRWHTB-QfzHnKLilBpEZ3G_35ltlMpdVhupwN0z7fizBfcvquhy8IFUxYF6K61D6RJUCVKGvAyP9w1SSdCNCtGcIb0StSisD4&s=10',
        'char_kway_teow': 'https://images.unsplash.com/photo-1569562211093-4ed0d0758f12',
        'roti_canai': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQgxSY4VmVrbeBsqe5mXTcUDzXzf7pz6rxFM7XREZdepTrDJTEz3g6udPhjWjufGWgd-fWpXzamyZNsHrFQXo_lmOvcEkO2DWO9WHv-pAdN&s=10',
    }
    
    # Use nasi lemak as default test
    image_path = download_sample_image(sample_urls['nasi_lemak'])
    
    # Make prediction
    print(f"\nAnalyzing image: {image_path}")
    predictions = predict_malaysian_food(model, processor, image_path, top_k=5)
    
    print("\n" + "=" * 70)
    print("PREDICTIONS:")
    print("=" * 70)
    
    for i, pred in enumerate(predictions, 1):
        print(f"\n#{i} - {pred['food'].replace('_', ' ').title()}")
        print(f"    Confidence: {pred['confidence']:.2f}%")
        
        if pred['nutrition']:
            print(f"    Nutritional Info (per 100g):")
            print(f"      Calories: {pred['nutrition']['calories']} kcal")
            print(f"      Protein:  {pred['nutrition']['protein']}g")
            print(f"      Carbs:    {pred['nutrition']['carbs']}g")
            print(f"      Fat:      {pred['nutrition']['fat']}g")
        else:
            print(f"    (Nutrition data not in database yet)")
    
    print("\n" + "=" * 70)
    print("\nADVANTAGES OF CLIP:")
    print("✓ No training required - works out of the box")
    print("✓ Can recognize ANY food you add to the list")
    print("✓ Works 100% offline after first download")
    print("✓ Easy to customize for your specific needs")
    print("\nNEXT STEPS:")
    print("1. Test with your own Malaysian food images")
    print("2. Add/remove foods from MALAYSIAN_FOODS list")
    print("3. Expand nutrition database with more foods")
    print("4. Add portion size estimation (ask user or use object detection)")
    print("=" * 70)

if __name__ == "__main__":
    main()