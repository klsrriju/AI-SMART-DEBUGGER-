# AI Smart Debugger & Converter

A powerful web application that automatically fixes Python code errors using AI, converts code between programming languages, and provides real-time AI assistance for learning.

## Features

### Core Features
- **Auto Code Debugger** - Instantly detects and fixes Python errors using AI
- **Language Converter** - Convert code between 8+ programming languages
- **AI Chat Assistant** - Ask questions about your code in real-time
- **Mistakes Tracker** - Learn from your common coding mistakes
- **Progress History** - Track all your debugging sessions
- **Multi-Device Sync** - Access your data from any device

### User Features
- **User Authentication** - Create account and login
- **Skill Level Tracking** - Beginner, Intermediate, Expert, Master
- **Personalized Notes** - Save your frequent mistakes
- **Cloud Sync** - Data syncs across all devices via SQLite database

## Tech Stack

| Technology | Purpose |
|-----------|---------|
| **Python (Flask)** | Backend API server |
| **SQLite** | Database for multi-device sync |
| **JavaScript** | Frontend logic |
| **Groq API** | AI code fixing (Llama 3.1) |
| **HTML/CSS** | Modern responsive UI |

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/klsrriju/ai-smart-debugger.git
cd ai-smart-debugger
```

### 2. Install Dependencies
```bash
pip install flask flask-cors
```

### 3. Run the Server
```bash
python server.py
```

### 4. Open in Browser
```
http://localhost:5000
```

## Project Structure

```
ai-smart-debugger/
├── server.py          # Flask backend with SQLite
├── index.html         # Frontend application
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

## Database Schema

### Users Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| username | TEXT | Unique login name |
| password_hash | TEXT | SHA256 hashed password |
| name | TEXT | Display name |
| user_class | TEXT | Class/University |
| skill_level | TEXT | beginner/intermediate/expert/master |

### Sessions Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to users |
| original_code | TEXT | Code with errors |
| fixed_code | TEXT | Corrected code |
| errors | TEXT | Error analysis |
| explanation | TEXT | AI explanation |

### Mistakes Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to users |
| mistake | TEXT | Common mistake note |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/register` | POST | Create new account |
| `/api/login` | POST | Login to account |
| `/api/sessions` | POST | Save debugging session |
| `/api/sessions/<user_id>` | GET | Get user sessions |
| `/api/mistakes` | POST | Save a mistake note |
| `/api/mistakes/<user_id>` | GET | Get user mistakes |
| `/api/health` | GET | Health check |

## Supported Languages

- Python
- JavaScript
- Java
- C++
- C#
- Go
- Rust
- Ruby

## Screenshots

### Login/Registration
Clean modal for user signup with skill level assessment.

### Debug Interface
- Faults Found - Shows all code errors
- Corrected Code - Fixed version of code
- AI Assistant - Chat for follow-up questions
- Mistakes Notes - Personal learning tracker

### Language Converter
Side-by-side source and converted code with language dropdowns.

## Development

### Local Development
```bash
# Start development server
python server.py

# Access at
http://localhost:5000
```

### Multi-Device Setup
```bash
# Find your IP
ipconfig

# Start server
python server.py

# Other devices access via
http://YOUR-IP:5000
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## License

MIT License - feel free to use for educational purposes.

## Author

KLSR

## Acknowledgments

- Groq API for providing free AI inference
- Flask for the backend framework
- Open source community
