from flask import Blueprint, request, jsonify, send_file, Response
import requests
import os
from datetime import datetime, UTC
from app.models import db, CaseStudy
from app.utils.auth_helpers import get_current_user_id, login_required
from app.services.ai_service import AIService
from app.services.media_service import MediaService
from app.utils.error_messages import UserFriendlyErrors
from flasgger import swag_from

bp = Blueprint('media', __name__, url_prefix='/api')

# API Configuration
HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_API_BASE_URL = "https://api.heygen.com/v2"
HEYGEN_AVATAR_ID = "Giulia_sitting_sofa_front"
HEYGEN_NEWSFLASH_AVATAR_ID = "Annie_Casual_Standing_Front_2_public"
HEYGEN_VOICE_ID = "4754e1ec667544b0bd18cdf4bec7d6a7"

PICTORY_CLIENT_ID = os.getenv("PICTORY_CLIENT_ID")
PICTORY_CLIENT_SECRET = os.getenv("PICTORY_CLIENT_SECRET")
PICTORY_USER_ID = os.getenv("PICTORY_USER_ID")
PICTORY_API_BASE_URL = "https://api.pictory.ai"

WONDERCRAFT_API_KEY = os.getenv("WONDERCRAFT_API_KEY")
WONDERCRAFT_API_BASE_URL = "https://api.wondercraft.ai/v1"

