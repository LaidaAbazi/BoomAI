from flask import Blueprint, request, jsonify, send_file, send_from_directory
import os
import json
import re
import uuid
import logging
from datetime import datetime, UTC, timezone
from fpdf import FPDF
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.models import db, CaseStudy, SolutionProviderInterview, ClientInterview, InviteToken, Label, StoryFeedback, User
from app.utils.auth_helpers import get_current_user_id, login_required, login_or_token_required, subscription_required, owner_required
from app.services.ai_service import AIService
from app.services.case_study_service import CaseStudyService
from app.utils.text_processing import clean_text, detect_language
from app.utils.language_utils import detect_and_normalize_language
from app.mappers.case_study_mapper import CaseStudyMapper
from io import BytesIO
from flasgger import swag_from

bp = Blueprint('case_studies', __name__, url_prefix='/api')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_PDFS_DIR = os.path.join(BASE_DIR, 'generated_pdfs')

@bp.route('/case_studies', methods=['GET'])
@login_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Get all case studies',
    'description': 'Retrieve all case studies for the current user',
    'parameters': [
        {
            'name': 'label',
            'in': 'query',
            'description': 'Filter by label ID',
            'schema': {'type': 'integer'}
        },
        {
            'name': 'creator_id',
            'in': 'query',
            'description': 'Filter by creator user ID',
            'schema': {'type': 'integer'}
        }
    ],
    'responses': {
        200: {
            'description': 'Case studies retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'case_studies': {
                                'type': 'array',
                                'items': {'$ref': '#/components/schemas/CaseStudy'}
                            }
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'}
    }
})
def get_case_studies():
    """Get all case studies for the current user"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        label_id = request.args.get('label', type=int)
        creator_id = request.args.get('creator_id', type=int)
        
        # Owners see their own stories + submitted employee stories, employees see all their own stories
        if user.role == 'owner' and user.company_id:
            # Owner: get their own stories OR submitted stories from their company
            from sqlalchemy import or_
            query = CaseStudy.query.filter(
                CaseStudy.company_id == user.company_id
            ).filter(
                or_(
                    CaseStudy.user_id == user_id,  # Owner's own stories
                    CaseStudy.submitted == True     # Submitted employee stories
                )
            )
        else:
            # Employee: only their own stories (submitted or not)
            query = CaseStudy.query.filter_by(user_id=user_id)
        
        if label_id:
            query = query.join(CaseStudy.labels).filter(Label.id == label_id)
        
        if creator_id:
            query = query.filter(CaseStudy.user_id == creator_id)
        
        case_studies = query.all()
        case_studies_data = []
        
        for case_study in case_studies:
            # Get user's feedback for this story
            user_feedback = StoryFeedback.query.filter_by(
                case_study_id=case_study.id,
                user_id=user_id
            ).first()
            
            # Get creator info - always include for filtering purposes
            creator_info = None
                creator = User.query.get(case_study.user_id)
                if creator:
                    creator_info = {
                        'id': creator.id,
                        'first_name': creator.first_name,
                        'last_name': creator.last_name,
                        'email': creator.email
                    }
            
            case_study_data = {
                'id': case_study.id,
                'title': case_study.title,
                'final_summary': case_study.final_summary,
                'meta_data_text': case_study.meta_data_text,
                'solution_provider_summary': case_study.solution_provider_interview.summary if case_study.solution_provider_interview else None,
                'client_summary': case_study.client_interview.summary if case_study.client_interview else None,
                'client_link_url': case_study.solution_provider_interview.client_link_url if case_study.solution_provider_interview else None,
                'created_at': case_study.created_at.isoformat() if case_study.created_at else None,
                'updated_at': case_study.updated_at.isoformat() if case_study.updated_at else None,
                'video_status': case_study.video_status,
                'pictory_video_status': case_study.pictory_video_status,
                'podcast_status': case_study.podcast_status,
                'labels': [{'id': l.id, 'name': l.name} for l in case_study.labels],
                'video_url': case_study.video_url,
                'video_id': case_study.video_id,
                'video_created_at': case_study.video_created_at.isoformat() if case_study.video_created_at else None,
                'newsflash_video_url': case_study.newsflash_video_url,
                'newsflash_video_id': case_study.newsflash_video_id,
                'newsflash_video_status': case_study.newsflash_video_status,
                'newsflash_video_created_at': case_study.newsflash_video_created_at.isoformat() if case_study.newsflash_video_created_at else None,
                'pictory_video_url': case_study.pictory_video_url,
                'pictory_storyboard_id': case_study.pictory_storyboard_id,
                'pictory_render_id': case_study.pictory_render_id,
                'pictory_video_created_at': case_study.pictory_video_created_at.isoformat() if case_study.pictory_video_created_at else None,
                'podcast_url': case_study.podcast_url,
                'podcast_job_id': case_study.podcast_job_id,
                'podcast_script': case_study.podcast_script,
                'podcast_created_at': case_study.podcast_created_at.isoformat() if case_study.podcast_created_at else None,
                'linkedin_post': case_study.linkedin_post,  # Legacy field for backward compatibility
                'linkedin_posts': {
                    'confident': case_study.linkedin_post_confident,
                    'pragmatic': case_study.linkedin_post_pragmatic,
                    'standard': case_study.linkedin_post_standard,
                    'formal': case_study.linkedin_post_formal
                },
                'email_subject': case_study.email_subject,
                'email_body': case_study.email_body,
                'user_feedback': user_feedback.to_dict() if user_feedback else None,
                'created_by': creator_info,  # Show creator info for owners viewing employee stories
                'submitted': case_study.submitted,  # Submission status
                'submitted_at': case_study.submitted_at.isoformat() if case_study.submitted_at else None,  # Submission timestamp
            }
            case_studies_data.append(case_study_data)
        
        return jsonify({'success': True, 'case_studies': case_studies_data})
    except Exception as e:
        logging.error(f"Error fetching case studies: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/case_studies/<int:case_study_id>', methods=['GET'])
@login_or_token_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Get case study by ID',
    'description': 'Retrieve a specific case study',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'}
        },
        {
            'name': 'token',
            'in': 'query',
            'required': False,
            'schema': {'type': 'string'},
            'description': 'Client interview token (optional, for client-side calls)'
        }
    ],
    'responses': {
        200: {
            'description': 'Case study retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'case_study': {'$ref': '#/components/schemas/CaseStudy'}
                        }
                    }
                }
            }
        },
        404: {'description': 'Case study not found'},
        401: {'description': 'Not authenticated'}
    }
})
def get_case_study(case_study_id):
    """Get a single case study by ID"""
    try:
        user_id = get_current_user_id()
        creator_info = None  # Initialize at the start to ensure it's always defined
        
        if user_id:
            # Session-based authentication - check company access
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            case_study = CaseStudy.query.filter_by(id=case_study_id).first()
            if not case_study:
                return jsonify({'error': 'Case study not found'}), 404
            
            # Check access: owners can see their own stories OR submitted company stories, employees only their own
            if user.role == 'owner':
                # Owner: must be from their company AND (their own story OR submitted)
                if case_study.company_id != user.company_id:
                    return jsonify({'error': 'Case study not found'}), 404
                # Allow if it's owner's own story OR if it's submitted
                if case_study.user_id != user_id and not case_study.submitted:
                    return jsonify({'error': 'Case study not found'}), 404
            else:
                # Employee: must be their own story
                if case_study.user_id != user_id:
                    return jsonify({'error': 'Case study not found'}), 404
            
            # Get creator info - always show who created the story for authenticated users
            try:
                creator = User.query.get(case_study.user_id)
                if creator:
                    creator_info = {
                        'id': creator.id,
                        'first_name': creator.first_name,
                        'last_name': creator.last_name,
                        'email': creator.email
                    }
            except Exception as e:
                print(f"Error fetching creator info: {e}")
                creator_info = None
        else:
            # Token-based authentication - just get the case study directly
            case_study = CaseStudy.query.filter_by(id=case_study_id).first()
            
            # Verify the token corresponds to this case study
            token = request.args.get('token')
            if token:
                invite_token = InviteToken.query.filter_by(token=token).first()
                if not invite_token or invite_token.case_study_id != case_study_id:
                    return jsonify({'error': 'Invalid token for this case study'}), 403
            
            # No creator info for token-based access
            creator_info = None
        
        if not case_study:
            return jsonify({'error': 'Case study not found'}), 404
        
        case_study_data = {
            'id': case_study.id,
            'title': case_study.title,
            'final_summary': case_study.final_summary,
            'meta_data_text': case_study.meta_data_text,
            'solution_provider_summary': case_study.solution_provider_interview.summary if case_study.solution_provider_interview else None,
            'client_summary': case_study.client_interview.summary if case_study.client_interview else None,
            'client_link_url': case_study.solution_provider_interview.client_link_url if case_study.solution_provider_interview else None,
            'created_at': case_study.created_at.isoformat() if case_study.created_at else None,
            'updated_at': case_study.updated_at.isoformat() if case_study.updated_at else None,
            'video_status': case_study.video_status,
            'pictory_video_status': case_study.pictory_video_status,
            'podcast_status': case_study.podcast_status,
            'labels': [{'id': l.id, 'name': l.name, 'color': l.color} for l in case_study.labels],
            'video_url': case_study.video_url,
            'video_id': case_study.video_id,
            'video_created_at': case_study.video_created_at.isoformat() if case_study.video_created_at else None,
            'newsflash_video_url': case_study.newsflash_video_url,
            'newsflash_video_id': case_study.newsflash_video_id,
            'newsflash_video_status': case_study.newsflash_video_status,
            'newsflash_video_created_at': case_study.newsflash_video_created_at.isoformat() if case_study.newsflash_video_created_at else None,
            'pictory_video_url': case_study.pictory_video_url,
            'pictory_storyboard_id': case_study.pictory_storyboard_id,
            'pictory_render_id': case_study.pictory_render_id,
            'pictory_video_created_at': case_study.pictory_video_created_at.isoformat() if case_study.pictory_video_created_at else None,
            'podcast_url': case_study.podcast_url,
            'podcast_job_id': case_study.podcast_job_id,
            'podcast_script': case_study.podcast_script,
            'podcast_created_at': case_study.podcast_created_at.isoformat() if case_study.podcast_created_at else None,
            'linkedin_post': case_study.linkedin_post,  # Legacy field for backward compatibility
            'linkedin_posts': {
                'confident': case_study.linkedin_post_confident,
                'pragmatic': case_study.linkedin_post_pragmatic,
                'standard': case_study.linkedin_post_standard,
                'formal': case_study.linkedin_post_formal
            },
            'email_subject': case_study.email_subject,
            'email_body': case_study.email_body,
            'submitted': case_study.submitted,
            'submitted_at': case_study.submitted_at.isoformat() if case_study.submitted_at else None,
            'created_by': creator_info,  # Creator info (name, email) - always included
        }
        
        return jsonify({'success': True, 'case_study': case_study_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
@bp.route('/labels', methods=['GET'])
@login_required
@swag_from({
    'tags': ['Labels'],
    'summary': 'Get all labels',
    'description': 'Retrieve all labels for the current user',
    'responses': {
        200: {
            'description': 'Labels retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'labels': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'integer'},
                                        'name': {'type': 'string'},
                                        'color': {'type': 'string', 'description': 'HEX color code'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'}
    }
})
def get_labels():
    """Get all labels for the current user"""
    try:
        user_id = get_current_user_id()
        labels = Label.query.filter_by(user_id=user_id).all()
        labels_data = [{'id': l.id, 'name': l.name, 'color': l.color} for l in labels]
        return jsonify({'success': True, 'labels': labels_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/labels', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Labels'],
    'summary': 'Create a new label',
    'description': 'Create a new label for organizing case studies',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['name'],
                    'properties': {
                        'name': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Label created successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'label': {'$ref': '#/components/schemas/Label'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Bad Request'},
        401: {'description': 'Not authenticated'}
    }
})
def create_label():
    """Create a new label"""
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'error': 'Label name required'}), 400
        
        label = Label(name=name, user_id=user_id)
        db.session.add(label)
        db.session.commit()
        
        return jsonify({'success': True, 'label': {'id': label.id, 'name': label.name, 'color': label.color}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/labels/<int:label_id>', methods=['PATCH'])
@login_required
@swag_from({
    'tags': ['Labels'],
    'summary': 'Rename a label',
    'description': 'Update the name of an existing label',
    'parameters': [
        {
            'name': 'label_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'}
        }
    ],
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['name'],
                    'properties': {
                        'name': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Label renamed successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'label': {'$ref': '#/components/schemas/Label'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Bad Request'},
        401: {'description': 'Not authenticated'},
        404: {'description': 'Label not found'}
    }
})
def rename_label(label_id):
    """Rename a label"""
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return jsonify({'error': 'New label name required'}), 400
        
        label = Label.query.filter_by(id=label_id, user_id=user_id).first()
        if not label:
            return jsonify({'error': 'Label not found'}), 404
        
        label.name = new_name
        db.session.commit()
        
        return jsonify({'success': True, 'label': {'id': label.id, 'name': label.name, 'color': label.color}})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/labels/<int:label_id>', methods=['DELETE'])
@login_required
@swag_from({
    'tags': ['Labels'],
    'summary': 'Delete a label',
    'description': 'Remove a label (case studies will not be deleted)',
    'parameters': [
        {
            'name': 'label_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'}
        }
    ],
    'responses': {
        200: {
            'description': 'Label deleted successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'},
        404: {'description': 'Label not found'}
    }
})
def delete_label(label_id):
    """Delete a label"""
    try:
        user_id = get_current_user_id()
        label = Label.query.filter_by(id=label_id, user_id=user_id).first()
        
        if not label:
            return jsonify({'error': 'Label not found'}), 404
        
        db.session.delete(label)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@bp.route('/color-palette', methods=['GET'])
@swag_from({
    'tags': ['Labels'],
    'summary': 'Get color palette information',
    'description': 'Retrieve information about the color palette used for labels',
    'responses': {
        200: {
            'description': 'Color palette information retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'palette': {
                                'type': 'object',
                                'properties': {
                                    'total_colors': {'type': 'integer'},
                                    'description': {'type': 'string'},
                                    'colors': {
                                        'type': 'array',
                                        'items': {'type': 'string'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
})
def get_color_palette():
    """Get color palette information for labels"""
    try:
        from app.utils.color_utils import ColorUtils
        palette_info = ColorUtils.get_color_palette_info()
        return jsonify({'success': True, 'palette': palette_info})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/case_studies/<int:case_study_id>/labels', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Labels'],
    'summary': 'Add labels to a case study',
    'description': 'Attach existing labels by ID or create by name and attach',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'}
        }
    ],
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'label_ids': {'type': 'array', 'items': {'type': 'integer'}},
                        'label_names': {'type': 'array', 'items': {'type': 'string'}}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Labels added successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'labels': {
                                'type': 'array',
                                'items': {'$ref': '#/components/schemas/Label'}
                            }
                        }
                    }
                }
            }
        },
        404: {'description': 'Case study not found'},
        401: {'description': 'Not authenticated'}
    }
})
def add_labels_to_case_study(case_study_id):
    """Add labels to a case study"""
    try:
        user_id = get_current_user_id()
        data = request.get_json()
        label_ids = data.get('label_ids', [])
        label_names = data.get('label_names', [])
        
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        if not case_study:
            return jsonify({'error': 'Case study not found'}), 404
        
        # Add by IDs
        for lid in label_ids:
            label = Label.query.filter_by(id=lid, user_id=user_id).first()
            if label and label not in case_study.labels:
                case_study.labels.append(label)
        
        # Add by names (create if not exist)
        for name in label_names:
            name = name.strip()
            if not name:
                continue
            label = Label.query.filter_by(name=name, user_id=user_id).first()
            if not label:
                label = Label(name=name, user_id=user_id)
                db.session.add(label)
                db.session.commit()
            if label not in case_study.labels:
                case_study.labels.append(label)
        
        db.session.commit()
        return jsonify({'success': True, 'labels': [{'id': l.id, 'name': l.name, 'color': l.color} for l in case_study.labels]})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/case_studies/<int:case_study_id>/labels/<int:label_id>', methods=['DELETE'])
@login_required
@swag_from({
    'tags': ['Labels'],
    'summary': 'Remove a label from a case study',
    'parameters': [
        {'name': 'case_study_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}},
        {'name': 'label_id', 'in': 'path', 'required': True, 'schema': {'type': 'integer'}}
    ],
    'responses': {
        200: {
            'description': 'Label removed successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'labels': {'type': 'array', 'items': {'$ref': '#/components/schemas/Label'}}
                        }
                    }
                }
            }
        },
        404: {'description': 'Case study or label not found'},
        401: {'description': 'Not authenticated'}
    }
})
def remove_label_from_case_study(case_study_id, label_id):
    """Remove a label from a case study"""
    try:
        user_id = get_current_user_id()
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        if not case_study:
            return jsonify({'error': 'Case study not found'}), 404
        
        label = Label.query.filter_by(id=label_id, user_id=user_id).first()
        if not label or label not in case_study.labels:
            return jsonify({'error': 'Label not found on this case study'}), 404
        
        case_study.labels.remove(label)
        db.session.commit()
        
        return jsonify({'success': True, 'labels': [{'id': l.id, 'name': l.name, 'color': l.color} for l in case_study.labels]})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route("/generate_linkedin_post", methods=["POST"])
@login_required
@owner_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Generate LinkedIn post variations',
    'description': 'Generate four variations of LinkedIn posts from case study content using different prompt styles: Confident, Pragmatic, Standard, and Formal',
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
            'description': 'LinkedIn post variations generated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {
                                'type': 'string',
                                'example': 'success'
                            },
                            'linkedin_posts': {
                                'type': 'object',
                                'description': 'Four variations of LinkedIn posts with different tones and styles',
                                'properties': {
                                    'confident': {
                                        'type': 'string',
                                        'description': 'Confident variation - sharply confident, witty, and punchy voice'
                                    },
                                    'pragmatic': {
                                        'type': 'string',
                                        'description': 'Pragmatic variation - grounded, relatable, authentic voice'
                                    },
                                    'standard': {
                                        'type': 'string',
                                        'description': 'Standard variation - conversational, expert, and authentic voice'
                                    },
                                    'formal': {
                                        'type': 'string',
                                        'description': 'Formal variation - formal, strategic, and highly analytical voice'
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing case study ID or no final summary'},
        403: {'description': 'Only owners can generate LinkedIn posts'},
        404: {'description': 'Case study not found'},
        500: {'description': 'Error generating LinkedIn post variations'}
    }
})
def generate_linkedin_post():
    """Generate LinkedIn post from case study"""
    try:
        data = request.get_json()
        case_study_id = data.get("case_study_id")

        if not case_study_id:
            return jsonify({"status": "error", "message": "Missing case_study_id"}), 400

        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404

        # Verify company access: owners can generate LinkedIn posts for any company story
        if user.role == 'owner' and user.company_id:
            if case_study.company_id != user.company_id:
                return jsonify({"status": "error", "message": "Case study not found"}), 404
        else:
            # Employees cannot generate LinkedIn posts
            return jsonify({"status": "error", "message": "Only owners can generate LinkedIn posts"}), 403

        if not case_study.final_summary:
            return jsonify({"status": "error", "message": "No final summary available"}), 400

        # Generate LinkedIn post variations using Gemini
        ai_service = AIService()
        result = ai_service.generate_linkedin_post_variations(case_study.final_summary)
        
        # Check if generation was successful
        if result.get("status") == "error":
            return jsonify({
                "status": "error", 
                "message": result.get("message", "Failed to generate LinkedIn posts")
            }), 500
        
        variations = result.get("variations", {})
        
        print(f"📥 Received {len(variations)} variations: {list(variations.keys())}")
        
        # Helper function to safely extract content
        def get_variation_content(variation_key):
            variation = variations.get(variation_key, {})
            if variation.get("status") == "success":
                return variation.get("content")
            else:
                error_msg = variation.get("content", "Unknown error")
                print(f"⚠️ Variation {variation_key} failed: {error_msg[:100]}")
                return None
        
        # Save all variations to database
        # Only update variations that successfully generated - don't overwrite with None
        confident_content = get_variation_content("confident")
        pragmatic_content = get_variation_content("pragmatic")
        standard_content = get_variation_content("standard")
        formal_content = get_variation_content("formal")
        
        # Only update database fields if content was successfully generated and is not empty
        # This preserves existing content if a variation fails to generate or generates empty content
        # Use same logic as API response to ensure consistency
        if confident_content and confident_content.strip():
            case_study.linkedin_post_confident = confident_content
        if pragmatic_content and pragmatic_content.strip():
            case_study.linkedin_post_pragmatic = pragmatic_content
        if standard_content and standard_content.strip():
            case_study.linkedin_post_standard = standard_content
        if formal_content and formal_content.strip():
            case_study.linkedin_post_formal = formal_content
        
        db.session.commit()

        # Build response with only successful variations (non-empty content)
        # Use same logic as database save to ensure consistency
        linkedin_posts = {}
        if confident_content and confident_content.strip():
            linkedin_posts["confident"] = confident_content
        if pragmatic_content and pragmatic_content.strip():
            linkedin_posts["pragmatic"] = pragmatic_content
        if standard_content and standard_content.strip():
            linkedin_posts["standard"] = standard_content
        if formal_content and formal_content.strip():
            linkedin_posts["formal"] = formal_content
        
        print(f"✅ Returning {len(linkedin_posts)} successful variations: {list(linkedin_posts.keys())}")
        
        # Verify that at least one variation generated successfully
        if not linkedin_posts:
            return jsonify({
                "status": "error",
                "message": "Failed to generate any LinkedIn post variations. Please try again."
            }), 500
        
        return jsonify({
            "status": "success",
            "linkedin_posts": linkedin_posts
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in generate_linkedin_post route: {str(e)}")
        return jsonify({"status": "error", "message": f"Error generating LinkedIn post: {str(e)}"}), 500

@bp.route("/save_linkedin_post", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Save LinkedIn post',
    'description': 'Save a LinkedIn post to a case study (for edited posts)',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id', 'linkedin_post'],
                    'properties': {
                        'case_study_id': {
                            'type': 'integer',
                            'description': 'ID of the case study'
                        },
                        'linkedin_post': {
                            'type': 'string',
                            'description': 'The LinkedIn post content to save'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'LinkedIn post saved successfully',
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
        400: {'description': 'Missing case study ID or LinkedIn post content'},
        404: {'description': 'Case study not found'},
        500: {'description': 'Error saving LinkedIn post'}
    }
})
def save_linkedin_post():
    """Save LinkedIn post to case study"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        data = request.get_json()
        case_study_id = data.get("case_study_id")
        linkedin_post = data.get("linkedin_post")  # Legacy field
        linkedin_posts = data.get("linkedin_posts", {})  # New field with all variations

        if not case_study_id:
            return jsonify({"status": "error", "message": "Missing case_study_id"}), 400

        if linkedin_post is None and not linkedin_posts:
            return jsonify({"status": "error", "message": "Missing linkedin_post or linkedin_posts"}), 400

        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404
        
        # Check access: owners can edit any company story, employees only their own
        if user.role == 'owner' and user.company_id:
            if case_study.company_id != user.company_id:
                return jsonify({"status": "error", "message": "Case study not found"}), 404
        else:
            if case_study.user_id != user_id:
                return jsonify({"status": "error", "message": "Case study not found"}), 404
        
        # Employees cannot edit submitted stories
        if user.role == 'employee' and case_study.submitted:
            return jsonify({
                "status": "error",
                "message": "Cannot edit submitted case study. Please contact your owner to make changes."
            }), 403

        # Save all variations to database
        # Only update fields that are actually present in the request to avoid overwriting with None
        if linkedin_posts:
            # Only update fields that are explicitly provided in the request
            if "confident" in linkedin_posts:
                case_study.linkedin_post_confident = linkedin_posts.get("confident")
            if "pragmatic" in linkedin_posts:
                case_study.linkedin_post_pragmatic = linkedin_posts.get("pragmatic")
            if "standard" in linkedin_posts:
                case_study.linkedin_post_standard = linkedin_posts.get("standard")
            if "formal" in linkedin_posts:
                case_study.linkedin_post_formal = linkedin_posts.get("formal")
        
        # Save legacy field for backward compatibility
        # Priority: 1) linkedin_post (active tab's content from frontend), 2) standard variation, 3) any other variation
        # Only update if a non-empty value is provided (empty strings should not overwrite existing data)
        if linkedin_post is not None and linkedin_post.strip():
            # Use the active tab's content (sent from frontend)
            case_study.linkedin_post = linkedin_post
        elif linkedin_posts:
            # Fallback: use standard if available, otherwise use the first available variation
            if linkedin_posts.get("standard") and linkedin_posts.get("standard").strip():
                case_study.linkedin_post = linkedin_posts.get("standard")
            else:
                # Find the first non-empty variation
                for variation_key in ["confident", "pragmatic", "formal", "standard"]:
                    content = linkedin_posts.get(variation_key)
                    if content and content.strip():
                        case_study.linkedin_post = content
                        break
        
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "LinkedIn post saved successfully"
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in save_linkedin_post route: {str(e)}")
        return jsonify({"status": "error", "message": f"Error saving LinkedIn post: {str(e)}"}), 500

