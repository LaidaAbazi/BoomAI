from flask import Blueprint, request, jsonify
from app.services.metadata_service import MetadataService
from app.models import db, CaseStudy
from flask import session
import json
from flasgger import swag_from

metadata_bp = Blueprint('metadata', __name__)
metadata_service = MetadataService()

@metadata_bp.route('/api/metadata/analyze', methods=['POST'])
@swag_from({
    'tags': ['Metadata'],
    'summary': 'Analyze metadata',
    'description': 'Analyze metadata for a case study',
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
            'description': 'Metadata analysis completed',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'metadata': {'type': 'object'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Bad Request'},
        404: {'description': 'Case study not found'}
    }
})
def analyze_metadata():
    """Analyze metadata for a case study"""
    try:
        data = request.get_json()
        case_study_id = data.get('case_study_id')
        
        if not case_study_id:
            return jsonify({"error": "Case study ID is required"}), 400
            
        # Get case study
        case_study = CaseStudy.query.get(case_study_id)
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
            
        # Get client summary if available
        client_summary = None
        if case_study.client_interview:
            client_summary = case_study.client_interview.summary
            
        # Generate metadata
        metadata = metadata_service.generate_metadata_summary(
            case_study.final_summary or "", 
            client_summary
        )
        
        return jsonify({
            "status": "success",
            "metadata": metadata
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@metadata_bp.route('/api/metadata/regenerate/<int:case_study_id>', methods=['POST'])
@swag_from({
    'tags': ['Metadata'],
    'summary': 'Regenerate metadata',
    'description': 'Regenerate metadata for an existing case study',
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
            'description': 'Metadata regenerated successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'message': {'type': 'string'},
                            'metadata': {'type': 'object'}
                        }
                    }
                }
            }
        },
        404: {'description': 'Case study not found'}
    }
})
def regenerate_metadata(case_study_id):
    """Regenerate metadata for an existing case study"""
    try:
        # Get case study
        case_study = CaseStudy.query.get(case_study_id)
        if not case_study:
            return jsonify({"error": "Case study not found"}), 404
            
        # Get client summary if available
        client_summary = None
        if case_study.client_interview:
            client_summary = case_study.client_interview.summary
            
        # Generate metadata
        metadata = metadata_service.generate_metadata_summary(
            case_study.final_summary or "", 
            client_summary
        )
        
        # Extract and save sentiment chart data if present
        sentiment_chart_data = None
        if metadata.get('sentiment', {}).get('visualizations', {}).get('sentiment_chart_data'):
            sentiment_chart_data = metadata['sentiment']['visualizations'].pop('sentiment_chart_data')
            print(f"🔍 Extracted sentiment chart data: {len(sentiment_chart_data)} bytes")
            
            # Save to database
            case_study.sentiment_chart_data = sentiment_chart_data
            
            # Update the URL in metadata to use the case study ID
            if metadata.get('sentiment', {}).get('visualizations', {}).get('sentiment_chart_img') == "PENDING_CASE_STUDY_ID":
                metadata['sentiment']['visualizations']['sentiment_chart_img'] = f"/api/sentiment_chart/{case_study.id}"
                print(f"🔍 Updated sentiment chart URL to: {metadata['sentiment']['visualizations']['sentiment_chart_img']}")
        
        # Update case study with new metadata
        case_study.meta_data_text = json.dumps(metadata, ensure_ascii=False, indent=2)
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Metadata regenerated successfully",
            "metadata": metadata
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@metadata_bp.route('/api/metadata/sentiment', methods=['POST'])
@swag_from({
    'tags': ['Metadata'],
    'summary': 'Analyze sentiment',
    'description': 'Analyze sentiment of text',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['text'],
                    'properties': {
                        'text': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Sentiment analysis completed',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'sentiment': {'type': 'object'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Text is required'}
    }
})
def analyze_sentiment():
    """Analyze sentiment of text"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({"error": "Text is required"}), 400
            
        sentiment = metadata_service.analyze_sentiment(text)
        
        return jsonify({
            "status": "success",
            "sentiment": sentiment
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@metadata_bp.route('/api/metadata/satisfaction', methods=['POST'])
@swag_from({
    'tags': ['Metadata'],
    'summary': 'Analyze client satisfaction',
    'description': 'Analyze client satisfaction from client summary',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['client_summary'],
                    'properties': {
                        'client_summary': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Satisfaction analysis completed',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'satisfaction': {'type': 'object'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Client summary is required'}
    }
})
def analyze_satisfaction():
    """Analyze client satisfaction"""
    try:
        data = request.get_json()
        client_summary = data.get('client_summary')
        
        if not client_summary:
            return jsonify({"error": "Client summary is required"}), 400
            
        satisfaction = metadata_service.extract_client_satisfaction(client_summary)
        
        return jsonify({
            "status": "success",
            "satisfaction": satisfaction
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@metadata_bp.route('/api/metadata/takeaways', methods=['POST'])
@swag_from({
    'tags': ['Metadata'],
    'summary': 'Extract client takeaways',
    'description': 'Extract client takeaways from client summary',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['client_summary'],
                    'properties': {
                        'client_summary': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Takeaways extracted successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'takeaways': {'type': 'object'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Client summary is required'}
    }
})
def extract_takeaways():
    """Extract client takeaways"""
    try:
        data = request.get_json()
        client_summary = data.get('client_summary')
        
        if not client_summary:
            return jsonify({"error": "Client summary is required"}), 400
            
        takeaways = metadata_service.extract_client_takeaways(client_summary)
        
        return jsonify({
            "status": "success",
            "takeaways": takeaways
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@metadata_bp.route('/api/metadata/quotes', methods=['POST'])
@swag_from({
    'tags': ['Metadata'],
    'summary': 'Extract quotes',
    'description': 'Extract quotes from text',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['text'],
                    'properties': {
                        'text': {'type': 'string'}
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Quotes extracted successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'quotes': {'type': 'object'}
                        }
                    }
                }
            }
        },
        400: {'description': 'Text is required'}
    }
})
def extract_quotes():
    """Extract quotes from text"""
    try:
        data = request.get_json()
        text = data.get('text')
        
        if not text:
            return jsonify({"error": "Text is required"}), 400
            
        quotes = metadata_service.extract_quotes_from_text(text)
        
        return jsonify({
            "status": "success",
            "quotes": quotes
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500 