@bp.route("/generate_newsflash_video", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Media'],
    'summary': 'Generate newsflash video',
    'description': 'Generate a 30-second newsflash video using HeyGen API',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id'],
                    'properties': {
                        'case_study_id': {'type': 'integer'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Newsflash video generation started',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'video_id': {'type': 'string'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Bad Request'},
        401: {'description': 'Not authenticated'},
        404: {'description': 'Case study not found'}
    }
})
def generate_newsflash_video():
    """Generate 30-second newsflash video using HeyGen API"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        
        if not case_study_id:
            error_response = UserFriendlyErrors.get_case_study_error("missing_data")
            return jsonify(error_response), 400
            
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            error_response = UserFriendlyErrors.get_case_study_error("not_found")
            return jsonify(error_response), 404
            
        if not case_study.final_summary:
            error_response = UserFriendlyErrors.get_case_study_error("missing_data")
            return jsonify(error_response), 400

        # Prevent multiple newsflash video generations for the same case study
        if case_study.newsflash_video_id:
            error_response = UserFriendlyErrors.get_media_error("video_generation_failed")
            return jsonify(error_response), 400

        # Generate optimized input text for HeyGen (30-second newsflash video)
        ai_service = AIService()
        input_text = ai_service.generate_heygen_newsflash_video_text(case_study.final_summary)
        if not input_text:
            error_response = UserFriendlyErrors.get_media_error("video_generation_failed")
            return jsonify(error_response), 500

        # Prepare the request to HeyGen API V2
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": HEYGEN_API_KEY
        }
        
        payload = {
            "caption": False,
            "dimension": {
                "width": 1280,
                "height": 720
            },
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": HEYGEN_NEWSFLASH_AVATAR_ID,
                        "scale": 1.0,
                        "avatar_style": "normal",
                        "offset": {
                            "x": 0.0,
                            "y": 0.0
                        }
                    },
                    "voice": {
                        "type": "text",
                        "voice_id": HEYGEN_VOICE_ID,
                        "input_text": input_text,
                        "speed": 1.0,
                        "pitch": 35,
                        "emotion": "Excited"
                    },
                    "background": {
                        "type": "image",
                        "url": "https://i.postimg.cc/g0tpPn1y/background3.jpg"
                    }
                }
            ]
        }

        response = requests.post(
            f"{HEYGEN_API_BASE_URL}/video/generate",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            video_data = response.json()
            video_id = video_data.get('data', {}).get('video_id')
            
            if not video_id:
                return jsonify({
                    "status": "error",
                    "error": "No video ID received from HeyGen API"
                }), 500
            
            # Update case study with newsflash video information
            case_study.newsflash_video_id = video_id
            case_study.newsflash_video_status = 'processing'
            case_study.newsflash_video_created_at = datetime.now(UTC)
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "video_id": video_id,
                "message": "Newsflash video generation started"
            })
        else:
            error_response = UserFriendlyErrors.get_media_error("api_connection_failed")
            return jsonify(error_response), response.status_code

    except Exception as e:
        db.session.rollback()
        error_response = UserFriendlyErrors.get_general_error("server_error", e)
        return jsonify(error_response), 500

@bp.route("/generate_video", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Media'],
    'summary': 'Generate video',
    'description': 'Generate a video using HeyGen API',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id'],
                    'properties': {
                        'case_study_id': {'type': 'integer'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Video generation started',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'video_id': {'type': 'string'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Bad Request'},
        401: {'description': 'Not authenticated'},
        404: {'description': 'Case study not found'}
    }
})
def generate_video():
    """Generate video using HeyGen API"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        
        if not case_study_id:
            error_response = UserFriendlyErrors.get_case_study_error("missing_data")
            return jsonify(error_response), 400
            
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            error_response = UserFriendlyErrors.get_case_study_error("not_found")
            return jsonify(error_response), 404
            
        if not case_study.final_summary:
            error_response = UserFriendlyErrors.get_case_study_error("missing_data")
            return jsonify(error_response), 400

        # Prevent multiple video generations for the same case study
        if case_study.video_id:
            error_response = UserFriendlyErrors.get_media_error("video_generation_failed")
            return jsonify(error_response), 400

        # Generate optimized input text for HeyGen (1-minute video)
        ai_service = AIService()
        input_text = ai_service.generate_heygen_1min_video_text(case_study.final_summary)
        if not input_text:
            error_response = UserFriendlyErrors.get_media_error("video_generation_failed")
            return jsonify(error_response), 500

        # Prepare the request to HeyGen API V2
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "x-api-key": HEYGEN_API_KEY
        }
        
        payload = {
            "caption": False,
            "dimension": {
                "width": 1280,
                "height": 720
            },
            "video_inputs": [
                {
                    "character": {
                        "type": "avatar",
                        "avatar_id": HEYGEN_AVATAR_ID,
                        "scale": 1.0,
                        "avatar_style": "normal",
                        "offset": {
                            "x": 0.0,
                            "y": 0.0
                        }
                    },
                    "voice": {
                        "type": "text",
                        "voice_id": HEYGEN_VOICE_ID,
                        "input_text": input_text,
                        "speed": 1.0,
                        "pitch": 35,
                        "emotion": "Excited"
                    },
                    "background": {
                        "type": "image",
                        "url": "https://i.postimg.cc/g0tpPn1y/background3.jpg"
                    }
                }
            ]
        }

        response = requests.post(
            f"{HEYGEN_API_BASE_URL}/video/generate",
            headers=headers,
            json=payload
        )

        if response.status_code == 200:
            video_data = response.json()
            video_id = video_data.get('data', {}).get('video_id')
            
            if not video_id:
                return jsonify({
                    "status": "error",
                    "error": "No video ID received from HeyGen API"
                }), 500
            
            # Update case study with video information
            case_study.video_id = video_id
            case_study.video_status = 'processing'
            case_study.video_created_at = datetime.now(UTC)
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "video_id": video_id,
                "message": "Video generation started"
            })
        else:
            error_response = UserFriendlyErrors.get_media_error("api_connection_failed")
            return jsonify(error_response), response.status_code

    except Exception as e:
        db.session.rollback()
        error_response = UserFriendlyErrors.get_general_error("server_error", e)
        return jsonify(error_response), 500

