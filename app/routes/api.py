from flask import Blueprint, request, jsonify
from app.models import db, Feedback, CaseStudy
from app.utils.auth_helpers import get_current_user_id, login_required
from app.services.feedback_service import FeedbackService
import uuid
from datetime import datetime
from flasgger import swag_from

bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize feedback sessions dictionary
feedback_sessions = {}

@bp.route('/feedback/start', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Feedback'],
    'summary': 'Start feedback session',
    'description': 'Initialize a new feedback collection session',
    'responses': {
        200: {
            'description': 'Feedback session started',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'session_id': {'type': 'string'},
                            'status': {'type': 'string'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'}
    }
})
def start_feedback_session():
    """Start a new feedback session"""
    try:
        user_id = get_current_user_id()
        session_id = str(uuid.uuid4())
        
        feedback_sessions[session_id] = {
            'user_id': user_id,
            'started_at': datetime.utcnow()
        }
        
        return jsonify({
            'session_id': session_id,
            'status': 'started'
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/feedback/submit', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Feedback'],
    'summary': 'Submit feedback',
    'description': 'Submit user feedback with optional rating',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['content'],
                    'properties': {
                        'content': {
                            'type': 'string',
                            'description': 'Feedback content'
                        },
                        'rating': {
                            'type': 'integer',
                            'minimum': 1,
                            'maximum': 5,
                            'description': 'Optional rating (1-5)'
                        },
                        'feedback_type': {
                            'type': 'string',
                            'default': 'general',
                            'description': 'Type of feedback'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Feedback submitted successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'message': {'type': 'string'},
                            'feedback_id': {'type': 'integer'},
                            'feedback_summary': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Bad Request'},
        401: {'description': 'Not authenticated'}
    }
})
def submit_feedback():
    """Submit user feedback"""
    try:
        data = request.get_json()
        content = data.get('content', '').strip()
        rating = data.get('rating')
        feedback_type = data.get('feedback_type', 'general')
        
        if not content:
            return jsonify({"error": "Feedback content is required"}), 400
        
        user_id = get_current_user_id()
        
        # Create feedback record
        feedback = Feedback(
            user_id=user_id,
            content=content,
            rating=rating,
            feedback_type=feedback_type
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        # Generate feedback summary using AI
        feedback_service = FeedbackService()
        summary = feedback_service.analyze_single_feedback(content, rating, feedback_type)
        
        # Update feedback with summary
        feedback.feedback_summary = summary
        db.session.commit()
        
        return jsonify({
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id,
            'feedback_summary': summary
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route('/feedback/history', methods=['GET'])
@login_required
@swag_from({
    'tags': ['Feedback'],
    'summary': 'Get feedback history',
    'description': 'Retrieve feedback history for the current user',
    'responses': {
        200: {
            'description': 'Feedback history retrieved',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'feedbacks': {
                                'type': 'array',
                                'items': {'$ref': '#/definitions/Feedback'}
                            }
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'}
    }
})
def get_feedback_history():
    """Get feedback history for the current user"""
    try:
        user_id = get_current_user_id()
        feedbacks = Feedback.query.filter_by(user_id=user_id).order_by(Feedback.created_at.desc()).all()
        
        feedback_data = [feedback.to_dict() for feedback in feedbacks]
        
        return jsonify({
            'feedbacks': feedback_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/feedback/all', methods=['GET'])
@login_required
@swag_from({
    'tags': ['Feedback'],
    'summary': 'Get all feedback',
    'description': 'Get all feedback for analysis (admin/closed beta analysis)',
    'responses': {
        200: {
            'description': 'All feedback retrieved',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'feedbacks': {
                                'type': 'array',
                                'items': {'$ref': '#/definitions/Feedback'}
                            },
                            'total_count': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'}
    }
})
def get_all_feedback():
    """Get all feedback for analysis (admin/closed beta analysis)"""
    try:
        # Get all feedback ordered by creation date
        feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
        
        feedback_data = [feedback.to_dict() for feedback in feedbacks]
        
        return jsonify({
            'feedbacks': feedback_data,
            'total_count': len(feedbacks)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/feedback/analyze', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Feedback'],
    'summary': 'Analyze all feedback',
    'description': 'Generate comprehensive analysis of all feedback',
    'responses': {
        200: {
            'description': 'Feedback analysis completed',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'comprehensive_summary': {'type': 'string'},
                            'statistics': {'type': 'object'},
                            'total_feedback_analyzed': {'type': 'integer'},
                            'generated_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        },
        404: {'description': 'No feedback available'},
        401: {'description': 'Not authenticated'}
    }
})
def analyze_feedback():
    """Generate comprehensive feedback analysis and summary"""
    try:
        feedback_service = FeedbackService()
        
        # Get all feedback
        all_feedbacks = Feedback.query.order_by(Feedback.created_at.desc()).all()
        
        if not all_feedbacks:
            return jsonify({
                "error": "No feedback available for analysis"
            }), 404
        
        # Generate comprehensive summary
        comprehensive_summary = feedback_service.generate_comprehensive_feedback_summary(all_feedbacks)
        
        # Get statistics
        statistics = feedback_service.get_feedback_statistics(all_feedbacks)
        
        return jsonify({
            'comprehensive_summary': comprehensive_summary,
            'statistics': statistics,
            'total_feedback_analyzed': len(all_feedbacks),
            'generated_at': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/feedback/update-summary/<int:feedback_id>', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Feedback'],
    'summary': 'Update feedback summary',
    'description': 'Update the summary for a specific feedback entry',
    'parameters': [
        {
            'name': 'feedback_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'}
        }
    ],
    'responses': {
        200: {
            'description': 'Feedback summary updated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'message': {'type': 'string'},
                            'feedback_summary': {'type': 'string'}
                        }
                    }
                }
            }
        },
        404: {'description': 'Feedback not found'},
        401: {'description': 'Not authenticated'}
    }
})
def update_feedback_summary(feedback_id):
    """Update the summary for a specific feedback entry"""
    try:
        feedback_service = FeedbackService()
        success = feedback_service.update_feedback_summary(feedback_id)
        
        if success:
            feedback = Feedback.query.get(feedback_id)
            return jsonify({
                'message': 'Feedback summary updated successfully',
                'feedback_summary': feedback.feedback_summary
            })
        else:
            return jsonify({"error": "Feedback not found or update failed"}), 404
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route("/save_final_summary", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Save final summary',
    'description': 'Save final summary to case study',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id', 'final_summary'],
                    'properties': {
                        'case_study_id': {
                            'type': 'integer',
                            'description': 'ID of the case study'
                        },
                        'final_summary': {
                            'type': 'string',
                            'description': 'Final case study summary text'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Final summary saved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing required data'},
        404: {'description': 'Case study not found'},
        401: {'description': 'Not authenticated'}
    }
})
def save_final_summary():
    """Save final summary to case study"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        final_summary = data.get('final_summary', '')
        
        if not case_study_id or not final_summary:
            return jsonify({"error": "Missing case_study_id or final_summary"}), 400
        
        user_id = get_current_user_id()
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Update case study with final summary
        case_study.final_summary = final_summary
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Final summary saved successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route("/save_as_word", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Summary'],
    'summary': 'Save as Word document',
    'description': 'Save case study as Word document',
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
                            'description': 'ID of the case study'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Word document generated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'word_path': {'type': 'string'},
                            'status': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing case study ID'},
        404: {'description': 'Case study not found'},
        401: {'description': 'Not authenticated'}
    }
})
def save_as_word():
    """Save case study as Word document"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        
        if not case_study_id:
            return jsonify({"error": "Missing case_study_id"}), 400
        
        user_id = get_current_user_id()
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Generate Word document using case study service
        from app.services.case_study_service import CaseStudyService
        case_study_service = CaseStudyService()
        word_path = case_study_service.generate_word_document(case_study)
        
        return jsonify({
            "word_path": word_path,
            "status": "success"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500 