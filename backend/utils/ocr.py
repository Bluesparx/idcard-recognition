import easyocr
import re

def extract_dob_name(image_path, languages=['en']):
    reader = easyocr.Reader(languages)
    results = reader.readtext(image_path, detail=0)
    text = "\n".join(results)

    # Extract
    dob_match = re.search(r'\d{2}/\d{2}/\d{4}', text)
    dob = dob_match.group(0) if dob_match else None
    
    name = None  
    
    #  accepts any two words togeter right now. 
    #  need to work on excluding - government, india, etc .

    for line in results:
        line = line.strip()
        if len(line.split()) >= 2 and not re.match(r'^\d', line):
            name = line
    
    return {
        "dob": dob, 
        "name": name
    }