@bp.route("/video_status/<video_id>", methods=["GET"])
@login_required
@swag_from({
    'tags': ['Media'],
    'summary': 'Check video generation status',
    'description': 'Check the status of a video generation job',
    'parameters': [
        {
            'name': 'video_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'},
            'description': 'Video generation job ID'
        }
    ],
    'responses': {
        200: {
            'description': 'Video status retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {
                                'type': 'string',
                                'enum': ['completed', 'processing', 'pending', 'failed', 'not_ready'],
                                'description': 'Current status of the video'
                            },
                            'video_url': {
                                'type': 'string',
                                'description': 'URL of the completed video (if status is completed)'
                            },
                            'message': {
                                'type': 'string',
                                'description': 'Status message'
                            }
                        }
                    }
                }
            }
        },
        400: {'description': 'Video ID is required'},
        500: {'description': 'Internal server error or API error'}
    }
})
def check_video_status(video_id):
    """Check video generation status"""
    if not video_id:
        return jsonify({"error": "Video ID is required"}), 400
        
    try:
        headers = {
            "accept": "application/json",
            "x-api-key": HEYGEN_API_KEY
        }
        
        # Use the correct v1 endpoint for status check
        response = requests.get(
            f"https://api.heygen.com/v1/video_status.get",
            headers=headers,
            params={"video_id": video_id}
        )
        
        if response.status_code == 404:
            return jsonify({"status": "not_ready", "message": "Video not ready yet"}), 200
        
        if response.status_code != 200:
            error_msg = f"HeyGen API error: {response.text}"
            return jsonify({"error": error_msg}), 500
            
        video_data = response.json()
        
        # Update case study with video status and URL if completed
        # Check both regular video and newsflash video
        case_study = CaseStudy.query.filter_by(video_id=video_id).first()
        is_newsflash = False
        
        if not case_study:
            case_study = CaseStudy.query.filter_by(newsflash_video_id=video_id).first()
            is_newsflash = True
        
        if case_study:
            status = video_data.get("data", {}).get("status")
            
            if is_newsflash:
                case_study.newsflash_video_status = status
            else:
                case_study.video_status = status
            
            if status == "completed":
                video_url = video_data.get("data", {}).get("video_url")
                if video_url:
                    if is_newsflash:
                        case_study.newsflash_video_url = video_url
                    else:
                        case_study.video_url = video_url
                    db.session.commit()
                    return jsonify({
                        "status": "completed",
                        "video_url": video_url
                    })
                else:
                    db.session.commit()
                    return jsonify({
                        "status": "completed",
                        "message": "Video completed but URL not available yet"
                    })
            elif status == "failed":
                error = video_data.get("data", {}).get("error")
                db.session.commit()
                return jsonify({
                    "status": "failed",
                    "message": f"Video generation failed: {error}" if error else "Video generation failed"
                })
            elif status in ["processing", "pending"]:
                db.session.commit()
                return jsonify({
                    "status": status,
                    "message": "Video is being processed"
                })
            else:
                db.session.commit()
                return jsonify({
                    "status": status,
                    "message": f"Video is {status}"
                })
        
        return jsonify(video_data)
            
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to connect to HeyGen API: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@bp.route("/generate_pictory_video", methods=["POST"])
@login_required
def generate_pictory_video():
    """Generate Pictory video"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        
        if not case_study_id:
            return jsonify({"error": "Case study ID is required"}), 400
            
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
            
        if not case_study.final_summary:
            return jsonify({"error": "Final summary is required for video generation"}), 400

        # Prevent multiple Pictory video generations for the same case study
        if case_study.pictory_storyboard_id:
            return jsonify({"error": "A Pictory video has already been generated for this case study."}), 400

        # Get Pictory access token
        media_service = MediaService()
        token = media_service.get_pictory_access_token()
        if not token:
            return jsonify({"error": "Failed to get Pictory access token"}), 500

        # Generate scene-based text for Pictory
        ai_service = AIService()
        scenes = ai_service.generate_pictory_scenes_text(case_study.final_summary)
        if not scenes:
            return jsonify({"error": "Failed to generate scenes text"}), 500

        # Create video name
        video_name = f"Case Study {case_study.id} - Short Form Video"

        # Create storyboard
        storyboard_job_id = media_service.create_pictory_storyboard(token, scenes, video_name)
        if not storyboard_job_id:
            return jsonify({"error": "Failed to create Pictory storyboard"}), 500

        # Update case study with Pictory information
        case_study.pictory_storyboard_id = storyboard_job_id
        case_study.pictory_video_status = 'storyboard_processing'
        case_study.pictory_video_created_at = datetime.now(UTC)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "storyboard_job_id": storyboard_job_id,
            "message": "Pictory video storyboard creation started"
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500

@bp.route("/pictory_video_status/<storyboard_job_id>", methods=["GET"])
@login_required
@swag_from({
    'tags': ['Media'],
    'summary': 'Check Pictory video status',
    'description': 'Check the status of a Pictory video generation job',
    'parameters': [
        {
            'name': 'storyboard_job_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'},
            'description': 'Pictory storyboard job ID'
        }
    ],
    'responses': {
        200: {
            'description': 'Pictory video status retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {
                                'type': 'string',
                                'enum': ['storyboard_processing', 'completed', 'rendering', 'failed', 'unknown'],
                                'description': 'Current status of the Pictory video'
                            },
                            'video_url': {
                                'type': 'string',
                                'description': 'URL of the completed video (if status is completed)'
                            },
                            'render_job_id': {
                                'type': 'string',
                                'description': 'Render job ID (if rendering)'
                            },
                            'message': {
                                'type': 'string',
                                'description': 'Status message'
                            }
                        }
                    }
                }
            }
        },
        400: {'description': 'Storyboard job ID is required'},
        500: {'description': 'Internal server error or API error'}
    }
})
def check_pictory_video_status(storyboard_job_id):
    """Check Pictory video status"""
    if not storyboard_job_id:
        return jsonify({"error": "Storyboard job ID is required"}), 400
        
    try:
        media_service = MediaService()
        token = media_service.get_pictory_access_token()
        if not token:
            return jsonify({"error": "Failed to get Pictory access token"}), 500

        # Check storyboard status
        storyboard_status = media_service.check_pictory_job_status(token, storyboard_job_id)
        if not storyboard_status:
            return jsonify({"error": "Failed to check storyboard status"}), 500

        status = storyboard_status.get("status", "unknown")
        
        # If storyboard is completed, start rendering
        if status == "completed" and storyboard_status.get("renderParams"):
            case_study = CaseStudy.query.filter_by(pictory_storyboard_id=storyboard_job_id).first()
            if case_study and not case_study.pictory_render_id:
                # Start rendering
                render_job_id = media_service.render_pictory_video(token, storyboard_job_id)
                if render_job_id:
                    case_study.pictory_render_id = render_job_id
                    case_study.pictory_video_status = 'rendering'
                    db.session.commit()
                    
                    return jsonify({
                        "status": "rendering",
                        "render_job_id": render_job_id,
                        "message": "Video rendering started"
                    })
                else:
                    return jsonify({
                        "status": "error",
                        "error": "Failed to start video rendering"
                    }), 500
        
        # Check if storyboard status already contains video URL (completed video)
        if status == "completed" and storyboard_status.get("videoURL"):
            case_study = CaseStudy.query.filter_by(pictory_storyboard_id=storyboard_job_id).first()
            if case_study:
                video_url = storyboard_status.get("videoURL")
                case_study.pictory_video_url = video_url
                case_study.pictory_video_status = 'completed'
                db.session.commit()
                
                return jsonify({
                    "status": "completed",
                    "video_url": video_url,
                    "message": "Video is ready"
                })
        
        # If we have a render job, check its status
        case_study = CaseStudy.query.filter_by(pictory_storyboard_id=storyboard_job_id).first()
        if case_study and case_study.pictory_render_id:
            render_status = media_service.check_pictory_job_status(token, case_study.pictory_render_id)
            if render_status:
                render_status_value = render_status.get("status", "unknown")
                
                if render_status_value == "completed":
                    video_url = (
                        render_status.get("videoURL") or
                        render_status.get("videoUrl") or
                        render_status.get("output", {}).get("videoUrl") or
                        render_status.get("output", {}).get("videoURL")
                    )
                    if video_url:
                        case_study.pictory_video_url = video_url
                        case_study.pictory_video_status = 'completed'
                        db.session.commit()
                        
                        return jsonify({
                            "status": "completed",
                            "video_url": video_url,
                            "message": "Video is ready"
                        })
                    else:
                        return jsonify({
                            "status": "error",
                            "error": "Video completed but no URL found"
                        }), 500
                elif render_status_value == "failed":
                    case_study.pictory_video_status = 'failed'
                    db.session.commit()
                    
                    return jsonify({
                        "status": "failed",
                        "error": "Video rendering failed"
                    }), 500
                else:
                    return jsonify({
                        "status": "rendering",
                        "message": f"Video is {render_status_value}"
                    })
        
        # Return storyboard status
        return jsonify({
            "status": status,
            "message": f"Storyboard is {status}"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@bp.route("/generate_podcast", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Media'],
    'summary': 'Generate podcast',
    'description': 'Generate a podcast using Wondercraft API',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id'],
                    'properties': {
                        'case_study_id': {
                            'type': 'integer',
                            'description': 'ID of the case study to generate podcast from'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Podcast generation started successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'job_id': {'type': 'string'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Missing case study ID or no final summary available',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'error': {'type': 'string'}
                        }
                    }
                }
            }
        },
        404: {'description': 'Case study not found'},
        500: {
            'description': 'Internal server error or API configuration issue',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'error': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
})
def generate_podcast():
    """Generate podcast using Wondercraft API"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        
        if not case_study_id:
            return jsonify({"error": "Case study ID is required"}), 400
            
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
            
        if not case_study.final_summary:
            return jsonify({"error": "Final summary is required for podcast generation"}), 400

        if not WONDERCRAFT_API_KEY:
            return jsonify({"error": "Wondercraft API key not configured"}), 500

        # Clear any previous failed podcast data if this is a retry
        if case_study.podcast_status == 'failed':
            case_study.podcast_job_id = None
            case_study.podcast_url = None
            case_study.podcast_script = None
            case_study.podcast_status = None
            case_study.podcast_created_at = None
            db.session.commit()

        # Generate podcast prompt
        ai_service = AIService()
        podcast_prompt = ai_service.generate_podcast_prompt(case_study.final_summary)
        if not podcast_prompt:
            return jsonify({"error": "Failed to generate podcast prompt"}), 500

        # Prepare the request to Wondercraft API
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": WONDERCRAFT_API_KEY
        }
        
        payload = {
            "prompt": podcast_prompt,
            "voice_ids": [
                "5acfb17c-dd70-4af3-b17e-750a8a312ef8",
                "331fbe9e-8efb-48f2-99d2-e81f3f7ccf84"
            ]
        }
        
        response = requests.post(
            f"{WONDERCRAFT_API_BASE_URL}/podcast",
            headers=headers,
            json=payload,
            timeout=120  # Increased timeout to 2 minutes for podcast generation
        )

        if response.status_code == 200:
            podcast_data = response.json()
            job_id = podcast_data.get('job_id')
            
            if not job_id:
                return jsonify({
                    "status": "error",
                    "error": "No job ID received from Wondercraft API"
                }), 500
            
            # Update case study with podcast information
            case_study.podcast_job_id = job_id
            case_study.podcast_status = 'processing'
            case_study.podcast_created_at = datetime.now(UTC)
            case_study.podcast_audio_data = podcast_data.get('audio_data')
            case_study.podcast_audio_mime = podcast_data.get('audio_mime')
            case_study.podcast_audio_size = podcast_data.get('audio_size')
            db.session.commit()
            
            return jsonify({
                "status": "success",
                "job_id": job_id,
                "message": "Podcast generation started"
            })
        elif response.status_code == 422:
            try:
                error_data = response.json()
                error_message = "Validation error occurred"
                if 'detail' in error_data and isinstance(error_data['detail'], list):
                    for error in error_data['detail']:
                        if 'msg' in error:
                            if 'voice_ids' in error['msg'].lower() and 'unique' in error['msg'].lower():
                                error_message = "Voice IDs must be unique. Please check your voice configuration."
                            elif 'voice_ids' in error['msg'].lower() or 'music_ids' in error['msg'].lower():
                                error_message = "Invalid voice IDs or music IDs provided."
                            elif 'music_spec' in error['msg'].lower() or 'music_id' in error['msg'].lower():
                                error_message = "Music configuration error. Please try again without music settings."
                            else:
                                error_message = error['msg']
                        elif 'type' in error:
                            error_message = f"{error.get('type', 'Unknown')}: {error.get('msg', 'Validation failed')}"
                
                return jsonify({
                    "status": "error",
                    "error": error_message,
                    "details": error_data
                }), 422
            except Exception as e:
                return jsonify({
                    "status": "error",
                    "error": f"Validation Error: {response.text}"
                }), 422
        elif response.status_code == 429:
            return jsonify({
                "status": "error",
                "error": "Rate limit exceeded. Too many concurrent jobs (max 5). Please try again later."
            }), 429
        elif response.status_code == 400:
            return jsonify({
                "status": "error",
                "error": f"Bad request: {response.text}"
            }), 400
        else:
            error_message = f"Wondercraft API error (Status {response.status_code}): {response.text}"
            return jsonify({
                "status": "error",
                "error": error_message
            }), response.status_code

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "error": str(e)}), 500

