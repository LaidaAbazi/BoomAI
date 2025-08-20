from flask import Blueprint, request, jsonify, send_file, send_from_directory
import os
import json
import re
import uuid
from datetime import datetime, UTC
from fpdf import FPDF
from docx import Document
from docx.shared import Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from app.models import db, CaseStudy, SolutionProviderInterview, ClientInterview, InviteToken, Label
from app.utils.auth_helpers import get_current_user_id, login_required
from app.services.ai_service import AIService
from app.services.case_study_service import CaseStudyService
from app.utils.text_processing import clean_text, detect_language
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
        label_id = request.args.get('label', type=int)
        
        query = CaseStudy.query.filter_by(user_id=user_id)
        if label_id:
            query = query.join(CaseStudy.labels).filter(Label.id == label_id)
        
        case_studies = query.all()
        case_studies_data = []
        
        for case_study in case_studies:
            case_study_data = {
                'id': case_study.id,
                'title': case_study.title,
                'final_summary': case_study.final_summary,
                'meta_data_text': case_study.meta_data_text,
                'solution_provider_summary': case_study.solution_provider_interview.summary if case_study.solution_provider_interview else None,
                'client_summary': case_study.client_interview.summary if case_study.client_interview else None,
                'client_link_url': case_study.solution_provider_interview.client_link_url if case_study.solution_provider_interview else None,
                'created_at': case_study.created_at.isoformat(),
                'updated_at': case_study.updated_at.isoformat(),
                'video_status': case_study.video_status,
                'pictory_video_status': case_study.pictory_video_status,
                'podcast_status': case_study.podcast_status,
                'labels': [{'id': l.id, 'name': l.name} for l in case_study.labels],
                'video_url': case_study.video_url,
                'video_id': case_study.video_id,
                'video_created_at': case_study.video_created_at.isoformat() if case_study.video_created_at else None,
                'pictory_video_url': case_study.pictory_video_url,
                'pictory_storyboard_id': case_study.pictory_storyboard_id,
                'pictory_render_id': case_study.pictory_render_id,
                'pictory_video_created_at': case_study.pictory_video_created_at.isoformat() if case_study.pictory_video_created_at else None,
                'podcast_url': case_study.podcast_url,
                'podcast_job_id': case_study.podcast_job_id,
                'podcast_script': case_study.podcast_script,
                'podcast_created_at': case_study.podcast_created_at.isoformat() if case_study.podcast_created_at else None,
                'linkedin_post': case_study.linkedin_post,
            }
            case_studies_data.append(case_study_data)
        
        return jsonify({'success': True, 'case_studies': case_studies_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/case_studies/<int:case_study_id>', methods=['GET'])
@login_required
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
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        
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
            'created_at': case_study.created_at.isoformat(),
            'updated_at': case_study.updated_at.isoformat(),
            'video_status': case_study.video_status,
            'pictory_video_status': case_study.pictory_video_status,
            'podcast_status': case_study.podcast_status,
            'labels': [{'id': l.id, 'name': l.name} for l in case_study.labels],
            'video_url': case_study.video_url,
            'video_id': case_study.video_id,
            'video_created_at': case_study.video_created_at.isoformat() if case_study.video_created_at else None,
            'pictory_video_url': case_study.pictory_video_url,
            'pictory_storyboard_id': case_study.pictory_storyboard_id,
            'pictory_render_id': case_study.pictory_render_id,
            'pictory_video_created_at': case_study.pictory_video_created_at.isoformat() if case_study.pictory_video_created_at else None,
            'podcast_url': case_study.podcast_url,
            'podcast_job_id': case_study.podcast_job_id,
            'podcast_script': case_study.podcast_script,
            'podcast_created_at': case_study.podcast_created_at.isoformat() if case_study.podcast_created_at else None,
            'linkedin_post': case_study.linkedin_post,
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
                                'items': {'$ref': '#/components/schemas/Label'}
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
        labels_data = [{'id': l.id, 'name': l.name} for l in labels]
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
        
        return jsonify({'success': True, 'label': {'id': label.id, 'name': label.name}})
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
        
        return jsonify({'success': True, 'label': {'id': label.id, 'name': label.name}})
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

@bp.route('/case_studies/<int:case_study_id>/labels', methods=['POST'])
@login_required
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
        return jsonify({'success': True, 'labels': [{'id': l.id, 'name': l.name} for l in case_study.labels]})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route('/case_studies/<int:case_study_id>/labels/<int:label_id>', methods=['DELETE'])
@login_required
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
        
        return jsonify({'success': True, 'labels': [{'id': l.id, 'name': l.name} for l in case_study.labels]})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@bp.route("/generate_linkedin_post", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Case Studies'],
    'summary': 'Generate LinkedIn post',
    'description': 'Generate a LinkedIn post from case study content',
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
            'description': 'LinkedIn post generated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'linkedin_post': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing case study ID or no final summary'},
        404: {'description': 'Case study not found'},
        500: {'description': 'Error generating LinkedIn post'}
    }
})
def generate_linkedin_post():
    """Generate LinkedIn post from case study"""
    try:
        data = request.get_json()
        case_study_id = data.get("case_study_id")

        if not case_study_id:
            return jsonify({"status": "error", "message": "Missing case_study_id"}), 400

        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404

        if not case_study.final_summary:
            return jsonify({"status": "error", "message": "No final summary available"}), 400

        # Generate LinkedIn post
        ai_service = AIService()
        linkedin_post = ai_service.generate_linkedin_post(case_study.final_summary)
        
        # Check if generation was successful
        if linkedin_post.startswith("Failed to generate") or linkedin_post.startswith("Error generating") or linkedin_post.startswith("AI service not available"):
            return jsonify({
                "status": "error", 
                "message": linkedin_post
            }), 500
        
        # Save to database
        case_study.linkedin_post = linkedin_post
        db.session.commit()

        return jsonify({
            "status": "success",
            "linkedin_post": linkedin_post
        })

    except Exception as e:
        db.session.rollback()
        print(f"Error in generate_linkedin_post route: {str(e)}")
        return jsonify({"status": "error", "message": f"Error generating LinkedIn post: {str(e)}"}), 500

