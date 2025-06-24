import cv2
import numpy as np
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from sklearn.metrics.pairwise import cosine_similarity
import logging
from concurrent.futures import ThreadPoolExecutor
import tensorflow as tf

class FaceMatcher:
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(128, 128, 3))
        
        base_model.trainable = False
        
        x = base_model.output
        x = GlobalAveragePooling2D()(x)
        x = Dense(64, activation='relu')(x)
        self.model = Model(inputs=base_model.input, outputs=x)
        
        self.model.compile(optimizer='adam', loss='mse')
        
        self.logger = logging.getLogger(__name__)
    
    def preprocess_image(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            return None, "Could not load image"
        
        height, width = image.shape[:2]
        if width > 800:
            scale = 800 / width
            new_width = 800
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height))
        
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=1.3,
            minNeighbors=3,
            minSize=(30, 30)
        )
        
        if len(faces) == 0:
            return None, "No face detected"
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
        
        padding = int(0.1 * min(w, h))
        x1 = max(0, x - padding)
        y1 = max(0, y - padding)
        x2 = min(image.shape[1], x + w + padding)
        y2 = min(image.shape[0], y + h + padding)
        
        face_img = image[y1:y2, x1:x2]
        
        face_img = cv2.resize(face_img, (128, 128))
        face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        face_img = face_img.astype('float32') / 255.0
        face_img = np.expand_dims(face_img, axis=0)
        
        return face_img, None
    
    def extract_features(self, image_path):
        processed_image, error = self.preprocess_image(image_path)
        if error:
            return None, error
        
        features = self.model.predict(processed_image, batch_size=1, verbose=0)
        return features.flatten(), None
    
    def compare_faces(self, id_card_image, selfie_image, threshold=0.6):
        id_features, id_error = self.extract_features(id_card_image)
        selfie_features, selfie_error = self.extract_features(selfie_image)

        if id_error or selfie_error:
            return {
                "match": False,
                "confidence": 0.0,
                "error": id_error or selfie_error,
                "details": {}
            }

        similarity = float(cosine_similarity([id_features], [selfie_features])[0][0])
        confidence = float(similarity * 100)
        is_match = bool(similarity >= threshold)

        return {
            "match": "Match" if is_match else "No match",
            "confidence": round(confidence, 2),
            "similarity_score": round(similarity, 4),
            "threshold": float(threshold),
            "details": {
                "method": "MobileNetV2"
            }
        }