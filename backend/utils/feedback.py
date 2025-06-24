import cv2

def evaluate_image_quality(image, blur_threshold=100.0, brightness_threshold=50):
    feedback = []

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < blur_threshold:
        feedback.append("Image appears blurry")

    brightness = gray.mean()
    if brightness < brightness_threshold:
        feedback.append("Image is too dark")

    return feedback