import React, { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:5000';

function DetectionForm() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(file);
      setError(null);
      setResult(null);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setResult(null);
    setError(null);

    if (!selectedFile) {
      setError('Please select an image to detect');
      return;
    }

    setLoading(true);

    try {
      const data = new FormData();
      data.append('photo', selectedFile);

      const response = await axios.post(`${API_URL}/detect`, data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      setResult(response.data);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to detect license plate');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
  };

  const playSound = () => {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    oscillator.type = 'sine';
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    oscillator.frequency.setValueAtTime(600, audioContext.currentTime + 0.1);
    oscillator.connect(audioContext.destination);
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.2);
  };

  React.useEffect(() => {
    if (result?.status === 'known_user') {
      playSound();
    }
  }, [result]);

  return (
    <div className="bg-white rounded-xl shadow-lg p-8">
      <h2 className="text-2xl font-bold text-indigo-900 mb-6">
        Detect License Plate
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="photo" className="block text-sm font-medium text-gray-700 mb-2">
            Upload License Plate Photo
          </label>
          <input
            type="file"
            id="photo"
            name="photo"
            accept="image/*"
            onChange={handleFileChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            required
          />
          {preview && (
            <div className="mt-4">
              <img
                src={preview}
                alt="Preview"
                className="w-full max-w-md mx-auto rounded-lg shadow-md"
              />
              <button
                type="button"
                onClick={handleReset}
                className="mt-2 text-red-600 hover:text-red-800 text-sm font-medium"
              >
                Clear Image
              </button>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading || !selectedFile}
          className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
            loading || !selectedFile
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white'
          }`}
        >
          {loading ? 'Detecting...' : 'Detect License Plate'}
        </button>

        {error && (
          <div className="p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}

        {result && (
          <div className={`p-6 rounded-lg ${
            result.status === 'known_user'
              ? 'bg-green-50 border-2 border-green-400'
              : result.status === 'unknown_user'
              ? 'bg-yellow-50 border-2 border-yellow-400'
              : 'bg-gray-50 border-2 border-gray-400'
          }`}>
            {/* Show Annotated Image if available */}
            {result.annotated_image_base64 && (
              <div className="mb-6">
                <img
                  src={`data:image/jpeg;base64,${result.annotated_image_base64}`}
                  alt="Annotated Detection"
                  className="w-full max-w-3xl mx-auto rounded-lg shadow-lg border-4 border-white"
                />
                <p className="text-xs text-center text-gray-500 mt-2">
                  🟢 Green = Registered | 🔴 Red = Unknown
                </p>
              </div>
            )}

            {result.status === 'known_user' && (
              <div className="text-center">
                <div className="text-6xl mb-4">✅</div>
                <h3 className="text-2xl font-bold text-green-700 mb-2">
                  Welcome Back, {result.name}!
                </h3>
                <p className="text-green-600 font-semibold text-lg">
                  License Plate: {result.license_plate}
                </p>
                {result.detected_plate && result.detected_plate !== result.license_plate && (
                  <p className="text-sm text-gray-600 mt-2">
                    Detected: {result.detected_plate} (matched with {(result.similarity * 100).toFixed(0)}% similarity)
                  </p>
                )}
                {result.confidence && (
                  <p className="text-sm text-gray-500 mt-1">
                    Detection Confidence: {(result.confidence * 100).toFixed(1)}%
                  </p>
                )}
              </div>
            )}

            {result.status === 'unknown_user' && (
              <div className="text-center">
                <div className="text-6xl mb-4">⚠️</div>
                <h3 className="text-2xl font-bold text-yellow-700 mb-2">
                  Unknown License Plate
                </h3>
                <p className="text-yellow-600">
                  This license plate is not registered in the system.
                </p>
                {result.detected_plate && (
                  <p className="text-lg font-semibold text-gray-700 mt-3">
                    Detected Plate: {result.detected_plate}
                  </p>
                )}
                {result.confidence && (
                  <p className="text-sm text-gray-500 mt-1">
                    Detection Confidence: {(result.confidence * 100).toFixed(1)}%
                  </p>
                )}
                <p className="text-sm text-gray-600 mt-3">
                  Please register this user first.
                </p>
              </div>
            )}

            {result.status === 'no_plate_found' && (
              <div className="text-center">
                <div className="text-6xl mb-4">🔍</div>
                <h3 className="text-2xl font-bold text-gray-700 mb-2">
                  No License Plate Detected
                </h3>
                <p className="text-gray-600">
                  Could not detect a license plate in the uploaded image.
                </p>
                <p className="text-sm text-gray-500 mt-2">
                  Please try a clearer image or better lighting.
                </p>
              </div>
            )}
          </div>
        )}
      </form>
    </div>
  );
}

export default DetectionForm;