@bp.route("/podcast_status/<job_id>", methods=["GET"])
@login_required
@swag_from({
    'tags': ['Media'],
    'summary': 'Check podcast generation status',
    'description': 'Check the status of a podcast generation job',
    'parameters': [
        {
            'name': 'job_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'},
            'description': 'Podcast generation job ID'
        }
    ],
    'responses': {
        200: {
            'description': 'Podcast status retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {
                                'type': 'string',
                                'enum': ['processing', 'completed', 'failed'],
                                'description': 'Current status of the podcast'
                            },
                            'audio_url': {
                                'type': 'string',
                                'description': 'URL of the completed podcast audio (if status is completed)'
                            },
                            'message': {
                                'type': 'string',
                                'description': 'Status message'
                            }
                        }
                    }
                }
            }
        },
        400: {'description': 'Job ID is required'},
        500: {'description': 'Internal server error or API error'}
    }
})
def check_podcast_status(job_id):
    """Check podcast generation status"""
    if not job_id:
        return jsonify({"error": "Job ID is required"}), 400
        
    try:
        headers = {
            "X-API-KEY": WONDERCRAFT_API_KEY
        }
        
        response = requests.get(
            f"{WONDERCRAFT_API_BASE_URL}/podcast/{job_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 404:
            print(f"🔍 DEBUG: Podcast not found: {response.text}")
            return jsonify({"status": "not_ready", "message": "Podcast not ready yet"}), 200
        
        if response.status_code != 200:
            print(f"🔍 DEBUG: Wondercraft API error: {response.text}")
            error_msg = f"Wondercraft API error: {response.text}"
            return jsonify({"error": error_msg}), 500
            
        podcast_data = response.json()
        
        # Update case study with podcast status and URL if completed
        case_study = CaseStudy.query.filter_by(podcast_job_id=job_id).first()
        if case_study:
            status = podcast_data.get('finished', False)
            error = podcast_data.get('error', False)
            url = podcast_data.get('url')
            script = podcast_data.get('script')
            
            if status and not error and url:
                # Podcast generation completed successfully
                case_study.podcast_status = 'completed'
                case_study.podcast_url = url
                case_study.podcast_script = script

                # Attempt to fetch and persist audio bytes
                try:
                    audio_resp = requests.get(url, timeout=60)
                    if audio_resp.status_code == 200 and audio_resp.content:
                        case_study.podcast_audio_data = audio_resp.content
                        case_study.podcast_audio_mime = audio_resp.headers.get('Content-Type', 'audio/mpeg')
                        case_study.podcast_audio_size = len(audio_resp.content)
                except Exception:
                    # If fetch fails, keep URL fallback
                    pass

                db.session.commit()
                
                return jsonify({
                    "status": "completed",
                    "url": url,
                    "script": script,
                    "message": "Podcast generation completed"
                })
        
        return jsonify(podcast_data)
            
    except requests.RequestException as e:
        return jsonify({"error": f"Failed to connect to Wondercraft API: {str(e)}"}), 500
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {str(e)}"}), 500

@bp.route("/podcast_audio/<int:case_study_id>", methods=["OPTIONS"])
def podcast_audio_options(case_study_id):
    """Handle CORS preflight requests for podcast audio."""
    response = jsonify({"status": "ok"})
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, HEAD, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Range, Content-Type'
    return response

@bp.route("/podcast_audio/<int:case_study_id>", methods=["GET"])
@swag_from({
    'tags': ['Media'],
    'summary': 'Get podcast audio file',
    'description': 'Serve podcast audio file for a case study. Automatically serves from database (permanent storage) if available, otherwise falls back to external URL. This endpoint handles CORS and streaming.',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'},
            'description': 'ID of the case study'
        }
    ],
    'responses': {
        200: {
            'description': 'Audio file served successfully',
            'content': {
                'audio/mpeg': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                },
                'audio/mp3': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            },
            'headers': {
                'X-Audio-Source': {
                    'description': 'Source of audio: "database" if served from DB (permanent), null if from URL (may expire)',
                    'schema': {'type': 'string'}
                },
                'Content-Length': {
                    'description': 'Size of audio file in bytes',
                    'schema': {'type': 'integer'}
                },
                'Content-Type': {
                    'description': 'MIME type of audio (usually audio/mpeg)',
                    'schema': {'type': 'string'}
                }
            }
        },
        404: {
            'description': 'Podcast not found for this case study',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'error': {'type': 'string'}
                        }
                    }
                }
            }
        },
        500: {
            'description': 'Failed to fetch audio file from external URL',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'error': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
})
def serve_podcast_audio(case_study_id):
    """Proxy endpoint to serve podcast audio files to avoid CORS issues."""
    try:
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        
        if not case_study:
            return jsonify({"error": "Podcast not found"}), 404

        # Serve from DB if stored
        if getattr(case_study, 'podcast_audio_data', None):
            return Response(
                case_study.podcast_audio_data,
                content_type=(case_study.podcast_audio_mime or 'audio/mpeg'),
                headers={
                    'Content-Length': str(case_study.podcast_audio_size or len(case_study.podcast_audio_data)),
                    'Accept-Ranges': 'bytes',
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                    'Access-Control-Allow-Headers': 'Range, Content-Type',
                    'Cache-Control': 'public, max-age=3600'
                }
            )
        
        if not case_study.podcast_url:
            return jsonify({"error": "Podcast not found"}), 404
        
        # Fetch the audio file from the external URL
        response = requests.get(case_study.podcast_url, stream=True, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"error": "Failed to fetch audio file"}), 500
        
        def generate():
            for chunk in response.iter_content(chunk_size=8192):
                yield chunk
        
        # Return the audio as a streaming response
        return Response(
            generate(),
            content_type=response.headers.get('Content-Type', 'audio/mpeg'),
            headers={
                'Content-Length': response.headers.get('Content-Length'),
                'Accept-Ranges': 'bytes',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, HEAD, OPTIONS',
                'Access-Control-Allow-Headers': 'Range, Content-Type',
                'Cache-Control': 'public, max-age=3600'
            }
        )
        
    except Exception as e:
        return jsonify({"error": "Internal server error"}), 500
        

