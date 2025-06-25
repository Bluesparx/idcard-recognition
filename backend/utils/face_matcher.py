import os
import cv2
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.models import Model
from tensorflow.keras.layers import GlobalAveragePooling2D, Dense, Dropout
from sklearn.metrics.pairwise import cosine_similarity
from typing import Union, Optional, Tuple
from mtcnn import MTCNN
from PIL import Image
import requests
from io import BytesIO
import logging


tf.config.set_visible_devices([], 'GPU')
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
tf.config.threading.set_intra_op_parallelism_threads(1)
tf.config.threading.set_inter_op_parallelism_threads(1)

class FaceMatcher:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.detector = MTCNN()
        self.face_model = self._build_model()

    def _build_model(self):
        base = MobileNetV2(input_shape=(224, 224, 3), include_top=False, weights='imagenet')
        base.trainable = False
        x = GlobalAveragePooling2D()(base.output)
        x = Dense(256, activation='relu')(x)
        x = Dropout(0.3)(x)
        model = Model(inputs=base.input, outputs=x)
        return model

    def _load_image(self, image_input: Union[str, np.ndarray]) -> Tuple[Optional[np.ndarray], Optional[str]]:
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

    def _get_main_face(self, image: np.ndarray, pad_ratio=0.3) -> Tuple[Optional[np.ndarray], Optional[str]]:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        faces = self.detector.detect_faces(image_rgb)
        if not faces:
            return None, "No face detected"
        face = max(faces, key=lambda x: x['confidence'])
        x, y, w, h = face['box']
        pad = int(min(w, h) * pad_ratio)
        x1, y1 = max(0, x - pad), max(0, y - pad)
        x2, y2 = min(image.shape[1], x + w + pad), min(image.shape[0], y + h + pad)
        face_img = image[y1:y2, x1:x2]
        return face_img, None

    def preprocess_image(self, image_input: Union[str, np.ndarray], target_size=(224, 224)) -> Tuple[Optional[np.ndarray], Optional[str]]:
        image, err = self._load_image(image_input)
        if err:
            return None, err
        face, err = self._get_main_face(image, pad_ratio=0.3)
        if err:
            return None, err
        try:
            face = cv2.resize(face, target_size)
            face = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
            face = face.astype('float32') / 255.0
            return np.expand_dims(face, axis=0), None
        except Exception as e:
            return None, str(e)

    def extract_features(self, image_input: Union[str, np.ndarray]) -> Tuple[Optional[np.ndarray], Optional[str]]:
        image_tensor, err = self.preprocess_image(image_input)
        if err:
            return None, err
        try:
            embedding = self.face_model.predict(image_tensor, batch_size=1, verbose=0)[0]
            embedding = embedding / np.linalg.norm(embedding)
            return embedding, None
        except Exception as e:
            return None, str(e)

    def compare_faces(self, id_img: Union[str, np.ndarray], selfie_img: Union[str, np.ndarray], threshold=0.6) -> dict:
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
            similarity = float(cosine_similarity([id_feat], [self_feat])[0][0])
            return {
                "match": similarity >= threshold,
                "confidence": round(similarity * 100, 2),
                "similarity_score": round(similarity, 4),
                "threshold": threshold,
                "details": {"method": "MobileNetV2 (224x224, padded, GAP + Dense)"}
            }
        except Exception as e:
            return {
                "match": False,
                "confidence": 0.0,
                "error": str(e),
                "details": {}
            }