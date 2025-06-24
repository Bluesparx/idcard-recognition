
from datetime import datetime

def is_adult(dob_str):
    
    # Returns age as integer.
    
    try:
        dob = datetime.strptime(dob_str, "%d/%m/%Y")
        today = datetime.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except:
        return 0