@bp.route("/save_email_draft", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Save email draft',
    'description': 'Save an email draft (subject and body) to a case study',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id', 'email_subject', 'email_body'],
                    'properties': {
                        'case_study_id': {
                            'type': 'integer',
                            'description': 'ID of the case study'
                        },
                        'email_subject': {
                            'type': 'string',
                            'description': 'The email subject to save'
                        },
                        'email_body': {
                            'type': 'string',
                            'description': 'The email body content to save'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Email draft saved successfully',
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
        400: {'description': 'Missing case study ID, email subject, or email body'},
        404: {'description': 'Case study not found'},
        500: {'description': 'Error saving email draft'}
    }
})
def save_email_draft():
    """Save email draft to case study"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        data = request.get_json()
        case_study_id = data.get("case_study_id")
        email_subject = data.get("email_subject")
        email_body = data.get("email_body")

        if not case_study_id:
            return jsonify({"status": "error", "message": "Missing case_study_id"}), 400

        if email_subject is None:
            return jsonify({"status": "error", "message": "Missing email_subject"}), 400

        if email_body is None:
            return jsonify({"status": "error", "message": "Missing email_body"}), 400

        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404
        
        # Check access: owners can edit any company story, employees only their own
        if user.role == 'owner' and user.company_id:
            if case_study.company_id != user.company_id:
                return jsonify({"status": "error", "message": "Case study not found"}), 404
        else:
            if case_study.user_id != user_id:
                return jsonify({"status": "error", "message": "Case study not found"}), 404
        
        # Employees cannot edit submitted stories
        if user.role == 'employee' and case_study.submitted:
            return jsonify({
                "status": "error",
                "message": "Cannot edit submitted case study. Please contact your owner to make changes."
            }), 403

        # Save to database
        case_study.email_subject = email_subject
        case_study.email_body = email_body
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Email draft saved successfully"
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in save_email_draft route: {str(e)}")
        return jsonify({"status": "error", "message": f"Error saving email draft: {str(e)}"}), 500


@bp.route("/download_full_summary_pdf")
@login_required
@swag_from({
    'tags': ['Files'],
    'summary': 'Download full summary PDF',
    'description': 'Download the full summary PDF from database',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'query',
            'required': True,
            'schema': {'type': 'string'},
            'description': 'ID of the case study'
        }
    ],
    'responses': {
        200: {
            'description': 'PDF downloaded successfully',
            'content': {
                'application/pdf': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        400: {'description': 'Missing case study ID'},
        404: {'description': 'Case study not found or PDF not available'}
    }
})
def download_full_summary_pdf():
    """Download the full summary PDF from DB"""
    case_study_id = request.args.get("case_study_id")
    print(f"📥 Download request for case study ID: {case_study_id}")
    
    if not case_study_id:
        return jsonify({"status": "error", "message": "Missing case_study_id"}), 400
    try:
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            print(f"❌ Case study not found: {case_study_id}")
            return jsonify({"status": "error", "message": "Case study not found"}), 404
            
        if not case_study.final_summary_pdf_data:
            print(f"❌ No PDF data found for case study: {case_study_id}")
            return jsonify({"status": "error", "message": "Final summary PDF not available"}), 404
            
        print(f"✅ Found PDF data, size: {len(case_study.final_summary_pdf_data)} bytes")
        return send_file(
            BytesIO(case_study.final_summary_pdf_data),
            as_attachment=True,
            download_name=f"{case_study.title or 'Case_Study'}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        print(f"❌ Error in download_full_summary_pdf: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# REMOVED: Duplicate route /generate_full_case_study - this is now handled by interviews.py
# This route was causing conflicts and preventing the solution provider interview from working properly

@bp.route("/extract_names", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Summary'],
    'summary': 'Extract names from case study text',
    'description': 'Extract company names and project title from case study text using AI',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_text'],
                    'properties': {
                        'case_study_text': {
                            'type': 'string',
                            'description': 'Case study text to extract names from'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Names extracted successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'names': {
                                'type': 'object',
                                'properties': {
                                    'lead_entity': {'type': 'string', 'description': 'Lead company name'},
                                    'partner_entity': {'type': 'string', 'description': 'Partner/client company name'},
                                    'project_title': {'type': 'string', 'description': 'Project title'}
                                }
                            },
                            'method': {'type': 'string', 'description': 'Method used for extraction'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing case study text'},
        500: {'description': 'Internal server error'}
    }
})
def extract_names():
    """Extract names from case study text"""
    try:
        data = request.get_json()
        # Accept both case_study_text and summary for compatibility
        case_study_text = data.get("case_study_text", "") or data.get("summary", "")
        if not case_study_text:
            return jsonify({"status": "error", "message": "Missing case_study_text or summary"}), 400

        print(f"🎯 Starting name extraction for text length: {len(case_study_text)}")
        ai_service = AIService()
        names = ai_service.extract_names_from_case_study(case_study_text)
        print(f"🎯 Name extraction result: {names}")
        
        return jsonify({
            "status": "success", 
            "names": names,
            "method": "llm"  # Add method indicator
        })
    except Exception as e:
        print(f"❌ Error in extract_names endpoint: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/save_final_summary", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Summary'],
    'summary': 'Save final summary',
    'description': 'Auto-save final case study summary',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id', 'final_summary'],
                    'properties': {
                        'case_study_id': {'type': 'integer'},
                        'final_summary': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Final summary saved',
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
        400: {'description': 'Missing data'}
    }
})
def save_final_summary():
    """Save final summary"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        data = request.get_json()
        case_study_id = data.get("case_study_id")
        final_summary = data.get("final_summary")
        # Get edited names from frontend if provided
        solution_provider = data.get("solution_provider")
        client_name = data.get("client_name") 
        project_name = data.get("project_name")

        if not case_study_id or not final_summary:
            return jsonify({"status": "error", "message": "Missing data"}), 400

        # Get the case study from DB
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404
        
        # Check access: owners can edit any company story, employees only their own
        if user.role == 'owner' and user.company_id:
            if case_study.company_id != user.company_id:
                return jsonify({"status": "error", "message": "Case study not found"}), 404
        else:
            if case_study.user_id != user_id:
                return jsonify({"status": "error", "message": "Case study not found"}), 404
        
        # Employees cannot edit submitted stories
        if user.role == 'employee' and case_study.submitted:
            return jsonify({
                "status": "error",
                "message": "Cannot edit submitted case study. Please contact your owner to make changes."
            }), 403

        # Update final summary
        case_study.final_summary = final_summary

        # Detect and store language if not already set
        if not case_study.language:
            case_study.language = detect_and_normalize_language(final_summary)

        # Use edited names from frontend if provided, otherwise extract from final summary
        if solution_provider and client_name and project_name:
            names = {
                "lead_entity": solution_provider,
                "partner_entity": client_name,
                "project_title": project_name
            }
            print(f"✅ Using edited names from frontend for final summary: {names}")
        else:
            # Extract names from the new final summary
            ai_service = AIService()
            names = ai_service.extract_names_from_case_study(final_summary)
            print(f"✅ Using extracted names from final summary: {names}")
        
        lead_entity = names["lead_entity"]
        partner_entity = names["partner_entity"]
        project_title = names["project_title"]

        # Update CaseStudy name fields
        case_study.provider_name = lead_entity
        case_study.client_name = partner_entity
        case_study.project_name = project_title

        # Enforce title format: "Client Name: Title"
        def strip_existing_prefix(text):
            if not text:
                return ""
            if ':' in text:
                parts = text.split(':', 1)
                if len(parts[0].strip()) <= 100:
                    return parts[1].strip()
            return text.strip()

        # Filter out placeholder/default values that shouldn't be used as client names
        placeholder_values = ["Client Name", "Company Name", "Unknown", "Unknown Client", ""]
        partner_entity_clean = (partner_entity or "").strip()
        is_placeholder = partner_entity_clean in placeholder_values or not partner_entity_clean
        
        # Get the title core (strip existing prefix if present)
        current_title_core = strip_existing_prefix(case_study.title or "")
        # If title core is empty after stripping, use the original title (might not have had a prefix)
        if not current_title_core:
            current_title_core = (case_study.title or "").strip()
        
        # Always add a prefix: use real client name if available, otherwise use "Unknown" as fallback
        if partner_entity_clean and not is_placeholder:
            case_study.title = f"{partner_entity_clean}: {current_title_core}"
        else:
            case_study.title = f"Unknown: {current_title_core}"

        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Final summary and title updated",
            "names": names,
            "case_study_id": case_study.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/generate_pdf", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Summary'],
    'summary': 'Generate PDF',
    'description': 'Generate PDF document from case study',
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
            'description': 'PDF file download',
            'content': {
                'application/pdf': {
                    'schema': {
                        'type': 'string',
                        'format': 'binary'
                    }
                }
            }
        },
        400: {'description': 'Missing case_study_id'}
    }
})
def generate_pdf():
    """Generate PDF from existing final summary - always regenerates with latest content"""
    try:
        print("PDF called here")
        data = request.get_json()
        case_study_id = data.get("case_study_id")

        if not case_study_id:
            return jsonify({"status": "error", "message": "Missing case_study_id"}), 400

        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404

        if not case_study.final_summary:
            return jsonify({"status": "error", "message": "No final summary available to generate PDF"}), 400

        pdf = FPDF()
        pdf.add_page()
        pdf.set_margins(20, 20, 20)  # Left, Top, Right margins
        pdf.set_auto_page_break(auto=True, margin=20)
        try:
            pdf.set_font("Arial", 'B', 16)

            pdf.set_text_color(0, 0, 0)
            title = case_study.title or "Case Study"
            clean_title = title.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, clean_title, align='C')
            pdf.ln(10)

            # Add final summary content with section headings
            pdf.set_text_color(0, 0, 0)
            summary_lines = case_study.final_summary.split('\n')
            for line in summary_lines:
                clean_line = line.encode('latin-1', 'replace').decode('latin-1').strip()

                # If line is a heading (uppercase & not too long) → bold
                if clean_line.isupper() and len(clean_line) < 60:
                    pdf.set_font("Arial", 'B', 13)
                    pdf.cell(0, 8, clean_line, ln=True)
                    pdf.ln(2)
                # Otherwise → normal paragraph text
                elif clean_line:
                    pdf.set_font("Arial", '', 11)
                    pdf.multi_cell(0, 6, clean_line)
                    pdf.ln(2)
                else:
                    pdf.ln(3)  # Extra space for empty lines
        except Exception as pdf_error:
            print(f"❌ PDF generation error: {str(pdf_error)}")
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, "Case Study PDF")
            pdf.ln(10)
            summary_text = case_study.final_summary[:1000] + "..." if len(
                case_study.final_summary) > 1000 else case_study.final_summary
            clean_summary_text = summary_text.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, clean_summary_text)

        # Save PDF to database (not filesystem)
        # Generate PDF as bytes - compatible with all FPDF versions
        try:
            # Try method 1: output to BytesIO buffer (works with most FPDF versions)
            pdf_buffer = BytesIO()
            result = pdf.output(pdf_buffer, 'S')
            
            # Handle different FPDF return types
            if isinstance(result, bytes):
                pdf_bytes = result
            elif isinstance(result, str):
                # Some FPDF versions return string, encode it
                pdf_bytes = result.encode('latin-1')
            else:
                # Buffer method - get value from buffer
                pdf_bytes = pdf_buffer.getvalue()
            
            print(f"📄 PDF generated: {len(pdf_bytes)} bytes")
            
            # Validate PDF was generated
            if not pdf_bytes or len(pdf_bytes) == 0:
                raise Exception("PDF generation failed: empty PDF buffer")
            
            # Validate PDF header (PDF files start with %PDF)
            if not pdf_bytes.startswith(b'%PDF'):
                print(f"⚠️ Invalid PDF header. First 20 bytes: {pdf_bytes[:20]}")
                raise Exception("PDF generation failed: invalid PDF format")
        except Exception as pdf_gen_error:
            print(f"❌ Error generating PDF bytes: {str(pdf_gen_error)}")
            import traceback
            traceback.print_exc()
            raise
        
        case_study.final_summary_pdf_data = pdf_bytes
        db.session.commit()

        # Return the file directly - create a fresh BytesIO from the bytes
        response_buffer = BytesIO(pdf_bytes)
        response_buffer.seek(0)

        return send_file(
            response_buffer,
            as_attachment=True,
            download_name=f"{case_study.title or 'Case_Study'}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/case_studies/<int:case_study_id>/title', methods=['PUT'])
@login_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Update case study title',
    'description': 'Update the title of a specific case study',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'},
            'description': 'ID of the case study'
        }
    ],
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['title'],
                    'properties': {
                        'title': {
                            'type': 'string',
                            'description': 'New title for the case study',
                            'maxLength': 200
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Title updated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'message': {'type': 'string'},
                            'title': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Invalid title or missing data'},
        404: {'description': 'Case study not found'},
        403: {'description': 'Not authorized to update this case study'}
    }
})
def update_case_study_title(case_study_id):
    """Update the title of a case study"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        data = request.get_json()
        
        if not data or 'title' not in data:
            return jsonify({"status": "error", "message": "Title is required"}), 400
        
        title = data['title'].strip()
        if not title:
            return jsonify({"status": "error", "message": "Title cannot be empty"}), 400
        
        if len(title) > 200:
            return jsonify({"status": "error", "message": "Title must be 200 characters or less"}), 400
        
        # Get the case study and verify ownership
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404
        
        # Employees cannot edit submitted stories
        if user.role == 'employee' and case_study.submitted:
            return jsonify({
                "status": "error",
                "message": "Cannot edit submitted case study. Please contact your owner to make changes."
            }), 403
        
        # Update the title
        case_study.title = title
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Title updated successfully",
            "title": title
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route('/case_studies/<int:case_study_id>/submit', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Submit case study to owner',
    'description': 'Submit a case study to the company owner. Once submitted, employees cannot edit it.',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'},
            'description': 'ID of the case study to submit'
        }
    ],
    'responses': {
        200: {
            'description': 'Case study submitted successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'message': {'type': 'string'},
                            'submitted_at': {'type': 'string', 'format': 'date-time'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Case study already submitted or invalid request'},
        403: {'description': 'Only employees can submit stories'},
        404: {'description': 'Case study not found'}
    }
})
def submit_case_study(case_study_id):
    """Submit a case study to the owner"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        # Only employees can submit stories
        if user.role != 'employee':
            return jsonify({
                "status": "error",
                "message": "Only employees can submit stories to owners"
            }), 403
        
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404
        
        # Check if already submitted
        if case_study.submitted:
            return jsonify({
                "status": "error",
                "message": "This case study has already been submitted"
            }), 400
        
        # Submit the case study
        case_study.submitted = True
        case_study.submitted_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Case study submitted successfully to owner",
            "submitted_at": case_study.submitted_at.isoformat()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/case_study_status/<int:case_study_id>", methods=["GET"])
