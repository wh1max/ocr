import React, { useState } from 'react';
import RegistrationForm from './components/RegistrationForm';
import DetectionForm from './components/DetectionForm';
import Dashboard from './components/Dashboard';

function App() {
  const [activeTab, setActiveTab] = useState('register');
  const [refreshKey, setRefreshKey] = useState(0);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  const handleUserAdded = () => {
    // Trigger dashboard refresh
    setRefreshKey(prev => prev + 1);
    setActiveTab('dashboard');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="container mx-auto px-4 py-8">
        <header className="text-center mb-8">
          <h1 className="text-4xl font-bold text-indigo-900 mb-2">
             AI-Powered Smart Parking System
          </h1>
          <p className="text-gray-600">Automated License Plate Recognition</p>
        </header>

        {/* Navigation Tabs */}
        <div className="flex justify-center mb-8">
          <div className="inline-flex rounded-lg border border-indigo-200 bg-white p-1">
            <button
              onClick={() => handleTabChange('register')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'register'
                  ? 'bg-indigo-500 text-white'
                  : 'text-indigo-600 hover:bg-indigo-50'
              }`}
            >
              Register New User
            </button>
            <button
              onClick={() => handleTabChange('detect')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'detect'
                  ? 'bg-indigo-500 text-white'
                  : 'text-indigo-600 hover:bg-indigo-50'
              }`}
            >
              Detect License Plate
            </button>
            <button
              onClick={() => handleTabChange('dashboard')}
              className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                activeTab === 'dashboard'
                  ? 'bg-indigo-500 text-white'
                  : 'text-indigo-600 hover:bg-indigo-50'
              }`}
            >
              View All Users
            </button>
          </div>
        </div>

        {/* Content Area */}
        <div className="max-w-3xl mx-auto">
          {activeTab === 'register' && (
            <RegistrationForm onUserAdded={handleUserAdded} />
          )}
          {activeTab === 'detect' && <DetectionForm />}
          {activeTab === 'dashboard' && <Dashboard key={refreshKey} />}
        </div>
      </div>

      <footer className="text-center mt-12 py-4 text-gray-600">
        <p>Smart Parking System © 2024</p>
      </footer>
    </div>
  );
}

export default App;




