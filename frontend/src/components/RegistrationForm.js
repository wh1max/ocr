import React, { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:5000';

function RegistrationForm({ onUserAdded }) {
  const [formData, setFormData] = useState({
    name: '',
    licensePlate: '',
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData({
      ...formData,
      [name]: value,
    });
  };

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
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setMessage(null);
    setError(null);

    if (!formData.name || !formData.licensePlate || !selectedFile) {
      setError('Please fill in all fields and upload a photo');
      return;
    }

    setLoading(true);

    try {
      const data = new FormData();
      data.append('name', formData.name);
      data.append('license_plate_number', formData.licensePlate);
      data.append('photo', selectedFile);

      const response = await axios.post(`${API_URL}/register`, data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.data.status === 'success') {
        setMessage(`✅ ${response.data.message}`);
        setFormData({ name: '', licensePlate: '' });
        setSelectedFile(null);
        setPreview(null);
        
        // Call the callback to refresh the dashboard
        if (onUserAdded) {
          setTimeout(() => {
            onUserAdded();
          }, 1000);
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to register user');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-lg p-8">
      <h2 className="text-2xl font-bold text-indigo-900 mb-6">
        Register New User
      </h2>
      
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-2">
            Full Name
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleInputChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            placeholder="Enter full name"
            required
          />
        </div>

        <div>
          <label htmlFor="licensePlate" className="block text-sm font-medium text-gray-700 mb-2">
            License Plate Number
          </label>
          <input
            type="text"
            id="licensePlate"
            name="licensePlate"
            value={formData.licensePlate}
            onChange={handleInputChange}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent uppercase"
            placeholder="ABC-1234"
            required
          />
        </div>

        <div>
          <label htmlFor="photo" className="block text-sm font-medium text-gray-700 mb-2">
            License Plate Photo
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
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
            loading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-indigo-600 hover:bg-indigo-700 text-white'
          }`}
        >
          {loading ? 'Registering...' : 'Register User'}
        </button>

        {message && (
          <div className="p-4 bg-green-100 border border-green-400 text-green-700 rounded-lg">
            {message}
          </div>
        )}

        {error && (
          <div className="p-4 bg-red-100 border border-red-400 text-red-700 rounded-lg">
            {error}
          </div>
        )}
      </form>
    </div>
  );
}

export default RegistrationForm;




