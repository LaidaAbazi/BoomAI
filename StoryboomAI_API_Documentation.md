# StoryboomAI API Documentation

## Overview

StoryboomAI is an AI-powered voice interview platform that automates the creation of professional case studies and marketing content. The system conducts real-time voice interviews with both solution providers and clients, gathering insights about project goals, implementation, and outcomes. Using AI to guide conversations and extract key details, the platform automatically generates comprehensive case studies that combine both perspectives. The generated content includes editable text with AI-extracted names and company details, downloadable PDF and Word documents, and organizational features with customizable labels. While the core MVP focuses on case study creation, the platform is designed to expand into additional content generation including promotional videos, podcast episodes, and social media posts.

## API Overview

This document provides the complete API reference for the StoryboomAI frontend integration. The API uses HTTP REST endpoints with JSON request/response formats. All endpoints require authentication via session cookies except where noted.

**Base URL**: `http://127.0.0.1:10000` (development) or your production domain

## Authentication

### POST `/api/signup`
Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "first_name": "John",
  "last_name": "Doe"
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "message": "User created successfully",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_verified": false,
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

**Error Response (400 Bad Request):**
```json
{
  "success": false,
  "error": "validation_failed",
  "message": "Invalid email format",
  "details": {
    "email": ["Invalid email format"]
  }
}
```