@bp.route("/save_as_word", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Summary'],
    'summary': 'Generate Word document',
    'description': 'Generate Word document from case study',
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
            'description': 'Word document file path',
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
        400: {'description': 'Missing case_study_id'}
    }
})
def save_as_word():
    """Save case study as Word document and store in DB"""
    try:
        data = request.get_json()
        case_study_id = data.get("case_study_id")
        final_summary = data.get("final_summary")
        title = data.get("title", "Case Study")

        if not case_study_id or not final_summary:
            return jsonify({"status": "error", "message": "Missing case_study_id or final_summary"}), 400

        # Create Word document using python-docx
        doc = Document()
        
        # Add title
        title_para = doc.add_paragraph()
        title_run = title_para.add_run(title)
        title_run.bold = True
        title_run.font.size = Inches(0.5)
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        # Add some spacing
        doc.add_paragraph()
        
        # Add the final summary content
        lines = final_summary.split('\n')
        for line in lines:
            if line.strip():  # Only add non-empty lines
                # Check if it's a header (all caps or starts with **)
                if line.strip().isupper() or line.strip().startswith('**'):
                    # It's a header
                    header_para = doc.add_paragraph()
                    header_run = header_para.add_run(line.strip().replace('**', ''))
                    header_run.bold = True
                    header_run.font.size = Inches(0.3)
                else:
                    # It's regular content
                    para = doc.add_paragraph()
                    para.add_run(line.strip())
        
        # Save to BytesIO buffer
        word_buffer = BytesIO()
        doc.save(word_buffer)
        word_data = word_buffer.getvalue()

        # Store in DB
        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404
        case_study.final_summary_word_data = word_data
        db.session.commit()

        # Return the file
        word_buffer.seek(0)
        return send_file(
            word_buffer,
            as_attachment=True,
            download_name=f"{title.replace(' ', '_')}_{case_study_id}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

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

@bp.route("/generate_full_case_study", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Summary'],
    'summary': 'Generate full case study',
    'description': 'Generate the complete final case study from provider and client interviews',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id'],
                    'properties': {
                        'case_study_id': {'type': 'integer'},
                        'solution_provider': {'type': 'string'},
                        'client_name': {'type': 'string'},
                        'project_name': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Full case study generated',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'text': {'type': 'string'},
                            'pdf_url': {'type': 'string'},
                            'word_url': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing or invalid data'},
        404: {'description': 'Case study not found'}
    }
})
def generate_full_case_study():
    """Generate the complete final case study"""
    try:
        data = request.get_json()
        case_study_id = data.get("case_study_id")
        # Get edited names from frontend if provided
        solution_provider = data.get("solution_provider")
        client_name = data.get("client_name") 
        project_name = data.get("project_name")

        if not case_study_id:
            return jsonify({"status": "error", "message": "Missing case_study_id"}), 400

        case_study = CaseStudy.query.filter_by(id=case_study_id).first()
        if not case_study:
            return jsonify({"status": "error", "message": "Case study not found"}), 404

        provider_interview = case_study.solution_provider_interview
        client_interview = case_study.client_interview

        if not provider_interview:
            return jsonify({"status": "error", "message": "Provider summary is required."}), 400

        provider_summary = provider_interview.summary or ""
        client_summary = client_interview.summary if client_interview else ""
        detected_language = detect_language(provider_summary)
        
        # Check if client story exists
        has_client_story = bool(client_interview and client_summary.strip())
        
        # Add detailed debugging for client summary
        print(f"🔍 Case study generation debugging:")
        print(f"   Provider summary length: {len(provider_summary)}")
        print(f"   Client summary length: {len(client_summary) if client_summary else 0}")
        print(f"   Has client interview: {bool(client_interview)}")
        print(f"   Has client story: {has_client_story}")
        if client_summary:
            print(f"   Client summary preview: {client_summary[:100]}...")
        else:
            print(f"   ❌ No client summary available")
        
        # Generate the full case study using AI service
        ai_service = AIService()
        case_study_service = CaseStudyService()
        
        main_story, meta_data = case_study_service.generate_full_case_study(
            provider_summary, client_summary, detected_language, has_client_story
        )
        
        # Extract and save sentiment chart data if present
        sentiment_chart_data = None
        if meta_data.get('sentiment', {}).get('visualizations', {}).get('sentiment_chart_data'):
            sentiment_chart_data = meta_data['sentiment']['visualizations'].pop('sentiment_chart_data')
            print(f"🔍 Extracted sentiment chart data: {len(sentiment_chart_data)} bytes")
        
        # Debug: Print metadata for troubleshooting
        print(f"🔍 Generated metadata for case study {case_study_id}:")
        print(f"   Meta data keys: {list(meta_data.keys()) if meta_data else 'None'}")
        print(f"   Quote highlights length: {len(meta_data.get('quote_highlights', '')) if meta_data else 0}")
        print(f"   Client takeaways length: {len(meta_data.get('client_takeaways', '')) if meta_data else 0}")
        print(f"   Sentiment data: {bool(meta_data.get('sentiment')) if meta_data else False}")
        
        # Add detailed sentiment debugging
        if meta_data and meta_data.get('sentiment'):
            sentiment = meta_data['sentiment']
            print(f"   🔍 Sentiment details:")
            print(f"      Overall sentiment: {sentiment.get('overall_sentiment', {}).get('sentiment', 'unknown')}")
            print(f"      Score: {sentiment.get('overall_sentiment', {}).get('score', 0)}")
            print(f"      Has visualizations: {bool(sentiment.get('visualizations'))}")
            if sentiment.get('visualizations'):
                viz = sentiment['visualizations']
                print(f"      Sentiment chart img: {viz.get('sentiment_chart_img', 'missing')}")
                print(f"      Client satisfaction gauge: {bool(viz.get('client_satisfaction_gauge'))}")
        else:
            print(f"   ❌ No sentiment data found in metadata")
            print(f"   🔍 Client summary provided: {bool(client_summary)}")
            print(f"   🔍 Client summary length: {len(client_summary) if client_summary else 0}")
        
        # Update case study
        case_study.final_summary = main_story
        
        # Save sentiment chart data if present
        if sentiment_chart_data:
            case_study.sentiment_chart_data = sentiment_chart_data
            print(f"🔍 Saved sentiment chart data to database: {len(sentiment_chart_data)} bytes")
            
            # Update the URL in metadata to use the case study ID
            if meta_data.get('sentiment', {}).get('visualizations', {}).get('sentiment_chart_img') == "PENDING_CASE_STUDY_ID":
                meta_data['sentiment']['visualizations']['sentiment_chart_img'] = f"/api/sentiment_chart/{case_study.id}"
                print(f"🔍 Updated sentiment chart URL to: {meta_data['sentiment']['visualizations']['sentiment_chart_img']}")
        
        # Debug: Check metadata size and content
        print(f"🔍 Metadata size before JSON serialization: {len(str(meta_data))}")
        if meta_data.get('sentiment', {}).get('visualizations'):
            viz = meta_data['sentiment']['visualizations']
            print(f"🔍 Sentiment chart img size: {len(str(viz.get('sentiment_chart_img', '')))}")
            print(f"🔍 Client satisfaction gauge size: {len(str(viz.get('client_satisfaction_gauge', '')))}")
        
        try:
            meta_data_json = json.dumps(meta_data, ensure_ascii=False, indent=2)
            print(f"🔍 JSON serialization successful, size: {len(meta_data_json)}")
            case_study.meta_data_text = meta_data_json
        except Exception as json_error:
            print(f"❌ JSON serialization error: {str(json_error)}")
            # Try without the gauge if it's causing issues
            if meta_data.get('sentiment', {}).get('visualizations', {}).get('client_satisfaction_gauge'):
                print("🔍 Attempting to save metadata without gauge...")
                meta_data['sentiment']['visualizations'].pop('client_satisfaction_gauge', None)
                case_study.meta_data_text = json.dumps(meta_data, ensure_ascii=False, indent=2)
            else:
                raise json_error
        
        # Use edited names from frontend if provided, otherwise extract from final summary
        if solution_provider and client_name and project_name:
            names = {
                "lead_entity": solution_provider,
                "partner_entity": client_name,
                "project_title": project_name
            }
            print(f"✅ Using edited names from frontend for full case study: {names}")
        else:
            # Extract names from the final summary
            names = ai_service.extract_names_from_case_study(main_story)
            print(f"✅ Using extracted names from final summary: {names}")
        
        # Update case study with extracted names (but don't use old format for title)
        lead_entity = names["lead_entity"]
        partner_entity = names["partner_entity"]
        project_title = names["project_title"]
        
        # Keep the title as is (it should be a short hook, not the old format)
        # The title is already set from the initial generation
        case_study.provider_name = lead_entity
        case_study.client_name = partner_entity
        case_study.project_name = project_title

        # Generate PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"final_case_study_{timestamp}.pdf"
        pdf_path = os.path.join("generated_pdfs", pdf_filename)
        os.makedirs("generated_pdfs", exist_ok=True)

        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Add title in bold at the top
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, case_study.title, ln=True, align='C')
        pdf.ln(10)
        
        # Add case study content
        pdf.set_font("Arial", size=12)
        for line in main_story.split("\n"):
            pdf.multi_cell(0, 10, line)

        pdf_buffer = BytesIO()
        pdf.output(pdf_buffer, 'S')
        case_study.final_summary_pdf_data = pdf_buffer.getvalue()
        
        # Generate Word document
        word_path = case_study_service.generate_word_document(case_study)
        word_filename = os.path.basename(word_path) if word_path else None
        
        db.session.commit()

        return jsonify({
            "status": "success",
            "text": main_story,
            "pdf_url": f"/download/{pdf_filename}",
            "word_url": f"/download/{word_filename}" if word_filename else None
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

@bp.route("/extract_names", methods=["POST"])
@login_required
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

        # Update final summary
        case_study.final_summary = final_summary

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

        # Update CaseStudy name fields (but keep title as is - it should be a short hook)
        case_study.provider_name = lead_entity
        case_study.client_name = partner_entity
        case_study.project_name = project_title

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
            pdf.multi_cell(0, 10, title, align='C')
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
            pdf.multi_cell(0, 10, summary_text)

        # Save PDF to database (not filesystem)
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        case_study.final_summary_pdf_data = pdf_bytes
        db.session.commit()

        # Return the file directly
        pdf_buffer = BytesIO(pdf_bytes)
        pdf_buffer.seek(0)

        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=f"{case_study.title or 'Case_Study'}.pdf",
            mimetype='application/pdf'
        )
    except Exception as e:
        db.session.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500

 