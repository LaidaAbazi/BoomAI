from flask import Blueprint, request, jsonify
from app.models import db, Feedback, CaseStudy
from app.utils.auth_helpers import get_current_user_id, login_required
import uuid
from datetime import datetime

bp = Blueprint('api', __name__, url_prefix='/api')

# Initialize feedback sessions dictionary
feedback_sessions = {}

@bp.route('/feedback/start', methods=['POST'])
@login_required
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
        
        return jsonify({
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route('/feedback/history', methods=['GET'])
@login_required
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

@bp.route("/save_final_summary", methods=["POST"])
@login_required
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