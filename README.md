# AI Case Study Generator - Flask Application

A comprehensive Flask application for generating business case studies with AI-powered content creation, video generation, and podcast creation.

## Project Structure

```
AICaseStudy/
├── app/                          # Main application package
│   ├── __init__.py              # Flask app factory
│   ├──                 # SQLAlchemy models
│   ├── routes/                  # Route blueprints
│   │   ├── __init__.py
│   │   ├── main.py             # Main routes (index, sessions)
│   │   ├── auth.py             # Authentication routes
│   │   ├── case_studies.py     # Case study management
│   │   ├── interviews.py       # Interview handling
│   │   ├── media.py            # Media generation (video, podcast)
│   │   └── api.py              # General API endpoints
│   ├── services/               # Business logic services
│   │   ├── __init__.py
│   │   ├── ai_service.py       # OpenAI integration
│   │   ├── media_service.py    # External media APIs
│   │   └── case_study_service.py # PDF/Word generation
│   ├── schemas/                # DTO schemas (Marshmallow)
│   │   ├── __init__.py
│   │   ├── user_schemas.py     # User DTOs
│   │   ├── case_study_schemas.py # Case study DTOs
│   │   ├── interview_schemas.py # Interview DTOs
│   │   ├── media_schemas.py    # Media DTOs
│   │   └── feedback_schemas.py # Feedback DTOs
│   ├── mappers/                # DTO mappers
│   │   ├── __init__.py
│   │   ├── user_mapper.py      # User mapper
│   │   ├── case_study_mapper.py # Case study mapper
│   │   ├── interview_mapper.py # Interview mapper
│   │   ├── media_mapper.py     # Media mapper
│   │   └── feedback_mapper.py  # Feedback mapper
│   └── utils/                  # Utility functions
│       ├── __init__.py
│       ├── auth_helpers.py     # Authentication utilities
│       ├── validators.py       # Input validation
│       └── text_processing.py  # Text processing utilities
├── static/                     # Static files (CSS, JS, images)
├── templates/                  # HTML templates
├── generated_pdfs/             # Generated PDF files
├── transcripts/                # Interview transcripts
├── client_transcripts/         # Client interview transcripts
├── config.py                   # Configuration settings
├── run.py                      # Application entry point
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

## Features

### Core Functionality
- **User Authentication**: Secure login/signup system with session management
- **Case Study Management**: Create, edit, and organize case studies
- **Interview Process**: Solution provider and client interview workflows
- **AI-Powered Content**: OpenAI integration for summaries and content generation
- **Media Generation**: Video and podcast creation using external APIs
- **DTO & Mappers**: Clean separation between API contracts and internal models

### Media Generation
- **HeyGen Videos**: AI-generated talking head videos
- **Pictory Videos**: Automated video creation from case studies
- **Wondercraft Podcasts**: AI-generated podcast episodes
- **LinkedIn Posts**: Social media content generation

### Document Generation
- **PDF Reports**: Professional case study PDFs
- **Word Documents**: Editable case study documents
- **Sentiment Analysis**: Client feedback analysis
- **Satisfaction Metrics**: Client satisfaction tracking

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AICaseStudy
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secret-key
   JWT_SECRET_KEY=your-jwt-secret
   DATABASE_URL=sqlite:///./case_study.db
   OPENAI_API_KEY=your-openai-api-key
   HEYGEN_API_KEY=your-heygen-api-key
   PICTORY_CLIENT_ID=your-pictory-client-id
   PICTORY_CLIENT_SECRET=your-pictory-client-secret
   PICTORY_USER_ID=your-pictory-user-id
   WONDERCRAFT_API_KEY=your-wondercraft-api-key
   ```

5. **Initialize the database**
   ```bash
   python run.py init-db
   ```

6. **Run the application**
   ```bash
   python run.py
   ```

## Usage

### Starting the Application
```bash
python run.py
```
The application will be available at `http://localhost:5000`

### Database Management
```bash
# Initialize database
python run.py init-db

# Create tables
python run.py create-tables
```

## API Endpoints

### Authentication
- `POST /api/signup` - User registration
- `POST /api/login` - User login
- `POST /api/logout` - User logout
- `GET /api/user` - Get current user info

### Case Studies
- `GET /api/case_studies` - List user's case studies
- `POST /api/labels` - Create label
- `PATCH /api/labels/<id>` - Update label
- `DELETE /api/labels/<id>` - Delete label