### POST `/api/login`
Authenticate user and create session.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Login successful",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_verified": true,
    "last_login": "2024-01-15T10:30:00Z"
  }
}
```

**Error Response (401 Unauthorized):**
```json
{
  "success": false,
  "error": "invalid_credentials",
  "message": "Invalid email or password"
}
```

### POST `/api/logout`
End user session.

**Response (200 OK):**
```json
{
  "message": "Logout successful"
}
```

### GET `/api/user`
Get current user information.

**Response (200 OK):**
```json
{
  "user": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_verified": true,
    "created_at": "2024-01-15T10:30:00Z",
    "last_login": "2024-01-15T10:30:00Z"
  }
}
```

## Dashboard Management

### GET `/api/case_studies`
Get all case studies for the current user.

**Query Parameters:**
- `label` (optional): Filter by label ID

**Response (200 OK):**
```json
{
  "success": true,
  "case_studies": [
    {
      "id": 1,
      "title": "Acme Corp x TechSolutions: Digital Transformation Success",
      "final_summary": "Acme Corporation partnered with TechSolutions to implement...",
      "solution_provider_summary": "TechSolutions provided comprehensive digital transformation...",
      "client_summary": "Acme Corp experienced significant improvements in efficiency...",
      "client_link_url": "http://127.0.0.1:10000/client/abc123-def456",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T11:45:00Z",
      "video_status": "completed",
      "pictory_video_status": "pending",
      "podcast_status": "not_started",
      "labels": [
        {
          "id": 1,
          "name": "Digital Transformation",
          "color": "#FAD0D0"
        },
        {
          "id": 2,
          "name": "Success Stories",
          "color": "#F7B7B7"
        }
      ],
      "video_url": "https://example.com/video.mp4",
      "video_id": "vid_123456",
      "video_created_at": "2024-01-15T12:00:00Z",
      "pictory_video_url": null,
      "pictory_storyboard_id": null,
      "pictory_render_id": null,
      "pictory_video_created_at": null,
      "podcast_url": null,
      "podcast_job_id": null,
      "podcast_script": null,
      "podcast_created_at": null,
      "linkedin_post": null
    }
  ]
}
```

### GET `/api/labels`
Get all labels for the current user.

**Response (200 OK):**
```json
{
  "success": true,
  "labels": [
    {
      "id": 1,
      "name": "Digital Transformation",
      "color": "#FAD0D0"
    },
    {
      "id": 2,
      "name": "Success Stories",
      "color": "#F7B7B7"
    },
    {
      "id": 3,
      "name": "Enterprise",
      "color": "#F9C3B9"
    }
  ]
}
```

### POST `/api/labels`
Create a new label.

**Request Body:**
```json
{
  "name": "New Label"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "label": {
    "id": 4,
    "name": "New Label",
    "color": "#FAD1C2"
  }
}
```

### PATCH `/api/labels/{label_id}`
Rename a label.

**Request Body:**
```json
{
  "name": "Updated Label Name"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "label": {
    "id": 4,
    "name": "Updated Label Name",
    "color": "#FAD0D0"
  }
}
```

### DELETE `/api/labels/{label_id}`
Delete a label.

**Response (200 OK):**
```json
{
  "success": true
}
```

### GET `/api/color-palette`
Get information about the color palette used for labels.

**Response (200 OK):**
```json
{
  "success": true,
  "palette": {
    "total_colors": 30,
    "description": "Pastel Rainbow Palette - Ordered red → orange → yellow → green → blue → indigo → violet",
    "colors": [
      "#FAD0D0", "#F7B7B7", "#F9C3B9", "#FAD1C2", "#FCD6B5",
      "#FDE0B2", "#FEE9B8", "#FFF1C1", "#FFF5CC", "#FFF7D6",
      "#FFF9E0", "#FFFBEA", "#EAF8CF", "#DFF5D2", "#D2F0DA",
      "#C8EEDD", "#CDEDEA", "#CBEFF2", "#CFEAF7", "#D4EEFF",
      "#DAF0FF", "#E0F2FF", "#DAD9FF", "#D7D1FF", "#D9C9FF",
      "#E0CCFF", "#E8C7FF", "#F0C8F9", "#F6C7EE", "#FAD0F0"
    ]
  }
}
```

### POST `/api/case_studies/{case_study_id}/labels`
Add labels to a case study.

**Request Body:**
```json
{
  "label_ids": [1, 2],
  "label_names": ["New Label"]
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "labels": [
    {
      "id": 1,
      "name": "Digital Transformation",
      "color": "#FAD0D0"
    },
    {
      "id": 2,
      "name": "Success Stories",
      "color": "#F7B7B7"
    },
    {
      "id": 5,
      "name": "New Label",
      "color": "#F9C3B9"
    }
  ]
}
```

### DELETE `/api/case_studies/{case_study_id}/labels/{label_id}`
Remove a label from a case study.

**Response (200 OK):**
```json
{
  "success": true,
  "labels": [
    {
      "id": 1,
      "name": "Digital Transformation",
      "color": "#FAD0D0"
    },
    {
      "id": 2,
      "name": "Success Stories",
      "color": "#F7B7B7"
    }
  ]
}
```

## Real-time Interview Management

### GET `/session`
Create OpenAI realtime session for voice interviews.

**Response (200 OK):**
```json
{
  "id": "session_abc123def456",
  "model": "gpt-4o-realtime-preview-2024-12-17",
  "voice": "coral",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### POST `/save_transcript`
Save provider interview transcript.

**Query Parameters:**
- `provider_session_id`: Session ID for the provider interview

**Request Body:**
```json
[
  {
    "speaker": "ai",
    "text": "Hello, I'm here to help you create a case study about your project."
  },
  {
    "speaker": "user",
    "text": "Thank you. We recently completed a digital transformation project."
  },
  {
    "speaker": "ai",
    "text": "That sounds interesting. Can you tell me more about the project?"
  }
]
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Transcript saved to DB"
}
```

### POST `/api/save_provider_summary`
Save provider interview summary.

**Request Body:**
```json
{
  "case_study_id": 1,
  "summary": "TechSolutions provided comprehensive digital transformation services to Acme Corporation, including cloud migration, process automation, and employee training. The project resulted in 40% efficiency improvements and $2M annual cost savings."
}
```

**Response (200 OK):**
```json
{
  "case_study_id": 1,
  "status": "success"
}
```

### POST `/save_client_transcript`
Save client interview transcript.

**Query Parameters:**
- `token`: Client interview token

**Request Body:**
```json
[
  {
    "speaker": "ai",
    "text": "Hello, I'd like to ask you some questions about your experience with the project."
  },
  {
    "speaker": "user",
    "text": "Sure, I'm happy to share our experience."
  }
]
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Client transcript saved",
  "session_id": "client_session_abc123"
}
```

### POST `/api/generate_client_summary`
Generate summary from client interview transcript.

**Request Body:**
```json
{
  "transcript": "AI: Hello, I'd like to ask you some questions about your experience with the project.\nUSER: Sure, I'm happy to share our experience.\nAI: What were the main challenges you faced?\nUSER: The main challenge was getting all departments on board with the new processes.",
  "token": "abc123-def456"
}
```

**Response (200 OK):**
```json
{
  "client_summary": "Acme Corporation's main challenge was achieving organizational buy-in across all departments for the new digital processes. The client emphasized the importance of change management and communication in ensuring successful adoption.",
  "status": "success"
}
```

### POST `/generate_summary`
Generate summary from transcript.

**Request Body:**
```json
{
  "transcript": "AI: Hello, I'm here to help you create a case study about your project.\nUSER: Thank you. We recently completed a digital transformation project.\nAI: That sounds interesting. Can you tell me more about the project?\nUSER: We worked with TechSolutions to migrate our systems to the cloud and automate our processes."
}
```

**Response (200 OK):**
```json
{
  "summary": "TechSolutions provided comprehensive digital transformation services to Acme Corporation, including cloud migration, process automation, and employee training. The project resulted in 40% efficiency improvements and $2M annual cost savings.",
  "status": "success"
}
```

## Final Story Management

### POST `/api/generate_full_case_study`
Generate the complete final case study.

**Request Body:**
```json
{
  "case_study_id": 1
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "text": "Acme Corporation x TechSolutions: Digital Transformation Success\n\nExecutive Summary\nAcme Corporation, a leading manufacturing company, partnered with TechSolutions to implement a comprehensive digital transformation initiative...",
  "pdf_url": "/download/final_case_study_20240115_104500.pdf"
}
```

### POST `/extract_names`
Extract names from case study text for editable links.

**Request Body:**
```json
{
  "summary": "Acme Corporation partnered with TechSolutions to implement a comprehensive digital transformation initiative that resulted in significant operational improvements."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "names": {
    "lead_entity": "Acme Corporation",
    "partner_entity": "TechSolutions",
    "project_title": "Digital Transformation Initiative"
  },
  "method": "llm"
}
```

### POST `/api/extract_names`
Extract names from case study text (alternative endpoint).

**Request Body:**
```json
{
  "case_study_text": "Acme Corporation partnered with TechSolutions to implement a comprehensive digital transformation initiative that resulted in significant operational improvements."
}
```

**Response (200 OK):**
```json
{
  "lead_entity": "Acme Corporation",
  "partner_entity": "TechSolutions",
  "project_title": "Digital Transformation Initiative"
}
```

### POST `/api/save_final_summary`
Save final summary and update case study title.

**Request Body:**
```json
{
  "case_study_id": 1,
  "final_summary": "Acme Corporation x TechSolutions: Digital Transformation Success\n\nExecutive Summary\nAcme Corporation, a leading manufacturing company, partnered with TechSolutions to implement a comprehensive digital transformation initiative..."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Final summary and title updated",
  "names": {
    "lead_entity": "Acme Corporation",
    "partner_entity": "TechSolutions",
    "project_title": "Digital Transformation Success"
  },
  "case_study_id": 1
}
```

### POST `/api/generate_pdf`
Generate PDF from existing final summary.

**Request Body:**
```json
{
  "case_study_id": 1
}
```

**Response:** Returns PDF file directly with filename based on case study title.

## Client Interview Link Generation

### POST `/generate_client_interview_link`
Generate client interview link.

**Request Body:**
```json
{
  "case_study_id": 1
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "interview_link": "http://127.0.0.1:10000/client/abc123-def456"
}
```

**Error Response (400 Bad Request):**
```json
{
  "status": "error",
  "message": "Final summary is required to generate client interview link. Please complete the final story first."
}
```

### GET `/get_provider_transcript`
Get provider transcript for client interview.

**Query Parameters:**
- `token`: Client interview token

**Response (200 OK):**
```json
{
  "status": "success",
  "transcript": "AI: Hello, I'm here to help you create a case study about your project.\nUSER: Thank you. We recently completed a digital transformation project.\nAI: That sounds interesting. Can you tell me more about the project?\nUSER: We worked with TechSolutions to migrate our systems to the cloud and automate our processes."
}
```

### POST `/api/extract_interviewee_name`
Extract interviewee name from transcript.

**Request Body:**
```json
{
  "transcript": "AI: Hello, I'd like to ask you some questions about your experience with the project.\nUSER: Sure, my name is John Smith and I'm happy to share our experience."
}
```

**Response (200 OK):**
```json
{
  "status": "success",
  "name": "John Smith",
  "method": "LLM"
}
```

## File Downloads

### GET `/download/{filename}`
Download generated PDF file.

**Response:** Returns PDF file directly.

### POST `/api/save_as_word`
Save case study as Word document.

**Request Body:**
```json
{
  "case_study_id": 1
}
```

**Response:** Returns Word document file directly with filename based on case study title.

## Error Responses

All endpoints may return the following error responses:

**400 Bad Request:**
```json
{
  "status": "error",
  "message": "Missing required field"
}
```

**401 Unauthorized:**
```json
{
  "success": false,
  "error": "not_authenticated",
  "message": "Authentication required"
}
```

**404 Not Found:**
```json
{
  "status": "error",
  "message": "Resource not found"
}
```

**500 Internal Server Error:**
```json
{
  "status": "error",
  "message": "Internal server error"
}
```

## Real-time Communication

The voice interviews use **WebRTC data channels** combined with HTTP REST API calls to OpenAI's real-time API via SDP (Session Description Protocol), not WebSockets. The frontend should:

1. Call `/session` to create an OpenAI realtime session
2. Use WebRTC to establish the data channel connection
3. Send audio/video streams through the WebRTC connection
4. Use the REST endpoints to save transcripts and summaries

## Notes

- All timestamps are in ISO 8601 format (UTC)
- File downloads return the actual file content, not JSON
- Authentication is handled via session cookies
- Client interview endpoints don't require authentication (they use tokens)
- The API supports both label IDs and label names for flexibility 