@bp.route("/download/<filename>")
@swag_from({
    'tags': ['Files'],
    'summary': 'Download generated files',
    'description': 'Download generated PDF and Word files',
    'parameters': [
        {
            'name': 'filename',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'}
        }
    ],
    'responses': {
        200: {
            'description': 'File download',
            'content': {
                'application/pdf': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                },
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        404: {'description': 'File not found'}
    }
})
def download_file(filename):
    """Download generated PDF or Word file"""
    try:
        file_path = f"generated_pdfs/{filename}"
        print(f"🔍 DEBUG: Attempting to download file: {file_path}")
        print(f"🔍 DEBUG: File exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            return jsonify({"error": "File not found"}), 404
            
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        print(f"🔍 ERROR: Download failed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/generated_pdfs/<filename>')
@swag_from({
    'tags': ['Files'],
    'summary': 'Serve generated PDFs',
    'description': 'Serve generated PDF files',
    'parameters': [
        {
            'name': 'filename',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'}
        }
    ],
    'responses': {
        200: {
            'description': 'File served',
            'content': {
                'application/pdf': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        404: {'description': 'File not found'}
    }
})
def serve_generated_file(filename):
    """Serve generated files"""
    try:
        return send_file(f"generated_pdfs/{filename}")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/sentiment_chart/<int:case_study_id>')
@swag_from({
    'tags': ['Metadata'],
    'summary': 'Get sentiment chart',
    'description': 'Retrieve sentiment analysis chart for a case study',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'}
        }
    ],
    'responses': {
        200: {
            'description': 'Sentiment chart retrieved',
            'content': {
                'image/png': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        404: {'description': 'Sentiment chart not found'}
    }
})
def serve_sentiment_chart(case_study_id):
    """Serve sentiment chart image from database"""
    try:
        case_study = CaseStudy.query.get(case_study_id)
        if not case_study or not case_study.sentiment_chart_data:
            return jsonify({"error": "Sentiment chart not found"}), 404
        
        # Return the image data
        from flask import Response
        return Response(
            case_study.sentiment_chart_data,
            mimetype='image/png',
            headers={
                'Cache-Control': 'public, max-age=3600',
                'Content-Disposition': 'inline'
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500 