### Interviews
- `POST /save_provider_summary` - Save solution provider interview
- `POST /save_client_transcript` - Save client interview
- `POST /generate_client_summary` - Generate client summary
- `POST /generate_full_case_study` - Generate complete case study

### Media Generation
- `POST /api/generate_video` - Generate HeyGen video
- `GET /api/video_status/<id>` - Check video status
- `POST /api/generate_pictory_video` - Generate Pictory video
- `GET /api/pictory_video_status/<id>` - Check Pictory video status
- `POST /api/generate_podcast` - Generate podcast
- `GET /api/podcast_status/<id>` - Check podcast status
- `POST /api/generate_linkedin_post` - Generate LinkedIn post

### Documents
- `POST /api/save_final_summary` - Save final summary
- `POST /api/save_as_word` - Save as Word document
- `GET /download/<filename>` - Download generated files

## Configuration

The application uses a configuration system with different environments:

- **Development**: Debug mode enabled, SQLite database
- **Production**: Optimized for production deployment
- **Testing**: In-memory database for testing

Configuration is handled in `config.py` and can be customized for different deployment environments.

## Database Models

### User
- Basic user information and authentication
- Company details and login tracking

### CaseStudy
- Main case study entity
- Links to provider and client interviews
- Stores generated media URLs and status

### SolutionProviderInterview
- Solution provider interview data
- Transcript and summary storage

### ClientInterview
- Client interview data
- Transcript and summary storage

### InviteToken
- Client interview invitation tokens
- Token management and validation

### Label
- User-defined labels for case studies
- Many-to-many relationship with case studies

### Feedback
- User feedback system
- Rating and feedback type tracking

## Services

### AIService
- OpenAI API integration
- Content generation and summarization
- Name extraction from case studies

### MediaService
- HeyGen video generation
- Pictory video creation
- Wondercraft podcast generation

### CaseStudyService
- PDF and Word document generation
- Sentiment analysis
- Client satisfaction metrics

## DTOs and Mappers

### Schemas (DTOs)
The application uses Marshmallow schemas to define Data Transfer Objects (DTOs) for:
- **Input Validation**: Automatic validation of incoming request data
- **Output Serialization**: Consistent API response formatting
- **Type Safety**: Strong typing for API contracts
- **Documentation**: Self-documenting API structure

### Mappers
Mapper classes handle conversion between:
- **Models to DTOs**: Converting database models to API responses
- **DTOs to Models**: Converting validated input to database models
- **Data Transformation**: Handling complex data transformations
- **Error Handling**: Centralized error handling for data conversion

### Benefits
- **Separation of Concerns**: API contracts separate from internal models
- **Validation**: Automatic input validation with detailed error messages
- **Consistency**: Standardized API responses across all endpoints
- **Maintainability**: Easy to modify API contracts without affecting business logic
- **Testing**: Simplified testing with clear input/output contracts

## Deployment

### Local Development
```bash
python run.py
```

### Production Deployment
```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 run:app

# Using Docker (if Dockerfile is provided)
docker build -t ai-case-study .
docker run -p 5000:5000 ai-case-study
```

## Configuration

### Environment Setup
1. Copy `env.example` to `.env` for local development
2. Set the required environment variables
3. For production deployment on Render, the `BASE_URL` will automatically be set to `https://storyboom.ai`

### Base URL Configuration
The application supports both local development and production deployment:
- **Local Development**: `BASE_URL=http://127.0.0.1:10000` (default)
- **Production**: `BASE_URL=https://storyboom.ai` (set by Render)
- **Custom Domain**: Set `BASE_URL` to your preferred domain

This configuration affects:
- Email verification links
- Client interview links
- CORS origins
- All generated URLs

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key | Yes |
| `JWT_SECRET_KEY` | JWT signing key | Yes |
| `DATABASE_URL` | Database connection string | No (defaults to SQLite) |
| `BASE_URL` | Application base URL | No (defaults to http://127.0.0.1:10000) |
| `OPENAI_API_KEY` | OpenAI API key | No (AI features disabled) |
| `HEYGEN_API_KEY` | HeyGen API key | No (video features disabled) |
| `PICTORY_CLIENT_ID` | Pictory client ID | No (Pictory features disabled) |
| `PICTORY_CLIENT_SECRET` | Pictory client secret | No |
| `PICTORY_USER_ID` | Pictory user ID | No |
| `WONDERCRAFT_API_KEY` | Wondercraft API key | No (podcast features disabled) |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 