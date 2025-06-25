from flask import Flask, request, jsonify
from utils.ocr import extract_dob_name
from utils.face_matcher import FaceMatcher
from utils.age import is_adult
from utils.feedback import evaluate_image_quality
import cv2
import os
import uuid

from flask_cors import CORS

app = Flask(__name__)

CORS(app, origins=[os.environ.get("CORS_ORIGIN", "http://localhost:5173")])

UPLOAD_FOLDER = "temp_images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

face_matcher = FaceMatcher()

def upload_images():
    doc_img = request.files.get("document")
    selfie_img = request.files.get("selfie")

    if not doc_img or not selfie_img:
        return None, None, None, None, jsonify({"error": "Both document and selfie are required"}), 400

    doc_ext = os.path.splitext(doc_img.filename)[1]
    selfie_ext = os.path.splitext(selfie_img.filename)[1]
    doc_path = os.path.join(UPLOAD_FOLDER, f"doc_{uuid.uuid4().hex}{doc_ext}")
    selfie_path = os.path.join(UPLOAD_FOLDER, f"selfie_{uuid.uuid4().hex}{selfie_ext}")

    doc_img.save(doc_path)
    selfie_img.save(selfie_path)

    return doc_path, selfie_path, None, None


#  2 routes ->
#    1. check image quality
#    2. verify image and get info

@app.route("/check-quality", methods=["POST"])
def check_quality():
    doc_path, selfie_path, error_response, error_code = upload_images()
    doc_image = cv2.imread(doc_path)
    selfie_image = cv2.imread(selfie_path)
    doc_feedback = evaluate_image_quality(doc_image)
    selfie_feedback = evaluate_image_quality(selfie_image)

    return jsonify({
        "document_feedback": doc_feedback,
        "selfie_feedback": selfie_feedback
    })

@app.route("/verify", methods=["POST"])
def verify():
    doc_path, selfie_path, error_response, error_code = upload_images()
    if error_response:
        return error_response, error_code

    ocr_result = extract_dob_name(doc_path)
    dob = ocr_result.get("dob")
    name = ocr_result.get("name")

    match_result = face_matcher.compare_faces(doc_path, selfie_path)

    age = is_adult(dob) if dob else 0

    if match_result.get("error"):
        return jsonify({
            "error": match_result["error"],
            "reason": "Face missing in input"
        }), 400

    face_match = "Face Verified" if match_result.get("match") else "Not Verified"
    confidence = match_result.get("confidence")

    # age_matched = "Age Verified" if (
    #     predicted_age is not None and age is not None and abs(age - predicted_age) <= 3
    # ) else "Not Verified"

    result = {
        "name": name,
        "dob": dob,
        "age": age,
        "is_adult": age >= 18,
        "face_match": face_match,
        "confidence": confidence
    }
    print(result)
    return jsonify(result)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


@app.route("/")
def home():
    return "Hello from Flask on Render!"