from flask import Blueprint, request, jsonify, current_app
from app.models import db, Feedback, CaseStudy, User
from app.utils.auth_helpers import get_current_user_id, login_required, subscription_required
from app.services.feedback_service import FeedbackService
import uuid
from datetime import datetime, date
from flasgger import swag_from
import os
# STRIPE IMPLEMENTATION COMMENTED OUT - Keep for future use
# import stripe
import json

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

@bp.route('/feedback/transcript', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Feedback'],
    'summary': 'Get feedback transcript',
    'description': 'Get feedback transcript for real-time feedback collection',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['session_id'],
                    'properties': {
                        'session_id': {
                            'type': 'string',
                            'description': 'Feedback session ID'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Feedback transcript retrieved',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'transcript': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'speaker': {'type': 'string'},
                                        'text': {'type': 'string'},
                                        'timestamp': {'type': 'string'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {'description': 'Missing session_id'},
        404: {'description': 'Session not found'},
        401: {'description': 'Not authenticated'}
    }
})
def get_feedback_transcript():
    """Get feedback transcript"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({"error": "Session ID is required"}), 400
        
        # For now, return empty transcript since we don't store real-time transcripts
        # This endpoint is used by the frontend to get the transcript during feedback collection
        return jsonify({
            'transcript': []
        })
        
    except Exception as e:
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

# STRIPE IMPLEMENTATION COMMENTED OUT - Keep for future use
# @bp.route('/stripe/webhook', methods=['POST'])
# @swag_from({
#     'tags': ['Stripe'],
#     'summary': 'Handle Stripe webhook events',
#     'description': 'Process Stripe webhook events for payment completion and subscription activation',
#     'responses': {
#         200: {'description': 'Webhook processed successfully'},
#         400: {'description': 'Invalid payload or signature'},
#         500: {'description': 'Internal server error'}
#     }
# })
# def stripe_webhook():
#     """Handle Stripe webhook events"""
#     try:
#         print("Webhook received!")
#         
#         # Check if Stripe is configured
#         webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
#         secret_key = current_app.config.get('STRIPE_SECRET_KEY')
#         
#         print(f"DEBUG: STRIPE_WEBHOOK_SECRET = {webhook_secret[:10] if webhook_secret else 'None'}...")
#         print(f"DEBUG: STRIPE_SECRET_KEY = {secret_key[:10] if secret_key else 'None'}...")
#         
#         if not webhook_secret:
#             print("ERROR: STRIPE_WEBHOOK_SECRET not configured")
#             return jsonify({"error": "Stripe webhook secret not configured"}), 500
#         
#         if not secret_key:
#             print("ERROR: STRIPE_SECRET_KEY not configured")
#             return jsonify({"error": "Stripe secret key not configured"}), 500
#         
#         payload = request.get_data()
#         sig_header = request.headers.get('Stripe-Signature')
#         
#         print(f"Payload length: {len(payload)}")
#         print(f"Signature header: {sig_header}")
#         
#         # Verify webhook signature
#         event = stripe.Webhook.construct_event(
#             payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
#         )
#         
#         print(f"Event type: {event['type']}")
#         
#         # Handle the event
#         if event['type'] == 'checkout.session.completed':
#             session = event['data']['object']
#             print(f"Handling checkout.session.completed for session: {session.get('id')}")
#             handle_successful_payment(session)
#         elif event['type'] == 'invoice.payment_succeeded':
#             invoice = event['data']['object']
#             print(f"Handling invoice.payment_succeeded for invoice: {invoice.get('id')}")
#             handle_subscription_payment(invoice)
#         elif event['type'] == 'customer.subscription.deleted':
#             subscription = event['data']['object']
#             print(f"Handling customer.subscription.deleted for subscription: {subscription.get('id')}")
#             handle_subscription_cancellation(subscription)
#         elif event['type'] == 'customer.subscription.updated':
#             subscription = event['data']['object']
#             print(f"Handling customer.subscription.updated for subscription: {subscription.get('id')}")
#             handle_subscription_update(subscription)
#         else:
#             print(f"Unhandled event type: {event['type']}")
#         
#         print("Webhook processed successfully")
#         return jsonify({"status": "success"})
#         
#     except ValueError as e:
#         print(f"ValueError: {str(e)}")
#         return jsonify({"error": "Invalid payload"}), 400
#     except stripe.error.SignatureVerificationError as e:
#         print(f"SignatureVerificationError: {str(e)}")
#         return jsonify({"error": "Invalid signature"}), 400
#     except Exception as e:
#         print(f"Unexpected error: {str(e)}")
#         return jsonify({"error": str(e)}), 500

@bp.route('/credits/status', methods=['GET'])
@login_required
@swag_from({
    'tags': ['Credits'],
    'summary': 'Get user credit status',
    'description': 'Get current story usage and credit status for the authenticated user',
    'responses': {
        200: {
            'description': 'Credit status retrieved',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'stories_used_this_month': {'type': 'integer'},
                            'extra_credits': {'type': 'integer'},
                            'can_create_story': {'type': 'boolean'},
                            'stories_remaining': {'type': 'integer'},
                            'last_reset_date': {'type': 'string', 'format': 'date'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'}
    }
})
def get_credit_status():
    """Get current credit status for the authenticated user"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
            
        stories_remaining = max(0, 10 - user.stories_used_this_month)
        
        return jsonify({
            'stories_used_this_month': user.stories_used_this_month,
            'extra_credits': user.extra_credits,
            'can_create_story': user.can_create_story(),
            'can_buy_extra_credits': user.can_buy_extra_credits(),
            'needs_subscription': user.needs_subscription(),
            'has_active_subscription': user.has_active_subscription,
            'stories_remaining': stories_remaining,
            'last_reset_date': user.last_reset_date.isoformat() if user.last_reset_date else None
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# STRIPE IMPLEMENTATION COMMENTED OUT - Keep for future use
# Helper functions for Stripe webhook processing
# def handle_successful_payment(session):
#     """Handle successful payment from Stripe checkout session"""
#     try:
#         print(f"Processing payment session: {session}")
#         
#         # Extract user information from client_reference_id or email
#         user_id = session.get('client_reference_id')
#         print(f"Using client_reference_id as user_id: {user_id}")
#         
#         # If no user_id from client_reference_id, try to find user by customer email as fallback
#         if not user_id:
#             customer_email = session.get('customer_details', {}).get('email')
#             if customer_email:
#                 user = User.query.filter_by(email=customer_email).first()
#                 if user:
#                     user_id = user.id
#                     print(f"Found user by email {customer_email}: {user_id}")
#         
#         print(f"User ID: {user_id}")
#         
#         if not user_id:
#             print(f"No user_id found in client_reference_id or customer email")
#             return
#         
#         user = User.query.get(user_id)
#         if not user:
#             print(f"User not found: {user_id}")
#             return
#         
#         # Determine payment type based on session mode or amount
#         if session.get('mode') == 'subscription':
#             payment_type = 'subscription'
#         else:
#             # Check amount to determine if it's extra credits ($6.90 = 690 cents)
#             amount_total = session.get('amount_total', 0)
#             if amount_total == 690:  # $6.90 for extra credits
#                 payment_type = 'extra_credits'
#                 quantity = 1
#             elif amount_total % 690 == 0:  # Multiple extra credits
#                 payment_type = 'extra_credits'
#                 quantity = amount_total // 690
#             else:
#                 payment_type = 'extra_credits'
#                 quantity = 1  # Default to 1 extra credit
#         
#         if payment_type == 'subscription':
#             # Activate monthly subscription
#             user.has_active_subscription = True
#             user.subscription_start_date = date.today()
#             
#             # Store Stripe customer and subscription IDs
#             customer_id = session.get('customer')
#             subscription_id = session.get('subscription')
#             if customer_id:
#                 user.stripe_customer_id = customer_id
#             if subscription_id:
#                 user.stripe_subscription_id = subscription_id
#             
#             print(f"Activated subscription for user {user_id} (customer: {customer_id}, subscription: {subscription_id})")
#             
#         elif payment_type == 'extra_credits' and quantity:
#             # Add extra story credits
#             quantity = int(quantity)
#             user.add_extra_credits(quantity)
#             print(f"Added {quantity} extra credits for user {user_id}")
#         
#         db.session.commit()
#         print(f"Database updated successfully for user {user_id}")
#         
#     except Exception as e:
#         print(f"Error handling successful payment: {str(e)}")
#         db.session.rollback()
# 
# def handle_subscription_payment(invoice):
#     """Handle recurring subscription payment"""
#     try:
#         # Extract user information from invoice metadata or subscription
#         user_id = invoice.get('metadata', {}).get('user_id')
#         subscription_id = invoice.get('subscription')
#         
#         # If no user_id in metadata, try to find by subscription_id
#         if not user_id and subscription_id:
#             user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
#             if user:
#                 user_id = user.id
#         
#         if not user_id:
#             print(f"No user_id found in invoice metadata: {invoice.get('metadata')}")
#             return
#         
#         user = User.query.get(user_id)
#         if not user:
#             print(f"User not found: {user_id}")
#             return
#         
#         # Ensure subscription is still active
#         user.has_active_subscription = True
#         if subscription_id:
#             user.stripe_subscription_id = subscription_id
#         db.session.commit()
#         print(f"Renewed subscription for user {user_id}")
#         
#     except Exception as e:
#         print(f"Error handling subscription payment: {str(e)}")
#         db.session.rollback()
# 
# def handle_subscription_cancellation(subscription):
#     """Handle subscription cancellation"""
#     try:
#         subscription_id = subscription.get('id')
#         customer_id = subscription.get('customer')
#         
#         print(f"Processing subscription cancellation: {subscription_id} for customer: {customer_id}")
#         
#         # Find user by subscription_id or customer_id
#         user = None
#         if subscription_id:
#             user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
#         if not user and customer_id:
#             user = User.query.filter_by(stripe_customer_id=customer_id).first()
#         
#         if not user:
#             print(f"User not found for subscription {subscription_id} or customer {customer_id}")
#             return
#         
#         # Deactivate subscription
#         user.has_active_subscription = False
#         # Keep subscription_id for reference, but mark as inactive
#         db.session.commit()
#         print(f"Cancelled subscription for user {user.id}")
#         
#     except Exception as e:
#         print(f"Error handling subscription cancellation: {str(e)}")
#         db.session.rollback()
# 
# def handle_subscription_update(subscription):
#     """Handle subscription status updates"""
#     try:
#         subscription_id = subscription.get('id')
#         status = subscription.get('status')
#         
#         print(f"Processing subscription update: {subscription_id} with status: {status}")
#         
#         # Find user by subscription_id
#         user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
#         if not user:
#             print(f"User not found for subscription {subscription_id}")
#             return
#         
#         # Update subscription status based on Stripe status
#         # active, trialing, past_due, canceled, unpaid, incomplete, incomplete_expired
#         if status in ['active', 'trialing']:
#             user.has_active_subscription = True
#         elif status in ['canceled', 'unpaid', 'incomplete', 'incomplete_expired', 'past_due']:
#             user.has_active_subscription = False
#         
#         db.session.commit()
#         print(f"Updated subscription status for user {user.id} to {status}")
#         
#     except Exception as e:
#         print(f"Error handling subscription update: {str(e)}")
#         db.session.rollback()

# STRIPE IMPLEMENTATION COMMENTED OUT - Keep for future use
# @bp.route('/stripe/customer-portal', methods=['POST'])
# @login_required
# @swag_from({
#     'tags': ['Stripe'],
#     'summary': 'Get Stripe Customer Portal URL',
#     'description': 'Returns a URL to Stripe Customer Portal where users can manage their subscription, including cancellation',
#     'responses': {
#         200: {
#             'description': 'Customer Portal URL generated',
#             'content': {
#                 'application/json': {
#                     'schema': {
#                         'type': 'object',
#                         'properties': {
#                             'url': {'type': 'string', 'description': 'URL to Stripe Customer Portal'}
#                         }
#                     }
#                 }
#             }
#         },
#         400: {'description': 'User has no Stripe customer ID'},
#         401: {'description': 'Not authenticated'},
#         500: {'description': 'Internal server error'}
#     }
# })
# def get_customer_portal():
#     """Get Stripe Customer Portal URL for subscription management"""
#     try:
#         user_id = get_current_user_id()
#         user = User.query.get(user_id)
#         
#         if not user:
#             return jsonify({"error": "User not found"}), 404
#         
#         if not user.stripe_customer_id:
#             return jsonify({"error": "No Stripe customer ID found. Please subscribe first."}), 400
#         
#         # Get Stripe secret key from config
#         secret_key = current_app.config.get('STRIPE_SECRET_KEY')
#         if not secret_key:
#             return jsonify({"error": "Stripe secret key not configured"}), 500
#         
#         # Initialize Stripe with secret key
#         stripe.api_key = secret_key
#         
#         # Create Customer Portal session
#         portal_session = stripe.billing_portal.Session.create(
#             customer=user.stripe_customer_id,
#             return_url=request.headers.get('Referer') or request.url_root
#         )
#         
#         return jsonify({"url": portal_session.url})
#         
#     except stripe.error.StripeError as e:
#         print(f"Stripe error: {str(e)}")
#         return jsonify({"error": f"Stripe error: {str(e)}"}), 500
#     except Exception as e:
#         print(f"Error creating customer portal session: {str(e)}")
#         return jsonify({"error": str(e)}), 500

# STRIPE IMPLEMENTATION COMMENTED OUT - Keep for future use
# @bp.route('/stripe/cancel-subscription', methods=['POST'])
# @login_required
# @swag_from({
#     'tags': ['Stripe'],
#     'summary': 'Cancel user subscription',
#     'description': 'Cancel the user\'s active subscription immediately or at period end',
#     'requestBody': {
#         'required': False,
#         'content': {
#             'application/json': {
#                 'schema': {
#                     'type': 'object',
#                     'properties': {
#                         'cancel_at_period_end': {
#                             'type': 'boolean',
#                             'description': 'If true, cancel at period end. If false, cancel immediately.',
#                             'default': True
#                         }
#                     }
#                 }
#             }
#         }
#     },
#     'responses': {
#         200: {
#             'description': 'Subscription cancelled successfully',
#             'content': {
#                 'application/json': {
#                     'schema': {
#                         'type': 'object',
#                         'properties': {
#                             'status': {'type': 'string'},
#                             'message': {'type': 'string'},
#                             'cancel_at_period_end': {'type': 'boolean'}
#                         }
#                     }
#                 }
#             }
#         },
#         400: {'description': 'No active subscription found'},
#         401: {'description': 'Not authenticated'},
#         500: {'description': 'Internal server error'}
#     }
# })
# def cancel_subscription():
#     """Cancel user subscription programmatically"""
#     try:
#         user_id = get_current_user_id()
#         user = User.query.get(user_id)
#         
#         if not user:
#             return jsonify({"error": "User not found"}), 404
#         
#         if not user.stripe_subscription_id:
#             return jsonify({"error": "No active subscription found"}), 400
#         
#         # Get Stripe secret key from config
#         secret_key = current_app.config.get('STRIPE_SECRET_KEY')
#         if not secret_key:
#             return jsonify({"error": "Stripe secret key not configured"}), 500
#         
#         # Initialize Stripe with secret key
#         stripe.api_key = secret_key
#         
#         # Get cancellation preference from request
#         data = request.get_json() or {}
#         cancel_at_period_end = data.get('cancel_at_period_end', True)
#         
#         # Cancel subscription
#         if cancel_at_period_end:
#             # Cancel at period end (user keeps access until billing period ends)
#             subscription = stripe.Subscription.modify(
#                 user.stripe_subscription_id,
#                 cancel_at_period_end=True
#             )
#             message = "Subscription will be cancelled at the end of the current billing period"
#         else:
#             # Cancel immediately
#             subscription = stripe.Subscription.delete(user.stripe_subscription_id)
#             user.has_active_subscription = False
#             db.session.commit()
#             message = "Subscription cancelled immediately"
#         
#         return jsonify({
#             "status": "success",
#             "message": message,
#             "cancel_at_period_end": cancel_at_period_end
#         })
#         
#     except stripe.error.StripeError as e:
#         print(f"Stripe error: {str(e)}")
#         return jsonify({"error": f"Stripe error: {str(e)}"}), 500
#     except Exception as e:
#         print(f"Error cancelling subscription: {str(e)}")
#         db.session.rollback()
#         return jsonify({"error": str(e)}), 500

@bp.route('/test/activate-subscription', methods=['POST'])
@swag_from({
    'tags': ['Testing'],
    'summary': 'Manually activate subscription for testing',
    'description': 'Manually activate subscription for a user (for testing purposes)',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['user_id'],
                    'properties': {
                        'user_id': {
                            'type': 'integer',
                            'description': 'User ID to activate subscription for'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {'description': 'Subscription activated successfully'},
        400: {'description': 'Missing user_id'},
        404: {'description': 'User not found'},
        500: {'description': 'Internal server error'}
    }
})
def test_activate_subscription():
    """Manually activate subscription for testing - ONLY for development/testing"""
    try:
        # Only allow in development mode
        if current_app.config.get('ENV') == 'production':
            return jsonify({"error": "Manual activation not allowed in production"}), 403
        
        data = request.get_json()
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Check if user already has active subscription
        if user.has_active_subscription:
            return jsonify({
                "ok": True,
                "message": f"User {user_id} already has an active subscription",
                "user_id": user_id,
                "has_active_subscription": user.has_active_subscription
            })
        
        # Activate subscription
        user.has_active_subscription = True
        user.subscription_start_date = date.today()
        
        db.session.commit()
        
        return jsonify({
            "ok": True,
            "message": f"Subscription activated for user {user_id}",
            "user_id": user_id,
            "has_active_subscription": user.has_active_subscription
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route('/test/add-extra-credits', methods=['POST'])
@swag_from({
    'tags': ['Testing'],
    'summary': 'Manually add extra credits for testing',
    'description': 'Manually add extra story credits for a user (for testing purposes)',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['user_id', 'quantity'],
                    'properties': {
                        'user_id': {
                            'type': 'integer',
                            'description': 'User ID to add credits for'
                        },
                        'quantity': {
                            'type': 'integer',
                            'description': 'Number of extra credits to add'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {'description': 'Extra credits added successfully'},
        400: {'description': 'Missing required data'},
        404: {'description': 'User not found'},
        500: {'description': 'Internal server error'}
    }
})
def test_add_extra_credits():
    """Manually add extra credits for testing"""
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        quantity = data.get('quantity')
        
        if not user_id or not quantity:
            return jsonify({"error": "user_id and quantity are required"}), 400
        
        user = User.query.get(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Add extra credits
        user.add_extra_credits(int(quantity))
        
        db.session.commit()
        
        return jsonify({
            "ok": True,
            "message": f"Added {quantity} extra credits for user {user_id}",
            "user_id": user_id,
            "extra_credits": user.extra_credits
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

