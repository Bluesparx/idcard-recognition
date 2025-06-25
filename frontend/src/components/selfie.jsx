import React, { useRef, useState } from "react";
import Webcam from "react-webcam";
import axios from "axios";
import { toast, ToastContainer } from "react-toastify";


function Selfie() {
  const webcamRef = useRef(null);
  const fileInputRef = useRef(null); 
  const [selfie, setSelfie] = useState(null);
  const [document, setDocument] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const baseUrl = import.meta.env.VITE_API_HOST;

  const captureSelfie = () => {
    const imageSrc = webcamRef.current.getScreenshot();
    fetch(imageSrc)
      .then(res => res.blob())
      .then(blob => {
        setSelfie(new File([blob], "selfie.png", { type: "image/png" }));
      });
  };

  const handleDocumentChange = (e) => {
    setDocument(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selfie || !document) return;

    setLoading(true);
    setResult(null);

    const formData = new FormData();
    formData.append("selfie", selfie);
    formData.append("document", document);

    try {
      const qualityCheck = await axios.post(`${baseUrl}/check-quality`, formData);
      const { document_feedback, selfie_feedback } = qualityCheck.data;

      if ((document_feedback?.length > 0) || (selfie_feedback?.length > 0)) {
        if (Array.isArray(document_feedback)) {
          document_feedback.forEach(msg => toast.warn(`Document: ${msg}`));
        }
        if (Array.isArray(selfie_feedback)) {
          selfie_feedback.forEach(msg => toast.warn(`Selfie: ${msg}`));
        }
        setLoading(false);
        return;
      }
      toast.success("Quality of images is good!"); 
      const verifyResponse = await axios.post(`${baseUrl}/verify`, formData);
      const verificationResult = verifyResponse.data;
      setResult(verificationResult);

      if (verificationResult.face_match?.match) {
        toast.success("Verification successful!");
      }
    } catch (err) {
      const status = err.response?.status;
      const errorMessage = err.response?.data?.error;

      if (status === 400 && err.response?.data?.reason === "Face missing in input") {
        toast.error("No face detected in one or both images!");
      } else {
        toast.error("Verification failed.");
      }
      setResult({ error: true, message: errorMessage || "Verification failed." });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSelfie(null);
    setDocument(null);
    setResult(null);

    if (fileInputRef.current) {
      fileInputRef.current.value = ""; // for file we use ref
    }
  };

  return (
    <div className="selfie-component">
      <h2>Face & Age Verification</h2>
      <div className="selfie-input">
      <Webcam
        audio={false}
        ref={webcamRef}
        screenshotFormat="image/png"
        width={300}
        height={200}
        style={{ marginBottom: 10 , transform: "scaleX(-1)"}}
      />
      <button onClick={captureSelfie}>Capture Selfie</button>
      {selfie && <p>Selfie captured</p>}
      </div>

      <div className="doc-input">
        <input
          type="file"
          accept="image/*"
          onChange={handleDocumentChange}
          ref={fileInputRef} 
        />
        {document && <p>{document.name}</p>}
      </div>

      <button onClick={handleSubmit} disabled={loading || !selfie || !document}>
        {loading ? "Verifying..." : "Submit"}
      </button>

      {result && (
        <div style={{ marginTop: 20 }}>
          {result.error ? (
            <p className="error-msg">{result.message}</p>
          ) : (
            <div className="results">
              <div className="face">
              <p>Face Similarity: {result.confidence}%</p>
              <p>Face verification: {result.face_match}</p>
              <p>DOB: {result.dob}</p>
              <p>Age: {result.age}</p>
              </div>
              {/* <div className="age">
              <p>Age Verification: {result.age_matched}</p>
              <p>Predicted Age:{result.predicted_age}</p>
              </div> */}
            </div>
          )}
        </div>
      )}

      {result && (
        <button onClick={resetForm} style={{ marginTop: 10 }}>
          Reset
        </button>
      )}

      <ToastContainer position="top-right" autoClose={3000} />
    </div>
  );
}

export default Selfie;