# AI-Powered Smart Parking System

A full-stack application that uses AI to automatically recognize and register vehicles using license plate detection.

## Features

- **User Registration**: Register new car owners with their license plate information
- **AI-Powered Detection**: Automatically detect and recognize returning users using EasyOCR
- **License Plate Recognition**: Extract license plate numbers from images using computer vision
- **Dashboard**: View and manage all registered users
- **Real-time Feedback**: Visual and audio notifications for recognized users

## Project Structure

```
ocr/
├── backend/          # Flask API server
│   ├── app.py        # Main Flask application
│   ├── detection.py  # License plate detection logic
│   ├── requirements.txt
│   └── uploads/      # Stored license plate images
│
└── frontend/         # React frontend
    ├── src/
    │   ├── App.js
    │   ├── components/
    │   │   ├── RegistrationForm.js
    │   │   ├── DetectionForm.js
    │   │   └── Dashboard.js
    │   └── index.js
    ├── package.json
    └── public/
```

## Quick Start

### Prerequisites

- Python 3.8+
- Node.js 14+
- npm or yarn

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Activate the virtual environment:
```bash
# Create your env
python -m venv env

# On macOS/Linux
source ../env/bin/activate

# On Windows
..\env\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Run the Flask server:
```bash
python app.py
```

The backend will run on `http://localhost:5000`

### Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the React app:
```bash
npm start
```

The frontend will run on `http://localhost:3000`

## Usage

### 1. Register a New User

- Navigate to the "Register New User" tab
- Enter the user's name and license plate number
- Upload a photo of the license plate
- Click "Register User"

### 2. Detect a Returning User

- Navigate to the "Detect License Plate" tab
- Upload a photo containing the license plate
- The system will automatically detect and check if the user is registered
- You'll see either:
  - "Welcome Back, [Name]!" for recognized users (with sound notification)
  - "Unknown User" for unregistered plates

### 3. View All Users

- Navigate to the "View All Users" tab
- See all registered users in a table
- Delete users as needed

## How It Works

1. **Registration**: When a new user registers, their photo is stored along with their name and license plate number
2. **Detection**: When detecting, EasyOCR extracts text from the uploaded image
3. **Matching**: The detected text is compared against registered license plates using fuzzy matching
4. **Recognition**: If a match is found (with 80%+ similarity), the user is recognized

## Technology Stack

### Backend
- **Flask**: Web framework
- **EasyOCR**: License plate text extraction
- **SQLite**: Database
- **OpenCV**: Image processing
- **RapidFuzz**: Fuzzy string matching

### Frontend
- **React**: UI library
- **Tailwind CSS**: Styling
- **Axios**: HTTP client

## API Endpoints

- `POST /register` - Register a new user
- `POST /detect` - Detect and recognize a license plate
- `GET /users` - Get all registered users
- `DELETE /users/<id>` - Delete a user

## Troubleshooting

### Backend Issues

1. **Module not found**: Make sure you're in the virtual environment and dependencies are installed
2. **Port already in use**: Change the port in `app.py` (default: 5000)

### Frontend Issues

1. **Cannot connect to backend**: Ensure the backend is running on port 5000
2. **CORS errors**: The backend has CORS enabled by default

### OCR Issues

1. **Low detection accuracy**: Use clear, well-lit images of license plates
2. **No plate detected**: Try different angles or lighting conditions


## License

MIT License - feel free to use this project for learning and development!

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.




