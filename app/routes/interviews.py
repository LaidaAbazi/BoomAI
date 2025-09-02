from flask import Blueprint, request, jsonify, render_template
import uuid
import os
import json
from datetime import datetime
from app.models import db, CaseStudy, SolutionProviderInterview, ClientInterview, InviteToken
from app.utils.auth_helpers import get_current_user_id, login_required
from app.services.ai_service import AIService
from app.services.case_study_service import CaseStudyService
from app.utils.text_processing import clean_text, detect_language
from io import BytesIO
from fpdf import FPDF
import requests
import re
from flasgger import swag_from

bp = Blueprint('interviews', __name__, url_prefix='/api')

@bp.route("/save_provider_summary", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Interviews'],
    'summary': 'Save provider interview summary',
    'description': 'Save the summary from a solution provider interview',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id', 'summary'],
                    'properties': {
                        'case_study_id': {'type': 'integer'},
                        'summary': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Provider summary saved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'case_study_id': {'type': 'integer'},
                            'status': {'type': 'string'}
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
def save_provider_summary():
    """Save provider interview summary"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        summary = data.get('summary', '')
        
        if not case_study_id or not summary:
            return jsonify({"error": "Missing case_study_id or summary"}), 400
        
        user_id = get_current_user_id()
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Update or create provider interview
        provider_interview = SolutionProviderInterview.query.filter_by(case_study_id=case_study_id).first()
        if not provider_interview:
            provider_interview = SolutionProviderInterview(
                case_study_id=case_study_id,
                session_id=str(uuid.uuid4()),
                summary=summary
            )
            db.session.add(provider_interview)
        else:
            provider_interview.summary = summary
        
        db.session.commit()
        
        return jsonify({
            "case_study_id": case_study.id,
            "status": "success"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route("/save_client_transcript", methods=["POST"])
def save_client_transcript():
    """Save client interview transcript"""
    try:
        data = request.get_json()
        transcript = data.get('transcript', '')
        token = data.get('token', '')
        
        if not transcript or not token:
            return jsonify({"error": "Missing transcript or token"}), 400
        
        # Find the invite token
        invite_token = InviteToken.query.filter_by(token=token, used=False).first()
        if not invite_token:
            return jsonify({"error": "Invalid or expired token"}), 400
        
        # Mark token as used
        invite_token.used = True
        
        # Create client interview record
        client_interview = ClientInterview(
            case_study_id=invite_token.case_study_id,
            session_id=str(uuid.uuid4()),
            transcript=transcript
        )
        db.session.add(client_interview)
        
        # Save transcript to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"client_session_{timestamp}.txt"
        filepath = os.path.join("client_transcripts", filename)
        
        os.makedirs("client_transcripts", exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(transcript)
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "filename": filename
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route("/generate_client_summary", methods=["POST"])
@swag_from({
    'tags': ['Interviews'],
    'summary': 'Generate client interview summary',
    'description': 'Generate a client perspective summary from client interview transcript',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['transcript', 'token'],
                    'properties': {
                        'transcript': {
                            'type': 'string',
                            'description': 'Client interview transcript text'
                        },
                        'token': {
                            'type': 'string',
                            'description': 'Client interview token'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Client summary generated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'summary': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing transcript or token'},
        404: {'description': 'Case study not found'}
    }
})
def generate_client_summary():
    """Generate summary from client interview transcript"""
    try:
        data = request.get_json()
        transcript = data.get('transcript', '')
        token = data.get('token', '')
        
        if not transcript or not token:
            return jsonify({"error": "Missing transcript or token"}), 400
        
        # Find the case study
        invite_token = InviteToken.query.filter_by(token=token).first()
        if not invite_token:
            return jsonify({"error": "Invalid token"}), 400
        
        case_study = CaseStudy.query.get(invite_token.case_study_id)
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Generate client summary using AI
        ai_service = AIService()
        client_summary = ai_service.generate_client_summary(transcript, case_study.final_summary)
        
        # Update or create client interview record
        client_interview = ClientInterview.query.filter_by(case_study_id=case_study.id).first()
        if client_interview:
            client_interview.transcript = transcript
            client_interview.summary = client_summary
        else:
            client_interview = ClientInterview(
                case_study_id=case_study.id,
                session_id=str(uuid.uuid4()),
                transcript=transcript,
                summary=client_summary
            )
            db.session.add(client_interview)
        
        db.session.commit()
        
        # ✅ Automatically generate full case study after client summary is created
        try:
            # Check if provider interview exists
            if case_study.solution_provider_interview:
                provider_interview = case_study.solution_provider_interview
                # Use the corrected final summary instead of the raw provider interview summary
                # This ensures we use the corrected names that were already processed
                corrected_provider_summary = case_study.final_summary or provider_interview.summary or ""
                detected_language = detect_language(corrected_provider_summary)
                
                # Generate full case study using the advanced service
                # FIXED: Now using corrected_provider_summary (which contains corrected names from final_summary)
                # instead of the raw provider_interview.summary (which had incorrect names)
                case_study_service = CaseStudyService()
                main_story, meta_data = case_study_service.generate_full_case_study(
                    corrected_provider_summary, client_summary, detected_language, True  # has_client_story = True
                )
                
                if main_story and main_story.strip():
                    # Update case study with final summary and metadata
                    case_study.final_summary = main_story
                    
                    # Handle bytes data in metadata before JSON serialization
                    serializable_meta_data = {}
                    for key, value in meta_data.items():
                        if key == "sentiment" and isinstance(value, dict):
                            # Handle sentiment data with bytes
                            sentiment_copy = value.copy()
                            if "visualizations" in sentiment_copy:
                                viz_copy = sentiment_copy["visualizations"].copy()
                                # Remove bytes data from JSON serialization
                                if "sentiment_chart_data" in viz_copy:
                                    del viz_copy["sentiment_chart_data"]
                                sentiment_copy["visualizations"] = viz_copy
                            serializable_meta_data[key] = sentiment_copy
                        else:
                            serializable_meta_data[key] = value
                    
                    case_study.meta_data_text = json.dumps(serializable_meta_data, ensure_ascii=False, indent=2)
                    
                    # Store sentiment chart bytes data if available
                    if "sentiment" in meta_data and "visualizations" in meta_data["sentiment"]:
                        viz_data = meta_data["sentiment"]["visualizations"]
                        if "sentiment_chart_data" in viz_data and viz_data["sentiment_chart_data"]:
                            case_study.sentiment_chart_data = viz_data["sentiment_chart_data"]
                            # Set the proper URL for the sentiment chart
                            if "sentiment_chart_img" in viz_data:
                                viz_data["sentiment_chart_img"] = f"/api/case_studies/{case_study.id}/sentiment_chart"
                    
                    # Extract names from the final summary
                    ai_service = AIService()
                    names = ai_service.extract_names_from_case_study(main_story)
                    
                    # Update case study with extracted names (but keep the title as a short hook)
                    lead_entity = names["lead_entity"]
                    partner_entity = names["partner_entity"]
                    project_title = names["project_title"]
                    
                    # Don't override the title - keep the short hook that was already generated
                    case_study.provider_name = lead_entity
                    case_study.client_name = partner_entity
                    case_study.project_name = project_title
                    
                    db.session.commit()
                    print(f"✅ Full case study automatically generated and saved for case study {case_study.id}")
                else:
                    print(f"⚠️ Failed to generate full case study content for case study {case_study.id}")
            else:
                print(f"⚠️ No provider interview found for case study {case_study.id}")
        except Exception as e:
            print(f"⚠️ Error in automatic full case study generation: {str(e)}")
            # Continue without failing the client summary generation
        
        return jsonify({
            "client_summary": client_summary,
            "status": "success",
            "case_study_id": case_study.id
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# @bp.route("/extract_names", methods=["POST"])
# @login_required
# def extract_names():
#     """Extract names from case study text"""
#     try:
#         data = request.get_json()
#         case_study_text = data.get('case_study_text', '')
#         if not case_study_text:
#             return jsonify({"error": "Missing case study text"}), 400
#         # Extract names using AI service
#         ai_service = AIService()
#         names = ai_service.extract_names_from_case_study(case_study_text)
#         # Return as flat JSON (not nested under 'names')
#         return jsonify(names)
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@bp.route("/generate_full_case_study", methods=["POST"])
@login_required
@swag_from({
    'tags': ['Interviews'],
    'summary': 'Generate full case study',
    'description': 'Generate complete case study from provider and client summaries',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['case_study_id'],
                    'properties': {
                        'case_study_id': {'type': 'integer', 'description': 'ID of the case study'},
                        'solution_provider': {'type': 'string', 'description': 'Name of the solution provider (optional)'},
                        'client_name': {'type': 'string', 'description': 'Name of the client (optional)'},
                        'project_name': {'type': 'string', 'description': 'Name of the project (optional)'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Full case study generated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'full_case_study': {'type': 'string', 'description': 'Generated case study content'},
                            'status': {'type': 'string', 'description': 'Success status'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Bad Request - Missing case_study_id or provider interview not found'},
        401: {'description': 'Not authenticated'},
        404: {'description': 'Case study not found'},
        500: {'description': 'Internal server error - Failed to generate case study'}
    }
})
def generate_full_case_study():
    """Generate complete case study from provider and client summaries"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        # Get edited names from frontend if provided
        solution_provider = data.get("solution_provider")
        client_name = data.get("client_name") 
        project_name = data.get("project_name")
        
        if not case_study_id:
            return jsonify({"error": "Missing case_study_id"}), 400
        
        user_id = get_current_user_id()
        case_study = CaseStudy.query.filter_by(id=case_study_id, user_id=user_id).first()
        
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
        
        # Check if provider interview exists
        if not case_study.solution_provider_interview:
            return jsonify({"error": "Provider interview not found. Please complete the provider interview first."}), 400
        
        provider_interview = case_study.solution_provider_interview
        client_interview = case_study.client_interview
        
        # FIXED: Use corrected final_summary when available instead of raw provider_interview.summary
        # This ensures we use the corrected names that were already processed
        corrected_provider_summary = case_study.final_summary or provider_interview.summary or ""
        client_summary = client_interview.summary if client_interview else ""
        detected_language = detect_language(corrected_provider_summary)
        print(detected_language)
        
        # Check if client story exists
        has_client_story = bool(client_interview and client_summary.strip())
        
        # Generate full case study using the advanced service
        # FIXED: Now using corrected_provider_summary (which contains corrected names from final_summary)
        # instead of the raw provider_interview.summary (which had incorrect names)
        case_study_service = CaseStudyService()
        main_story, meta_data = case_study_service.generate_full_case_study(
            corrected_provider_summary, client_summary, detected_language, has_client_story
        )
        
        if not main_story or main_story.strip() == "":
            return jsonify({"error": "Failed to generate case study content"}), 500
        
        # Update case study with final summary and metadata
        case_study.final_summary = main_story
        
        # Handle bytes data in metadata before JSON serialization
        serializable_meta_data = {}
        for key, value in meta_data.items():
            if key == "sentiment" and isinstance(value, dict):
                # Handle sentiment data with bytes
                sentiment_copy = value.copy()
                if "visualizations" in sentiment_copy:
                    viz_copy = sentiment_copy["visualizations"].copy()
                    # Remove bytes data from JSON serialization
                    if "sentiment_chart_data" in viz_copy:
                        del viz_copy["sentiment_chart_data"]
                    sentiment_copy["visualizations"] = viz_copy
                serializable_meta_data[key] = sentiment_copy
            else:
                serializable_meta_data[key] = value
        
        case_study.meta_data_text = json.dumps(serializable_meta_data, ensure_ascii=False, indent=2)
        
        # Store sentiment chart bytes data if available
        if "sentiment" in meta_data and "visualizations" in meta_data["sentiment"]:
            viz_data = meta_data["sentiment"]["visualizations"]
            if "sentiment_chart_data" in viz_data and viz_data["sentiment_chart_data"]:
                case_study.sentiment_chart_data = viz_data["sentiment_chart_data"]
                # Set the proper URL for the sentiment chart
                if "sentiment_chart_img" in viz_data:
                    viz_data["sentiment_chart_img"] = f"/api/case_studies/{case_study.id}/sentiment_chart"
        
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
            ai_service = AIService()
            names = ai_service.extract_names_from_case_study(main_story)
            print(f"✅ Using extracted names from final summary: {names}")
        
        # Update case study with extracted names (but keep the title as a short hook)
        lead_entity = names["lead_entity"]
        partner_entity = names["partner_entity"]
        project_title = names["project_title"]
        
        # Don't override the title - keep the short hook that was already generated
        case_study.provider_name = lead_entity
        case_study.client_name = partner_entity
        case_study.project_name = project_title
        
        # Generate PDF and store in DB
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            
            # Clean the text to remove any problematic characters
            cleaned_text = main_story.encode('latin-1', 'replace').decode('latin-1')
            
            for line in cleaned_text.split("\n"):
                # Limit line length to prevent PDF generation issues
                if len(line) > 100:
                    # Split long lines
                    words = line.split()
                    current_line = ""
                    for word in words:
                        if len(current_line + " " + word) <= 100:
                            current_line += (" " + word) if current_line else word
                        else:
                            if current_line:
                                pdf.multi_cell(0, 10, current_line)
                            current_line = word
                    if current_line:
                        pdf.multi_cell(0, 10, current_line)
                else:
                    pdf.multi_cell(0, 10, line)
            
            # Generate PDF as bytes - compatible with all FPDF versions
            pdf_buffer = BytesIO()
            pdf.output(pdf_buffer, 'S')
            case_study.final_summary_pdf_data = pdf_buffer.getvalue()
        except Exception as pdf_error:
            print(f"PDF generation error: {pdf_error}")
            # Continue without PDF if generation fails
        
        db.session.commit()
        
        return jsonify({
            "full_case_study": main_story,
            "status": "success"
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error in generate_full_case_study: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

@bp.route("/extract_interviewee_name", methods=["POST"])
@swag_from({
    'tags': ['Interviews'],
    'summary': 'Extract interviewee name',
    'description': 'Extract interviewee name from transcript using AI/LLM with fallback to regex',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['transcript'],
                    'properties': {
                        'transcript': {
                            'type': 'string',
                            'description': 'Interview transcript text'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Name extracted successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'name': {'type': 'string'},
                            'method': {'type': 'string'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing transcript'}
    }
})
def extract_interviewee_name():
    """Extract interviewee name from transcript using AI/LLM with fallback to regex"""
    try:
        data = request.get_json()
        transcript = data.get('transcript', '')
        
        if not transcript:
            return jsonify({"status": "error", "message": "Missing transcript"}), 400
        
        # First try LLM extraction for maximum accuracy
        ai_service = AIService()
        
        try:
            # Use OpenAI to extract the interviewee name
            prompt = f"""Extract the name of the person being interviewed from this transcript. 
            
            Look for patterns like:
            - "My name is [name]"
            - "I'm [name]" or "I am [name]"
            - "USER: [name]" (if it's just a name)
            - Any other clear introduction of the person's name
            
            Transcript:
            {transcript}
            
            Return ONLY the name as a simple string, nothing else. If no name is found, return an empty string."""
            
            headers = {
                "Authorization": f"Bearer {ai_service.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": ai_service.openai_config["model"],
                "messages": [{"role": "system", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 50
            }
            
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if "choices" in result and len(result["choices"]) > 0:
                    extracted_name = result["choices"][0]["message"]["content"].strip()
                    
                    # Clean up the response - remove quotes if present
                    extracted_name = extracted_name.strip('"').strip("'").strip()
                    
                    if extracted_name and extracted_name.lower() not in ["unknown", "none", "empty", "no name found"]:
                        return jsonify({
                            "status": "success",
                            "name": extracted_name,
                            "method": "LLM"
                        })
            
        except Exception as llm_error:
            print(f"LLM extraction failed: {llm_error}")
        
        # Fallback to regex extraction
        lines = transcript.split('\n')
        regex_method_used = None
        
        for line in lines:
            if line.startswith('USER:'):
                # Pattern 1: "My name is [name]"
                name_match = re.search(r'my name is ([^,.]+)', line, re.IGNORECASE)
                if name_match:
                    return jsonify({
                        "status": "success",
                        "name": name_match.group(1).strip(),
                        "method": "Regex - 'my name is'"
                    })
                
                # Pattern 2: "I'm [name]" or "I am [name]"
                name_match = re.search(r"i'?m ([^,.]+)", line, re.IGNORECASE) or re.search(r"i am ([^,.]+)", line, re.IGNORECASE)
                if name_match:
                    return jsonify({
                        "status": "success",
                        "name": name_match.group(1).strip(),
                        "method": "Regex - 'I'm/I am'"
                    })
                
                # Pattern 3: Just a name after "USER:" (for cases like "USER: Lajda.")
                name_match = re.search(r'^USER:\s*([A-Za-z]+)', line)
                if name_match and 'work' not in line.lower() and 'company' not in line.lower():
                    return jsonify({
                        "status": "success",
                        "name": name_match.group(1).strip(),
                        "method": "Regex - 'USER: [name]'"
                    })
        
        # No name found
        return jsonify({
            "status": "success",
            "name": "",
            "method": "No name found"
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# REMOVED: Duplicate client-interview route - this is handled in main.py 
