import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Model, load_model
from tensorflow.keras.layers import Dense, GlobalAveragePooling2D
from sklearn.metrics.pairwise import cosine_similarity
from typing import Union, Optional, Tuple, Dict, Any
import requests
from io import BytesIO
from PIL import Image
import logging
from mtcnn import MTCNN

# TensorFlow CPU-only config
tf.config.set_visible_devices([], 'GPU')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
tf.config.threading.set_intra_op_parallelism_threads(1)
tf.config.threading.set_inter_op_parallelism_threads(1)

class FaceMatcher:
    def __init__(self, age_model_path: Optional[str] = None):
        self.detector = MTCNN(device="CPU:0")
        base_model = MobileNetV2(weights='imagenet', include_top=False, input_shape=(128, 128, 3))
        base_model.trainable = False
        x = GlobalAveragePooling2D()(base_model.output)
        x = Dense(64, activation='relu')(x)
        self.face_model = Model(inputs=base_model.input, outputs=x)
        
        self.age_model = None
        self.age_model_loaded = False
        self._load_age_model(age_model_path)
        self.logger = logging.getLogger(__name__)


    def _load_image(self, image_input: Union[str, np.ndarray]) -> Tuple[np.ndarray, str]:
        try:
            if isinstance(image_input, str):
                if image_input.startswith(('http://', 'https://')):
                    response = requests.get(image_input)
                    response.raise_for_status()
                    image = np.array(Image.open(BytesIO(response.content)))
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                else:
                    image = cv2.imread(image_input)
            elif isinstance(image_input, np.ndarray):
                image = image_input.copy()
            else:
                return None, "Unsupported input type"
            if image is None:
                return None, "Could not load image"
            return image, None
        except Exception as e:
            return None, str(e)

    def _get_main_face(self, image: np.ndarray) -> Tuple[np.ndarray, str]:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.detector.detect_faces(image_rgb)
        if not results:
            return None, "No face detected"
        main_face = max(results, key=lambda x: x['confidence'])
        x, y, w, h = main_face['box']
        pad = int(0.1 * min(w, h))
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(image.shape[1], x + w + pad), min(image.shape[0], y + h + pad)
        face_img = image[y1:y2, x1:x2]
        return face_img, None

    def preprocess_image(self, image_input: Union[str, np.ndarray], target_size: Tuple[int, int] = (128, 128)):
        image, err = self._load_image(image_input)
        if err:
            return None, err
        face_img, err = self._get_main_face(image)
        if err:
            return None, err
        try:
            face_img = cv2.resize(face_img, target_size)
            face_img = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
            face_img = face_img.astype('float32') / 255.0
            return np.expand_dims(face_img, axis=0), None
        except Exception as e:
            return None, str(e)

    def extract_features(self, image_input: Union[str, np.ndarray]):
        img, err = self.preprocess_image(image_input, (128, 128))
        if err:
            return None, err
        try:
            features = self.face_model.predict(img, batch_size=1, verbose=0)
            return features.flatten(), None
        except Exception as e:
            return None, str(e)


#  -------------------- will work later -----------------
    # def predict_age(self, image_input: Union[str, np.ndarray]) -> Dict[str, Any]:
    #     if not self.age_model_loaded:
    #         return {"predicted_age": None, "confidence": 0.0, "error": "Age model not loaded"}
    #     img, err = self.preprocess_image(image_input, (64, 64))
    #     if err:
    #         return {"predicted_age": None, "confidence": 0.0, "error": err}
    #     try:
    #         preds = self.age_model.predict(img, verbose=0)[0]
    #         if len(preds) > 1:
    #             idx = np.arange(0, len(preds))
    #             age = int(np.round(np.sum(preds * idx)))
    #             conf = float(np.max(preds))
    #         else:
    #             age = int(np.round(preds[0]))
    #             conf = 1.0
    #         return {"predicted_age": age, "confidence": conf, "error": None}
    #     except Exception as e:
    #         return {"predicted_age": None, "confidence": 0.0, "error": str(e)}

    def compare_faces(self, id_img: Union[str, np.ndarray], selfie_img: Union[str, np.ndarray], threshold=0.70):
        id_feat, err1 = self.extract_features(id_img)
        self_feat, err2 = self.extract_features(selfie_img)
        if err1 or err2:
            return {
                "match": False,
                "confidence": 0.0,
                "error": err1 or err2,
                "details": {}
            }
        try:
            sim = float(cosine_similarity([id_feat], [self_feat])[0][0])
            return {
                "match": sim >= threshold,
                "confidence": round(sim * 100, 2),
                "similarity_score": round(sim, 4),
                "threshold": float(threshold),
                "details": {"method": "MobileNetV2"}
            }
        except Exception as e:
            return {
                "match": False,
                "confidence": 0.0,
                "error": str(e),
                "details": {}
            }