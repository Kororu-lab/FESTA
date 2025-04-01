# FESTA: From Earth to Star Thanks to AI

FESTA is an advanced Q&A system for academic papers, leveraging Retrieval-Augmented Generation (RAG) technology to provide accurate and context-aware responses to questions about research papers.

## Features

- **Multi-format Document Support**
  - PDF, Markdown, HTML, LaTeX, and TXT file support
  - Automatic text extraction and processing
  - Metadata extraction and management

- **Intelligent Q&A System**
  - Context-aware responses using DeepSeek API
  - Document-based answer generation
  - Source citation and reference tracking

- **User-Friendly Interface**
  - Modern chat-style UI
  - Real-time document upload and processing
  - Interactive Q&A experience

## Technology Stack

### Backend
- FastAPI
- SQLite (with SQLAlchemy)
- DeepSeek API
- LangChain
- ChromaDB (for vector storage)

### Frontend
- HTML5
- TailwindCSS
- WebSocket for real-time communication

## Project Structure

```
FESTA/
├── backend/
│   ├── app/
│   │   ├── data/
│   │   │   ├── papers/         # Original uploaded papers
│   │   │   │   └── db/            # Database files
│   │   ├── models/            # Data models
│   │   ├── utils/             # Utility functions
│   │   └── main.py           # FastAPI application
│   ├── static/               # Static files
│   ├── templates/            # HTML templates
│   └── requirements.txt      # Python dependencies
└── README.md
```

## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/Kororu-lab/FESTA.git
cd FESTA
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
cd backend
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the backend directory with:
```
DEEPSEEK_API_KEY=your_api_key_here
```

5. Run the application:
```bash
uvicorn app.main:app --reload
```

6. Access the application:
Open your browser and navigate to `http://localhost:8000`

## Usage

1. **Upload Papers**
   - Click the "Upload" button to select and upload your papers
   - Supported formats: PDF, Markdown, HTML, LaTeX, TXT

2. **Ask Questions**
   - Type your question in the chat input
   - The system will analyze relevant papers and provide context-aware answers
   - Sources are cited for transparency

3. **View Responses**
   - Answers are displayed in a chat-like interface
   - Reference documents are shown below each response

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- DeepSeek API for providing the language model capabilities
- FastAPI team for the excellent web framework
- All contributors and users of this project 