import cv2
import numpy as np
from tensorflow.keras.applications import VGG16
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from sklearn.metrics.pairwise import cosine_similarity
import logging

class DeepFaceMatchingService:
    def __init__(self):
        #  downloading from cv data 
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        base_model = VGG16(weights='imagenet', include_top=False, input_shape=(224, 224, 3))
        x = base_model.output
        x = GlobalAveragePooling2D()(x)
        x = Dense(128, activation='relu')(x)
        self.model = Model(inputs=base_model.input, outputs=x)
        self.logger = logging.getLogger(__name__)

    def preprocess_image(self, image_path):
        image = cv2.imread(image_path)
        if image is None:
            return None, "Could not load image"
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 4)

        if len(faces) == 0:
            return None, "No face detected"
        x, y, w, h = max(faces, key=lambda f: f[2] * f[3])

        face_img = image[y:y+h, x:x+w]
        face_img = cv2.resize(face_img, (224, 224))
        face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        face_img = face_img.astype('float32') / 255.0
        face_img = np.expand_dims(face_img, axis=0)

        return face_img, None


    def extract_features(self, image_path):
        processed_image, error = self.preprocess_image(image_path)
        if error:
            return None, error
        features = self.model.predict(processed_image)
        return features.flatten(), None


    def compare_faces(self, id_card_image, selfie_image, threshold=0.7):
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
            "match": is_match,
            "confidence": round(confidence, 2),
            "similarity_score": round(similarity, 4),
            "threshold": float(threshold),
            "details": {
                "method": "VGG16",
                "recommendation": "Match" if is_match else "No match"
            }
        }