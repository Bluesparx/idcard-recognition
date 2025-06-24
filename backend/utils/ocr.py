import easyocr
import re

def extract_dob_name(image_path, languages=['en']):
    reader = easyocr.Reader(languages)
    results = reader.readtext(image_path, detail=0)
    text = "\n".join(results)

    # Extract
    dob_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
    dob = dob_match.group(0) if dob_match else None
    
    #  accepts any two words togeter right now. 
    #  need to work on excluding - government, india, etc .
    
    SKIP_PHRASES = [
        "government of india", "govt of india", "भारत सरकार", "indian government",
        "republic of india", "ministry of", "aadhaar", "uidai",
        "male", "female", "महिला", "पुरुष",
        "aam aadmi ka aadhikar", "मेरा आधार मेरी पहचान"
    ]
    english_name = None
    hindi_name = None

    for line in results:
        line_clean = line.strip()
        lower_line = line_clean.lower()

        # Skip numeric lines or skip phrases
        if re.match(r'^\d', lower_line):
            continue
        if any(phrase in lower_line for phrase in SKIP_PHRASES):
            continue

        # Detect script: Hindi characters are in Unicode Devanagari block
        is_hindi = any('\u0900' <= c <= '\u097F' for c in line_clean)
        
        if is_hindi and not hindi_name:
            hindi_name = line_clean
        elif not is_hindi and not english_name:
            english_name = line_clean

        if english_name and hindi_name:
            break

    return {
        "dob": dob,
        "name_en": english_name,
        "name_hi": hindi_name
    }