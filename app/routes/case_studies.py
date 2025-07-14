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

bp = Blueprint('case_studies', __name__, url_prefix='/api')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
GENERATED_PDFS_DIR = os.path.join(BASE_DIR, 'generated_pdfs')

@bp.route('/case_studies', methods=['GET'])
@login_required
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
        
        # Generate the full case study using AI service
        ai_service = AIService()
        case_study_service = CaseStudyService()
        
        main_story, meta_data = case_study_service.generate_full_case_study(
            provider_summary, client_summary, detected_language, has_client_story
        )
        
        # Update case study
        case_study.final_summary = main_story
        case_study.meta_data_text = json.dumps(meta_data, ensure_ascii=False, indent=2)
        
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
        
        # Update case study title with the correct names
        lead_entity = names["lead_entity"]
        partner_entity = names["partner_entity"]
        project_title = names["project_title"]
        new_title = f"{lead_entity} x {partner_entity}: {project_title}"
        
        case_study.title = new_title
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
        pdf.set_font("Arial", size=12)
        for line in main_story.split("\n"):
            pdf.multi_cell(0, 10, line)

        pdf_buffer = BytesIO()
        pdf.output(pdf_buffer, 'S')
        case_study.final_summary_pdf_data = pdf_buffer.getvalue()
        db.session.commit()

        return jsonify({
            "status": "success",
            "text": main_story,
            "pdf_url": f"/download/{pdf_filename}"
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
        new_title = f"{lead_entity} x {partner_entity}: {project_title}"

        # Update CaseStudy title and name fields
        case_study.title = new_title
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
def generate_pdf():
    """Generate PDF from existing final summary - always regenerates with latest content"""
    try:
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
        pdf.set_auto_page_break(auto=True, margin=15)
        try:
            # Add title
            pdf.set_font("Arial", 'B', 16)
            title = case_study.title or "Case Study"
            clean_title = title.encode('latin-1', 'replace').decode('latin-1')
            pdf.cell(0, 10, clean_title, ln=True, align='C')
            pdf.ln(5)
            # Add final summary content
            pdf.set_font("Arial", size=12)
            summary_lines = case_study.final_summary.split('\n')
            for line in summary_lines:
                clean_line = line.encode('latin-1', 'replace').decode('latin-1')
                pdf.multi_cell(0, 10, clean_line)
        except Exception as pdf_error:
            print(f"❌ PDF generation error: {str(pdf_error)}")
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.multi_cell(0, 10, "Case Study PDF")
            pdf.ln(10)
            pdf.multi_cell(0, 10, case_study.final_summary[:1000] + "..." if len(case_study.final_summary) > 1000 else case_study.final_summary)

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

 