@login_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Check case study completion status',
    'description': 'Check if case study has been completed with client interview',
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
            'description': 'Case study status retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string', 'description': 'completion status'},
                            'has_client_interview': {'type': 'boolean'},
                            'has_full_case_study': {'type': 'boolean'},
                            'updated_at': {'type': 'string'},
                            'client_summary': {'type': 'string'},
                            'final_summary': {'type': 'string'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'},
        404: {'description': 'Case study not found'}
    }
})
def check_case_study_status(case_study_id):
    """Check if case study has been completed with client interview"""
    try:
        user_id = get_current_user_id()
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Check if client interview exists and has summary
        has_client_interview = bool(
            case_study.client_interview and 
            case_study.client_interview.summary and 
            case_study.client_interview.summary.strip()
        )
        
        # ✅ FIXED: Check if final_summary was generated AFTER client interview
        # We check for meta_data_text which is only generated when both interviews are complete
        has_full_case_study_with_client = bool(
            case_study.final_summary and 
            case_study.final_summary.strip() and
            case_study.meta_data_text and  # This is only set when both interviews are processed
            case_study.meta_data_text.strip()
        )
        
        # Additional check: Ensure final_summary contains client perspective content
        # (This is generated only when client interview is included)
        has_client_content_in_summary = False
        if has_client_interview and case_study.final_summary:
            # Check if the final_summary was updated after client interview completion
            # by looking for metadata or timestamp comparison
            if case_study.meta_data_text:
                try:
                    meta_data = json.loads(case_study.meta_data_text)
                    # If sentiment data exists, it means the full case study was generated with client data
                    has_client_content_in_summary = bool(meta_data.get("sentiment"))
                except:
                    has_client_content_in_summary = False
        
        # Final check: Both conditions must be true for completion
        has_full_case_study = has_full_case_study_with_client and (has_client_content_in_summary or not has_client_interview)
        
        # Determine overall status
        if has_client_interview and has_full_case_study:
            status = "completed"
        elif has_client_interview:
            status = "client_completed"
        else:
            status = "pending"
        
        return jsonify({
            "status": status,
            "has_client_interview": has_client_interview,
            "has_full_case_study": has_full_case_study,
            "updated_at": case_study.updated_at.isoformat() if case_study.updated_at else None,
            "client_summary": case_study.client_interview.summary if case_study.client_interview else None,
            "final_summary": case_study.final_summary
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route('/case_studies/<int:case_study_id>/feedback', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Story Feedback'],
    'summary': 'Submit feedback for a specific story',
    'description': 'Submit or update feedback (thumbs up/down) for a story. Text feedback is optional for both thumbs up and thumbs down.',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'},
            'description': 'ID of the case study/story'
        }
    ],
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['is_thumbs_up'],
                    'properties': {
                        'is_thumbs_up': {
                            'type': 'boolean',
                            'description': 'True for thumbs up, False for thumbs down'
                        },
                        'feedback_text': {
                            'type': 'string',
                            'description': 'Optional text feedback explaining what can be improved. Can be provided for both thumbs up and thumbs down.'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Feedback submitted/updated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'},
                            'feedback': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'case_study_id': {'type': 'integer'},
                                    'user_id': {'type': 'integer'},
                                    'is_thumbs_up': {'type': 'boolean'},
                                    'is_thumbs_down': {'type': 'boolean'},
                                    'feedback_text': {'type': 'string', 'nullable': True},
                                    'created_at': {'type': 'string', 'format': 'date-time'},
                                    'updated_at': {'type': 'string', 'format': 'date-time'}
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Bad request - missing required fields or invalid data',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        },
        404: {
            'description': 'Story not found',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'},
        500: {
            'description': 'Internal server error',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
})
def submit_story_feedback(case_study_id):
    """Submit feedback for a specific story"""
    try:
        user_id = get_current_user_id()
        
        # Verify the case study exists and belongs to the user
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        if not case_study:
            return jsonify({'success': False, 'message': 'Story not found'}), 404
        
        data = request.get_json()
        is_thumbs_up = data.get('is_thumbs_up')
        feedback_text = data.get('feedback_text', '').strip()
        
        if is_thumbs_up is None:
            return jsonify({'success': False, 'message': 'is_thumbs_up is required'}), 400
        
        # Check if feedback already exists
        existing_feedback = StoryFeedback.query.filter_by(
            case_study_id=case_study_id,
            user_id=user_id
        ).first()
        
        if existing_feedback:
            # If clicking the same feedback type again without text, remove it (toggle off)
            # For thumbs up: if same type, remove
            # For thumbs down: if same type AND no text provided, remove (toggle off)
            if existing_feedback.is_thumbs_up == is_thumbs_up:
                if is_thumbs_up:
                    # Thumbs up: always toggle off if clicking same
                    db.session.delete(existing_feedback)
                    db.session.commit()
                    return jsonify({
                        'success': True,
                        'message': 'Feedback removed successfully',
                        'feedback': None
                    })
                else:
                    # Thumbs down: only toggle off if no text provided (button click to remove)
                    # If text is provided, update the feedback text
                    if not feedback_text:
                        db.session.delete(existing_feedback)
                        db.session.commit()
                        return jsonify({
                            'success': True,
                            'message': 'Feedback removed successfully',
                            'feedback': None
                        })
                    else:
                        # Update the feedback text
                        existing_feedback.feedback_text = feedback_text
                        existing_feedback.updated_at = datetime.now(UTC)
                        db.session.commit()
                        return jsonify({
                            'success': True,
                            'message': 'Feedback updated successfully',
                            'feedback': existing_feedback.to_dict()
                        })
            else:
                # Update existing feedback to different type
                existing_feedback.is_thumbs_up = is_thumbs_up
                existing_feedback.is_thumbs_down = not is_thumbs_up  # Keep in sync
                existing_feedback.feedback_text = feedback_text if feedback_text else None
                existing_feedback.updated_at = datetime.now(UTC)
                db.session.commit()
                return jsonify({
                    'success': True,
                    'message': 'Feedback updated successfully',
                    'feedback': existing_feedback.to_dict()
                })
        else:
            # Create new feedback
            # Text is optional for both thumbs up and thumbs down
            feedback = StoryFeedback(
                case_study_id=case_study_id,
                user_id=user_id,
                is_thumbs_up=is_thumbs_up,
                feedback_text=feedback_text if feedback_text else None
            )
            db.session.add(feedback)
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Feedback submitted successfully',
                'feedback': feedback.to_dict()
            })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@bp.route('/case_studies/<int:case_study_id>/feedback', methods=['GET'])
@login_required
@swag_from({
    'tags': ['Story Feedback'],
    'summary': 'Get feedback for a specific story',
    'description': 'Retrieve the current user\'s feedback for a specific story',
    'parameters': [
        {
            'name': 'case_study_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'},
            'description': 'ID of the case study/story'
        }
    ],
    'responses': {
        200: {
            'description': 'Feedback retrieved successfully (or null if no feedback exists)',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'feedback': {
                                'type': 'object',
                                'nullable': True,
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'case_study_id': {'type': 'integer'},
                                    'user_id': {'type': 'integer'},
                                    'is_thumbs_up': {'type': 'boolean'},
                                    'is_thumbs_down': {'type': 'boolean'},
                                    'feedback_text': {'type': 'string', 'nullable': True},
                                    'created_at': {'type': 'string', 'format': 'date-time'},
                                    'updated_at': {'type': 'string', 'format': 'date-time'}
                                }
                            }
                        }
                    }
                }
            }
        },
        404: {
            'description': 'Story not found',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'},
        500: {
            'description': 'Internal server error',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
})
def get_story_feedback(case_study_id):
    """Get feedback for a specific story"""
    try:
        user_id = get_current_user_id()
        
        # Verify the case study exists and belongs to the user
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        if not case_study:
            return jsonify({'success': False, 'message': 'Story not found'}), 404
        
        # Get user's feedback for this story
        feedback = StoryFeedback.query.filter_by(
            case_study_id=case_study_id,
            user_id=user_id
        ).first()
        
        if feedback:
            return jsonify({
                'success': True,
                'feedback': feedback.to_dict()
            })
        else:
            return jsonify({
                'success': True,
                'feedback': None
            })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
