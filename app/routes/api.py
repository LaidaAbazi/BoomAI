from flask import Blueprint, request, jsonify, current_app
from app.models import db, Feedback, CaseStudy, User, StripeWebhookEvent, Company, CompanyInvite
from app.utils.auth_helpers import get_current_user_id, login_required, subscription_required, owner_required
from app.utils.language_utils import detect_and_normalize_language
from app.services.feedback_service import FeedbackService
import uuid
from datetime import datetime, date, timedelta, timezone
import secrets
from flasgger import swag_from
import os
import stripe
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
        
        # Detect and store language if not already set
        if not case_study.language:
            case_study.language = detect_and_normalize_language(final_summary)
        
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Final summary saved successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route('/stripe/webhook', methods=['POST'])
@swag_from({
    'tags': ['Stripe'],
    'summary': 'Handle Stripe webhook events',
    'description': 'Process Stripe webhook events for payment completion and subscription activation',
    'responses': {
        200: {'description': 'Webhook processed successfully'},
        400: {'description': 'Invalid payload or signature'},
        500: {'description': 'Internal server error'}
    }
})
def stripe_webhook():
    """Handle Stripe webhook events"""
    try:
        print("Webhook received!")
        
        # Check if Stripe is configured
        webhook_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
        secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        
        print(f"DEBUG: STRIPE_WEBHOOK_SECRET = {webhook_secret[:10] if webhook_secret else 'None'}...")
        print(f"DEBUG: STRIPE_SECRET_KEY = {secret_key[:10] if secret_key else 'None'}...")
        
        if not webhook_secret:
            print("ERROR: STRIPE_WEBHOOK_SECRET not configured")
            return jsonify({"error": "Stripe webhook secret not configured"}), 500
        
        if not secret_key:
            print("ERROR: STRIPE_SECRET_KEY not configured")
            return jsonify({"error": "Stripe secret key not configured"}), 500
        
        payload = request.get_data()
        sig_header = request.headers.get('Stripe-Signature')
        
        print(f"Payload length: {len(payload)}")
        print(f"Signature header: {sig_header}")
        
        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload, sig_header, current_app.config['STRIPE_WEBHOOK_SECRET']
        )
        
        event_id = event.get('id')
        event_type = event.get('type')
        
        # Log ALL incoming events for debugging (especially important for Test Clock simulations)
        # NOTE: When using Stripe Test Clock, events may arrive with delays or out of order.
        # The invoice.payment_succeeded event typically arrives after invoice.created.
        # If you don't see invoice.payment_succeeded immediately, wait 30-60 seconds and check again.
        print(f"=== WEBHOOK EVENT RECEIVED ===")
        print(f"Event type: {event_type}, Event ID: {event_id}")
        print(f"Event timestamp: {event.get('created', 'unknown')}")
        
        # Log invoice/subscription details if present for subscription-related events
        if event_type in ['invoice.payment_succeeded', 'invoice_payment.paid', 'invoice.created', 'invoice.paid']:
            invoice_obj = event.get('data', {}).get('object', {})
            invoice_id = invoice_obj.get('id', 'unknown')
            subscription_id = invoice_obj.get('subscription')
            billing_reason = invoice_obj.get('billing_reason')
            print(f"  Invoice ID: {invoice_id}")
            print(f"  Subscription ID: {subscription_id}")
            print(f"  Billing Reason: {billing_reason}")
            print(f"  Invoice Status: {invoice_obj.get('status', 'unknown')}")
        
        if event_type in ['customer.subscription.updated', 'customer.subscription.created']:
            sub_obj = event.get('data', {}).get('object', {})
            sub_id = sub_obj.get('id', 'unknown')
            sub_status = sub_obj.get('status', 'unknown')
            print(f"  Subscription ID: {sub_id}")
            print(f"  Subscription Status: {sub_status}")
        
        print(f"==============================")
        
        # Check for idempotency - prevent duplicate processing
        existing_event = StripeWebhookEvent.query.filter_by(event_id=event_id).first()
        if existing_event and existing_event.processed:
            print(f"Event {event_id} already processed, skipping")
            return jsonify({"status": "success", "message": "Event already processed"})
        
        # Record event (even if not processed yet, to prevent race conditions)
        if not existing_event:
            webhook_event = StripeWebhookEvent(
                event_id=event_id,
                event_type=event_type,
                processed=False
            )
            db.session.add(webhook_event)
            db.session.commit()
        else:
            webhook_event = existing_event
        
        # Handle the event
        try:
            if event_type == 'checkout.session.completed':
                session = event['data']['object']
                print(f"Handling checkout.session.completed for session: {session.get('id')}")
                handle_successful_payment(session)
            elif event_type == 'invoice.payment_succeeded':
                invoice = event['data']['object']
                print(f"Handling invoice.payment_succeeded for invoice: {invoice.get('id')}")
                handle_subscription_payment(invoice)
            elif event_type == 'invoice_payment.paid':
                # Handle invoice_payment.paid event (alternative event name for successful invoice payments)
                invoice = event['data']['object']
                print(f"Handling invoice_payment.paid for invoice: {invoice.get('id')}")
                handle_subscription_payment(invoice)
            elif event_type == 'invoice.created':
                # Acknowledge invoice creation (no action needed)
                invoice = event['data']['object']
                print(f"INFO: Acknowledged invoice.created - Invoice {invoice.get('id')}")
            elif event_type == 'invoice.paid':
                # Acknowledge invoice payment (no action needed, handled by invoice.payment_succeeded)
                invoice = event['data']['object']
                print(f"INFO: Acknowledged invoice.paid - Invoice {invoice.get('id')}")
            elif event_type == 'customer.subscription.deleted':
                subscription = event['data']['object']
                print(f"Handling customer.subscription.deleted for subscription: {subscription.get('id')}")
                handle_subscription_cancellation(subscription)
            elif event_type == 'customer.subscription.created':
                # Acknowledge subscription creation (no action needed, handled by checkout.session.completed)
                subscription = event['data']['object']
                print(f"INFO: Acknowledged customer.subscription.created - Subscription {subscription.get('id')}")
            elif event_type == 'customer.subscription.updated':
                subscription = event['data']['object']
                print(f"Handling customer.subscription.updated for subscription: {subscription.get('id')}")
                handle_subscription_update(subscription)
            else:
                print(f"Unhandled event type: {event_type}")
            
            # Mark event as processed
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            db.session.commit()
            
            print("Webhook processed successfully")
            return jsonify({"status": "success"})
            
        except Exception as e:
            print(f"Error processing event: {str(e)}")
            # Don't mark as processed if there was an error
            db.session.rollback()
            raise
        
    except ValueError as e:
        print(f"ValueError: {str(e)}")
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        print(f"SignatureVerificationError: {str(e)}")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
        
        # Get billing date from subscription info if available
        next_billing_date = None
        if user.stripe_subscription_id:
            try:
                secret_key = current_app.config.get('STRIPE_SECRET_KEY')
                if secret_key:
                    stripe.api_key = secret_key
                    subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
                    
                    # Get billing date (next_billing_date or current_period_end)
                    cancel_at_period_end = getattr(subscription, 'cancel_at_period_end', False)
                    cancel_at = getattr(subscription, 'cancel_at', None)
                    
                    if cancel_at_period_end and cancel_at:
                        # Subscription is cancelling - no next billing
                        next_billing_date = None
                    else:
                        # Try to get from subscription items (most reliable)
                        try:
                            subscription_items = stripe.SubscriptionItem.list(
                                subscription=user.stripe_subscription_id, 
                                limit=1
                            )
                            if subscription_items.data and len(subscription_items.data) > 0:
                                period_end = getattr(subscription_items.data[0], 'current_period_end', None)
                                if period_end:
                                    next_billing_date = period_end * 1000  # Convert to milliseconds
                        except Exception:
                            # Fallback to subscription current_period_end if available
                            period_end = getattr(subscription, 'current_period_end', None)
                            if period_end:
                                next_billing_date = period_end * 1000
            except Exception as e:
                print(f"Error fetching billing date for credit status: {str(e)}")
                # Continue without billing date
        
        return jsonify({
            'stories_used_this_month': user.stories_used_this_month,
            'extra_credits': user.extra_credits,
            'can_create_story': user.can_create_story(),
            'can_buy_extra_credits': user.can_buy_extra_credits(),
            'needs_subscription': user.needs_subscription(),
            'has_active_subscription': user.has_active_subscription,
            'stories_remaining': stories_remaining,
            'last_reset_date': user.last_reset_date.isoformat() if user.last_reset_date else None,
            'next_billing_date': next_billing_date
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Helper functions for Stripe webhook processing
def handle_successful_payment(session):
    """Handle successful payment from Stripe checkout session"""
    try:
        print(f"Processing payment session: {session}")
        
        # Extract user information from client_reference_id or email
        user_id = session.get('client_reference_id')
        print(f"Using client_reference_id as user_id: {user_id}")
        
        # Convert user_id to int if it's a string
        if user_id and isinstance(user_id, str):
            try:
                user_id = int(user_id)
            except ValueError:
                print(f"Warning: client_reference_id '{user_id}' is not a valid integer")
                user_id = None
        
        # If no user_id from client_reference_id, try to find user by customer email as fallback
        if not user_id:
            customer_email = session.get('customer_details', {}).get('email')
            if customer_email:
                user = User.query.filter_by(email=customer_email).first()
                if user:
                    user_id = user.id
                    print(f"Found user by email {customer_email}: {user_id}")
        
        print(f"User ID: {user_id}")
        
        if not user_id:
            print(f"No user_id found in client_reference_id or customer email")
            return
        
        user = User.query.get(user_id)
        if not user:
            print(f"User not found: {user_id}")
            return
        
        # Determine payment type based on session mode or metadata
        if session.get('mode') == 'subscription':
            payment_type = 'subscription'
        else:
            # Check metadata first for quantity (more reliable)
            metadata = session.get('metadata', {})
            if metadata.get('payment_type') == 'extra_credits':
                payment_type = 'extra_credits'
                quantity = int(metadata.get('quantity', 1))
            else:
                # Fallback: Check amount to determine if it's extra credits ($6.90 = 690 cents)
                amount_total = session.get('amount_total', 0)
                if amount_total == 690:  # $6.90 for extra credits
                    payment_type = 'extra_credits'
                    quantity = 1
                elif amount_total % 690 == 0:  # Multiple extra credits
                    payment_type = 'extra_credits'
                    quantity = amount_total // 690
                else:
                    payment_type = 'extra_credits'
                    quantity = 1  # Default to 1 extra credit
        
        if payment_type == 'subscription':
            # Check if user already has an active subscription
            if user.has_active_subscription and user.stripe_subscription_id:
                # Cancel the old subscription before activating the new one
                try:
                    old_subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
                    if old_subscription.status in ['active', 'trialing']:
                        # Cancel the old subscription immediately
                        stripe.Subscription.delete(user.stripe_subscription_id)
                        print(f"Cancelled old subscription {user.stripe_subscription_id} for user {user_id}")
                except stripe.error.InvalidRequestError:
                    # Old subscription doesn't exist, continue
                    pass
                except stripe.error.StripeError as e:
                    print(f"Error cancelling old subscription: {str(e)}")
                    # Continue anyway
            
            # Also check if customer has any other active subscriptions in Stripe
            customer_id = session.get('customer') or user.stripe_customer_id
            if customer_id:
                try:
                    subscriptions = stripe.Subscription.list(
                        customer=customer_id,
                        status='active',
                        limit=10
                    )
                    # Cancel any other active subscriptions (except the new one)
                    new_subscription_id = session.get('subscription')
                    for sub in subscriptions.data:
                        if sub.id != new_subscription_id:
                            try:
                                stripe.Subscription.delete(sub.id)
                                print(f"Cancelled duplicate subscription {sub.id} for user {user_id}")
                            except stripe.error.StripeError as e:
                                print(f"Error cancelling duplicate subscription {sub.id}: {str(e)}")
                except stripe.error.StripeError as e:
                    print(f"Error checking for duplicate subscriptions: {str(e)}")
                    # Continue anyway
            
            # Activate new monthly subscription
            user.has_active_subscription = True
            user.subscription_start_date = date.today()
            
            # Store Stripe customer and subscription IDs
            if customer_id:
                user.stripe_customer_id = customer_id
                # Update customer info in Stripe to ensure name and email are current
                try:
                    customer_name = f"{user.first_name} {user.last_name}".strip()
                    stripe.Customer.modify(
                        customer_id,
                        email=user.email,
                        name=customer_name if customer_name else None,
                        metadata={
                            'user_id': str(user_id)
                        }
                    )
                except stripe.error.StripeError as e:
                    print(f"Warning: Could not update customer {customer_id}: {str(e)}")
                    # Continue anyway - customer exists
            subscription_id = session.get('subscription')
            if subscription_id:
                user.stripe_subscription_id = subscription_id
            
            # Reset monthly usage to grant initial 10 credits for new subscription
            # Check metadata to ensure this is a subscription payment
            metadata = session.get('metadata', {})
            if metadata.get('payment_type') == 'subscription' or session.get('mode') == 'subscription':
                user.reset_monthly_usage()
                print(f"Granted initial 10 credits to user {user_id} for new subscription")
            
            print(f"Activated subscription for user {user_id} (customer: {customer_id}, subscription: {subscription_id})")
            
        elif payment_type == 'extra_credits' and quantity:
            # Add extra story credits
            quantity = int(quantity)
            user.add_extra_credits(quantity)
            print(f"Added {quantity} extra credits for user {user_id}")
        
        db.session.commit()
        print(f"Database updated successfully for user {user_id}")
        
    except Exception as e:
        print(f"Error handling successful payment: {str(e)}")
        db.session.rollback()

def handle_subscription_payment(invoice):
    """Handle recurring subscription payment - Always retrieves fresh invoice from Stripe for reliability"""
    try:
        # Extract invoice ID from payload (handles both Invoice and InvoicePayment objects)
        invoice_obj_type = invoice.get('object')
        
        # Handle InvoicePayment objects (from invoice_payment.paid events)
        # InvoicePayment objects have an 'invoice' field with the invoice ID (string)
        if invoice_obj_type == 'invoice_payment' and invoice.get('invoice'):
            invoice_id = invoice.get('invoice')  # This is the actual invoice ID
            print(f"DEBUG: InvoicePayment object detected, invoice ID: {invoice_id}")
        else:
            # Regular Invoice object
            invoice_id = invoice.get('id', 'unknown')
            print(f"DEBUG: Invoice object detected, invoice ID: {invoice_id}")
        
        if not invoice_id or invoice_id == 'unknown':
            print(f"ERROR: Cannot determine invoice ID from payload. Ignoring event.")
            return
        
        # ALWAYS retrieve the full invoice from Stripe to guarantee we have all fields
        # This is critical for test simulations where payloads may be incomplete
        print(f"DEBUG: Retrieving full invoice {invoice_id} from Stripe...")
        try:
            secret_key = current_app.config.get('STRIPE_SECRET_KEY')
            if not secret_key:
                print(f"ERROR: Stripe secret key not configured, cannot retrieve invoice")
                return
            
            stripe.api_key = secret_key
            full_invoice = stripe.Invoice.retrieve(invoice_id)
            invoice = full_invoice  # Use the retrieved invoice for all subsequent operations
            invoice_id = invoice.get('id', 'unknown')
            
            print(f"DEBUG: Successfully retrieved invoice {invoice_id} from Stripe")
        except Exception as e:
            print(f"ERROR: Failed to retrieve invoice {invoice_id} from Stripe: {str(e)}")
            import traceback
            traceback.print_exc()
            return
        
        # Extract key fields from the full invoice
        subscription_id = invoice.get('subscription')  # May be None, but we don't require it
        customer_id = invoice.get('customer')
        billing_reason = invoice.get('billing_reason')
        
        print(f"DEBUG: Invoice {invoice_id} - subscription_id: {subscription_id}, customer_id: {customer_id}, billing_reason: {billing_reason}")
        
        # Require customer_id to find the user
        if not customer_id:
            print(f"INFO: Invoice {invoice_id} has no customer_id. Ignoring event.")
            return
        
        # Find user by customer_id (required for credit reset)
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if not user:
            print(f"ERROR: User not found for customer_id {customer_id}")
            return
        
        print(f"DEBUG: Found user {user.id} - stories_used_this_month: {user.stories_used_this_month}, last_reset_date: {user.last_reset_date}")
        
        # Update user's subscription info if we have it
        user.has_active_subscription = True
        if customer_id:
            user.stripe_customer_id = customer_id
        if subscription_id:
            user.stripe_subscription_id = subscription_id
        
        # Credit reset is triggered ONLY when both conditions are met:
        # 1. User is successfully found using customer_id (already verified above)
        # 2. billing_reason == 'subscription_cycle'
        if billing_reason == 'subscription_cycle':
            # This is a recurring renewal - reset monthly credits
            print(f"SUCCESS: Detected subscription_cycle - resetting credits for user {user.id}")
            user.reset_monthly_usage()
            db.session.commit()
            print(f"SUCCESS: Renewed subscription for user {user.id} (billing cycle) - reset monthly credits")
            print(f"DEBUG: After reset - stories_used_this_month: {user.stories_used_this_month}, last_reset_date: {user.last_reset_date}")
        elif billing_reason == 'subscription_create':
            # This is the initial subscription payment - don't reset credits
            # Credits are granted in checkout.session.completed handler
            db.session.commit()
            print(f"INFO: Initial subscription payment for user {user.id} - credits already granted, will reset on renewal")
        else:
            # Other billing reasons (subscription_update, etc.) - don't reset
            db.session.commit()
            print(f"INFO: Subscription payment processed for user {user.id} (billing_reason: {billing_reason}) - no credit reset")
        
    except Exception as e:
        print(f"ERROR: Error handling subscription payment: {str(e)}")
        import traceback
        traceback.print_exc()
        db.session.rollback()

def handle_subscription_cancellation(subscription):
    """Handle subscription cancellation"""
    try:
        subscription_id = subscription.get('id')
        customer_id = subscription.get('customer')
        
        print(f"Processing subscription cancellation: {subscription_id} for customer: {customer_id}")
        
        # Find user by subscription_id or customer_id
        user = None
        if subscription_id:
            user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
        if not user and customer_id:
            user = User.query.filter_by(stripe_customer_id=customer_id).first()
        
        if not user:
            print(f"User not found for subscription {subscription_id} or customer {customer_id}")
            return
        
        # Deactivate subscription
        user.has_active_subscription = False
        # Keep subscription_id for reference, but mark as inactive
        db.session.commit()
        print(f"Cancelled subscription for user {user.id}")
        
    except Exception as e:
        print(f"Error handling subscription cancellation: {str(e)}")
        db.session.rollback()

def handle_subscription_update(subscription):
    """Handle subscription status updates"""
    try:
        subscription_id = subscription.get('id')
        status = subscription.get('status')
        
        print(f"Processing subscription update: {subscription_id} with status: {status}")
        
        # Find user by subscription_id
        user = User.query.filter_by(stripe_subscription_id=subscription_id).first()
        if not user:
            print(f"User not found for subscription {subscription_id}")
            return
        
        # Update subscription status based on Stripe status
        # active, trialing, past_due, canceled, unpaid, incomplete, incomplete_expired
        if status in ['active', 'trialing']:
            user.has_active_subscription = True
        elif status in ['canceled', 'unpaid', 'incomplete', 'incomplete_expired', 'past_due']:
            user.has_active_subscription = False
        
        db.session.commit()
        print(f"Updated subscription status for user {user.id} to {status}")
        
    except Exception as e:
        print(f"Error handling subscription update: {str(e)}")
        db.session.rollback()

@bp.route('/stripe/customer-portal', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Stripe'],
    'summary': 'Get Stripe Customer Portal URL',
    'description': 'Returns a URL to Stripe Customer Portal where users can manage their subscription, including cancellation',
    'responses': {
        200: {
            'description': 'Customer Portal URL generated',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'url': {'type': 'string', 'description': 'URL to Stripe Customer Portal'}
                        }
                    }
                }
            }
        },
        400: {'description': 'User has no Stripe customer ID'},
        401: {'description': 'Not authenticated'},
        500: {'description': 'Internal server error'}
    }
})
def get_customer_portal():
    """Get Stripe Customer Portal URL for subscription management"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if not user.stripe_customer_id:
            return jsonify({"error": "No Stripe customer ID found. Please subscribe first."}), 400
        
        # Get Stripe secret key from config
        secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not secret_key:
            return jsonify({"error": "Stripe secret key not configured"}), 500
        
        # Initialize Stripe with secret key
        stripe.api_key = secret_key
        
        # Create Customer Portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=request.headers.get('Referer') or request.url_root
        )
        
        return jsonify({"url": portal_session.url})
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({"error": f"Stripe error: {str(e)}"}), 500
    except Exception as e:
        print(f"Error creating customer portal session: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/stripe/cancel-subscription', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Stripe'],
    'summary': 'Cancel user subscription',
    'description': 'Cancel the user\'s active subscription immediately or at period end',
    'requestBody': {
        'required': False,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'properties': {
                        'cancel_at_period_end': {
                            'type': 'boolean',
                            'description': 'If true, cancel at period end. If false, cancel immediately.',
                            'default': True
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Subscription cancelled successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'status': {'type': 'string'},
                            'message': {'type': 'string'},
                            'cancel_at_period_end': {'type': 'boolean'}
                        }
                    }
                }
            }
        },
        400: {'description': 'No active subscription found'},
        401: {'description': 'Not authenticated'},
        500: {'description': 'Internal server error'}
    }
})
def cancel_subscription():
    """Cancel user subscription programmatically"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if not user.stripe_subscription_id:
            return jsonify({"error": "No active subscription found"}), 400
        
        # Get Stripe secret key from config
        secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not secret_key:
            return jsonify({"error": "Stripe secret key not configured"}), 500
        
        # Initialize Stripe with secret key
        stripe.api_key = secret_key
        
        # Get cancellation preference from request
        data = request.get_json() or {}
        cancel_at_period_end = data.get('cancel_at_period_end', True)
        
        # Cancel subscription
        if cancel_at_period_end:
            # Cancel at period end (user keeps access until billing period ends)
            subscription = stripe.Subscription.modify(
                user.stripe_subscription_id,
                cancel_at_period_end=True
            )
            message = "Subscription will be cancelled at the end of the current billing period"
        else:
            # Cancel immediately
            subscription = stripe.Subscription.delete(user.stripe_subscription_id)
            user.has_active_subscription = False
            db.session.commit()
            message = "Subscription cancelled immediately"
        
        return jsonify({
            "status": "success",
            "message": message,
            "cancel_at_period_end": cancel_at_period_end
        })
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({"error": f"Stripe error: {str(e)}"}), 500
    except Exception as e:
        print(f"Error cancelling subscription: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route('/stripe/create-checkout-session', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Stripe'],
    'summary': 'Create Stripe checkout session',
    'description': 'Create a Stripe checkout session for subscription or extra credits. For extra_credits, users can specify quantity (1-100).',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['type'],
                    'properties': {
                        'type': {
                            'type': 'string',
                            'enum': ['subscription', 'extra_credits'],
                            'description': 'Type of checkout session'
                        },
                        'quantity': {
                            'type': 'integer',
                            'minimum': 1,
                            'maximum': 100,
                            'description': 'Number of extra credits to purchase (for extra_credits type only). Must be between 1 and 100.',
                            'default': 1,
                            'example': 5
                        }
                    }
                }
            }
        }
    },
    'responses': {
        200: {
            'description': 'Checkout session created successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'url': {
                                'type': 'string',
                                'description': 'Stripe Checkout session URL to redirect user to',
                                'example': 'https://checkout.stripe.com/pay/cs_test_...'
                            }
                        }
                    }
                }
            }
        },
        400: {
            'description': 'Invalid request - validation errors',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'error': {
                                'type': 'string',
                                'description': 'Error message',
                                'examples': {
                                    'invalid_payment_type': 'Invalid payment type',
                                    'invalid_quantity': 'Invalid quantity',
                                    'quantity_too_low': 'Quantity must be at least 1',
                                    'quantity_too_high': 'Quantity cannot exceed 100',
                                    'active_subscription': 'You already have an active subscription. Please cancel your current subscription before creating a new one.'
                                }
                            },
                            'has_active_subscription': {
                                'type': 'boolean',
                                'description': 'Whether user has an active subscription (only for subscription type)'
                            },
                            'subscription_id': {
                                'type': 'string',
                                'description': 'Existing subscription ID (only for subscription type)'
                            },
                            'existing_subscriptions': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'List of existing active subscription IDs'
                            }
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated - login required'},
        404: {'description': 'User not found'},
        500: {
            'description': 'Internal server error',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'error': {
                                'type': 'string',
                                'description': 'Error message',
                                'examples': {
                                    'stripe_error': 'Stripe error: ...',
                                    'config_error': 'Stripe secret key not configured',
                                    'price_id_error': 'Stripe subscription/extra credits price ID not configured'
                                }
                            }
                        }
                    }
                }
            }
        }
    }
})
def create_checkout_session():
    """Create a Stripe checkout session"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        payment_type = data.get('type')
        quantity = data.get('quantity', 1)
        
        if payment_type not in ['subscription', 'extra_credits']:
            return jsonify({"error": "Invalid payment type"}), 400
        
        # Validate quantity for extra credits
        if payment_type == 'extra_credits':
            try:
                quantity = int(quantity)
                if quantity < 1:
                    return jsonify({"error": "Quantity must be at least 1"}), 400
                if quantity > 100:
                    return jsonify({"error": "Quantity cannot exceed 100"}), 400
            except (ValueError, TypeError):
                return jsonify({"error": "Invalid quantity"}), 400
        
        # Get Stripe secret key from config
        secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not secret_key:
            return jsonify({"error": "Stripe secret key not configured"}), 500
        
        # Initialize Stripe with secret key
        stripe.api_key = secret_key
        
        # Get base URL for success/cancel URLs
        base_url = current_app.config.get('BASE_URL', request.url_root.rstrip('/'))
        
        if payment_type == 'subscription':
            # Check if user already has an active subscription
            if user.has_active_subscription and user.stripe_subscription_id:
                # Verify with Stripe that subscription is actually active
                try:
                    existing_subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
                    if existing_subscription.status in ['active', 'trialing']:
                        return jsonify({
                            "error": "You already have an active subscription. Please cancel your current subscription before creating a new one.",
                            "has_active_subscription": True,
                            "subscription_id": user.stripe_subscription_id
                        }), 400
                except stripe.error.InvalidRequestError:
                    # Subscription doesn't exist in Stripe, allow creation
                    pass
                except stripe.error.StripeError as e:
                    print(f"Error checking subscription: {str(e)}")
                    # Continue with creation if check fails
            
            # Get or create Stripe customer
            customer_id = user.stripe_customer_id
            customer_name = f"{user.first_name} {user.last_name}".strip()
            
            if not customer_id:
                # Create a new Stripe customer if one doesn't exist
                customer = stripe.Customer.create(
                    email=user.email,
                    name=customer_name if customer_name else None,
                    metadata={
                        'user_id': str(user_id)
                    }
                )
                customer_id = customer.id
                # Save customer ID to user
                user.stripe_customer_id = customer_id
                db.session.commit()
            else:
                # Update existing customer to ensure name and email are current
                try:
                    stripe.Customer.modify(
                        customer_id,
                        email=user.email,
                        name=customer_name if customer_name else None,
                        metadata={
                            'user_id': str(user_id)
                        }
                    )
                except stripe.error.StripeError as e:
                    print(f"Warning: Could not update customer {customer_id}: {str(e)}")
                    # Continue anyway - customer exists
            
            # Also check if customer has any other active subscriptions in Stripe
            if customer_id:
                try:
                    subscriptions = stripe.Subscription.list(
                        customer=customer_id,
                        status='active',
                        limit=10
                    )
                    if subscriptions.data:
                        # User has active subscription(s) in Stripe
                        active_sub_ids = [sub.id for sub in subscriptions.data]
                        return jsonify({
                            "error": "You already have an active subscription. Please cancel your current subscription before creating a new one.",
                            "has_active_subscription": True,
                            "existing_subscriptions": active_sub_ids
                        }), 400
                except stripe.error.StripeError as e:
                    print(f"Error checking existing subscriptions: {str(e)}")
                    # Continue with creation if check fails
            
            # Create subscription checkout session
            price_id = current_app.config.get('STRIPE_SUBSCRIPTION_PRICE_ID')
            if not price_id:
                return jsonify({"error": "Stripe subscription price ID not configured"}), 500
            
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,  # Use existing customer
                client_reference_id=str(user_id),
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f'{base_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{base_url}/dashboard?canceled=true',
                metadata={
                    'user_id': str(user_id),
                    'payment_type': 'subscription'
                }
            )
        else:
            # Create extra credits checkout session
            price_id = current_app.config.get('STRIPE_EXTRA_CREDITS_PRICE_ID')
            if not price_id:
                return jsonify({"error": "Stripe extra credits price ID not configured"}), 500
            
            # Get or create Stripe customer for invoice creation
            customer_id = user.stripe_customer_id
            customer_name = f"{user.first_name} {user.last_name}".strip()
            
            if not customer_id:
                # Create a new Stripe customer if one doesn't exist
                customer = stripe.Customer.create(
                    email=user.email,
                    name=customer_name if customer_name else None,
                    metadata={
                        'user_id': str(user_id)
                    }
                )
                customer_id = customer.id
                # Save customer ID to user
                user.stripe_customer_id = customer_id
                db.session.commit()
            else:
                # Update existing customer to ensure name and email are current
                try:
                    stripe.Customer.modify(
                        customer_id,
                        email=user.email,
                        name=customer_name if customer_name else None,
                        metadata={
                            'user_id': str(user_id)
                        }
                    )
                except stripe.error.StripeError as e:
                    print(f"Warning: Could not update customer {customer_id}: {str(e)}")
                    # Continue anyway - customer exists
            
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,  # Use existing customer for invoice creation
                client_reference_id=str(user_id),
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': quantity,
                }],
                mode='payment',
                invoice_creation={
                    'enabled': True  # Enable invoice creation for extra credits
                },
                success_url=f'{base_url}/dashboard?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{base_url}/dashboard?canceled=true',
                metadata={
                    'user_id': str(user_id),
                    'payment_type': 'extra_credits',
                    'quantity': str(quantity)
                }
            )
        
        return jsonify({"url": checkout_session.url})
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({"error": f"Stripe error: {str(e)}"}), 500
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")
        return jsonify({"error": str(e)}), 500

@bp.route('/stripe/subscription-info', methods=['GET'])
@login_required
@swag_from({
    'tags': ['Stripe'],
    'summary': 'Get subscription information',
    'description': 'Get current subscription information for the authenticated user, including details from Stripe',
    'responses': {
        200: {
            'description': 'Subscription information retrieved',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'has_active_subscription': {'type': 'boolean'},
                            'stripe_customer_id': {'type': 'string'},
                            'stripe_subscription_id': {'type': 'string'},
                            'subscription_start_date': {'type': 'string', 'format': 'date'},
                            'subscription_status': {'type': 'string'},
                            'cancel_at_period_end': {'type': 'boolean'},
                            'canceled_at': {'type': 'integer', 'description': 'Unix timestamp'},
                            'current_period_start': {'type': 'integer', 'description': 'Unix timestamp'},
                            'current_period_end': {'type': 'integer', 'description': 'Unix timestamp - end of current period (could be cancellation date)'},
                            'next_billing_date': {'type': 'integer', 'description': 'Unix timestamp - next billing date (only if renewing, None if cancelled)'}
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'}
    }
})
def get_subscription_info():
    """Get subscription information for the current user, including details from Stripe"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Base response with database fields
        response_data = {
            'has_active_subscription': user.has_active_subscription,
            'stripe_customer_id': user.stripe_customer_id,
            'stripe_subscription_id': user.stripe_subscription_id,
            'subscription_start_date': user.subscription_start_date.isoformat() if user.subscription_start_date else None,
            'subscription_status': None,
            'cancel_at_period_end': False,
            'canceled_at': None,
            'current_period_start': None,
            'current_period_end': None,
            'next_billing_date': None  # Only set if subscription is renewing (not cancelled)
        }
        
        # If user has a Stripe subscription ID, fetch details from Stripe
        if user.stripe_subscription_id:
            try:
                # Get Stripe secret key from config
                secret_key = current_app.config.get('STRIPE_SECRET_KEY')
                if not secret_key:
                    # If Stripe is not configured, return basic info
                    return jsonify(response_data)
                
                # Initialize Stripe with secret key
                stripe.api_key = secret_key
                
                # Retrieve subscription from Stripe
                subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
                
                # Extract subscription details from subscription object
                # Stripe Python SDK returns objects that can be accessed both ways
                try:
                    # Direct attribute access (preferred)
                    status = subscription.status
                    cancel_at_period_end = subscription.cancel_at_period_end
                    canceled_at = subscription.canceled_at  # When user requested cancellation
                    cancel_at = getattr(subscription, 'cancel_at', None)  # When subscription will actually end
                    created_ts = getattr(subscription, 'created', None)  # Subscription creation timestamp (fallback for period start)
                except AttributeError:
                    # Dictionary access (fallback)
                    if hasattr(subscription, '__getitem__'):
                        status = subscription['status'] if 'status' in subscription else None
                        cancel_at_period_end = subscription.get('cancel_at_period_end', False) if hasattr(subscription, 'get') else False
                        canceled_at = subscription.get('canceled_at') if hasattr(subscription, 'get') else None
                        cancel_at = subscription.get('cancel_at') if hasattr(subscription, 'get') else None
                        created_ts = subscription.get('created') if hasattr(subscription, 'get') else None
                    else:
                        # Last resort: use getattr with None check
                        status = getattr(subscription, 'status', None)
                        cancel_at_period_end = getattr(subscription, 'cancel_at_period_end', False)
                        canceled_at = getattr(subscription, 'canceled_at', None)
                        cancel_at = getattr(subscription, 'cancel_at', None)
                        created_ts = getattr(subscription, 'created', None)
                
                # Extract subscription details
                # Stripe returns timestamps in Unix seconds, convert to milliseconds for JavaScript
                response_data['subscription_status'] = status
                response_data['cancel_at_period_end'] = bool(cancel_at_period_end) if cancel_at_period_end is not None else False
                
                # Handle timestamps - convert from Unix seconds to milliseconds
                # Check for None explicitly since 0 is a valid timestamp
                if canceled_at is not None:
                    response_data['canceled_at'] = int(canceled_at) * 1000
                else:
                    response_data['canceled_at'] = None
                
                # Get current period timestamps from SubscriptionItem (primary method)
                # This is the recommended approach for future-proofing against Stripe API changes
                period_start_from_stripe = None
                period_end_from_stripe = None
                
                try:
                    subscription_items = stripe.SubscriptionItem.list(subscription=user.stripe_subscription_id, limit=1)
                    if subscription_items.data and len(subscription_items.data) > 0:
                        first_item = subscription_items.data[0]
                        period_start_from_stripe = getattr(first_item, 'current_period_start', None)
                        period_end_from_stripe = getattr(first_item, 'current_period_end', None)
                except Exception as e:
                    print(f"Could not retrieve subscription items: {e}")
                
                # Use period start from SubscriptionItem, or fallback to created timestamp (still from Stripe)
                if period_start_from_stripe is not None:
                    response_data['current_period_start'] = int(period_start_from_stripe) * 1000
                elif created_ts is not None:
                    # FALLBACK: Use subscription 'created' date (still from Stripe, not calculated)
                    response_data['current_period_start'] = int(created_ts) * 1000
                else:
                    response_data['current_period_start'] = None
                
                # Determine effective period end and next billing date
                # current_period_end = end of current billing period (could be cancellation date)
                # next_billing_date = next billing date (only if renewing, None if cancelled)
                
                effective_period_end_ts = None
                next_billing_date_ts = None
                
                if cancel_at_period_end and cancel_at is not None:
                    # Case 1: Subscription is scheduled to cancel at period end
                    # Use cancel_at from Stripe as the effective end date
                    effective_period_end_ts = cancel_at
                    # No next billing date since subscription is cancelling
                    next_billing_date_ts = None
                elif period_end_from_stripe is not None:
                    # Case 2: Standard renewing subscription - use current_period_end from SubscriptionItem
                    effective_period_end_ts = period_end_from_stripe
                    # Next billing date is the same as current_period_end for renewing subscriptions
                    next_billing_date_ts = period_end_from_stripe
                else:
                    # Case 3: No data available from Stripe - return None (NO CALCULATIONS)
                    effective_period_end_ts = None
                    next_billing_date_ts = None
                
                # Set the effective period end (only if we have data from Stripe)
                if effective_period_end_ts is not None:
                    response_data['current_period_end'] = int(effective_period_end_ts) * 1000
                else:
                    response_data['current_period_end'] = None
                
                # Set next billing date (only if subscription is renewing)
                if next_billing_date_ts is not None:
                    response_data['next_billing_date'] = int(next_billing_date_ts) * 1000
                else:
                    response_data['next_billing_date'] = None
                
            except stripe.error.InvalidRequestError as e:
                # Subscription doesn't exist in Stripe (might have been deleted)
                print(f"Subscription {user.stripe_subscription_id} not found in Stripe: {str(e)}")
                # Return basic info without Stripe details
                pass
            except stripe.error.StripeError as e:
                # Other Stripe errors - log but don't fail
                print(f"Stripe error retrieving subscription: {str(e)}")
                # Return basic info without Stripe details
                pass
            except Exception as e:
                # Catch any other unexpected errors when processing subscription
                print(f"Unexpected error processing subscription: {str(e)}")
                import traceback
                traceback.print_exc()
                # Return basic info without Stripe details
                pass
        
        return jsonify(response_data)
        
    except Exception as e:
        print(f"Error getting subscription info: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@bp.route('/stripe/reactivate-subscription', methods=['POST'])
@login_required
@swag_from({
    'tags': ['Stripe'],
    'summary': 'Reactivate subscription',
    'description': 'Reactivate a cancelled subscription',
    'responses': {
        200: {
            'description': 'Subscription reactivated successfully',
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
        400: {'description': 'No subscription found'},
        401: {'description': 'Not authenticated'},
        500: {'description': 'Internal server error'}
    }
})
def reactivate_subscription():
    """Reactivate a cancelled subscription"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if not user.stripe_subscription_id:
            return jsonify({"error": "No subscription found"}), 400
        
        # Get Stripe secret key from config
        secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not secret_key:
            return jsonify({"error": "Stripe secret key not configured"}), 500
        
        # Initialize Stripe with secret key
        stripe.api_key = secret_key
        
        # Reactivate subscription by removing cancel_at_period_end
        subscription = stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        # Update user subscription status
        user.has_active_subscription = True
        db.session.commit()
        
        return jsonify({
            "status": "success",
            "message": "Subscription reactivated successfully"
        })
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({"error": f"Stripe error: {str(e)}"}), 500
    except Exception as e:
        print(f"Error reactivating subscription: {str(e)}")
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route('/stripe/invoices', methods=['GET'])
@login_required
@swag_from({
    'tags': ['Stripe'],
    'summary': 'Get user invoices',
    'description': 'Get invoice history for the authenticated user',
    'responses': {
        200: {
            'description': 'Invoices retrieved',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'invoices': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'string'},
                                        'amount_paid': {'type': 'integer'},
                                        'currency': {'type': 'string'},
                                        'status': {'type': 'string'},
                                        'created': {'type': 'integer'},
                                        'invoice_pdf': {'type': 'string'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {'description': 'No Stripe customer ID'},
        401: {'description': 'Not authenticated'},
        500: {'description': 'Internal server error'}
    }
})
def get_invoices():
    """Get invoice history for the current user"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        if not user.stripe_customer_id:
            return jsonify({"error": "No Stripe customer ID found"}), 400
        
        # Get Stripe secret key from config
        secret_key = current_app.config.get('STRIPE_SECRET_KEY')
        if not secret_key:
            return jsonify({"error": "Stripe secret key not configured"}), 500
        
        # Initialize Stripe with secret key
        stripe.api_key = secret_key
        
        # Get invoices for the customer
        invoices = stripe.Invoice.list(
            customer=user.stripe_customer_id,
            limit=10
        )
        
        invoice_list = []
        for invoice in invoices.data:
            invoice_list.append({
                'id': invoice.id,
                'amount_paid': invoice.amount_paid,
                'currency': invoice.currency,
                'status': invoice.status,
                'created': invoice.created,
                'invoice_pdf': invoice.invoice_pdf,
                'hosted_invoice_url': invoice.hosted_invoice_url
            })
        
        return jsonify({
            'invoices': invoice_list
        })
        
    except stripe.error.StripeError as e:
        print(f"Stripe error: {str(e)}")
        return jsonify({"error": f"Stripe error: {str(e)}"}), 500
    except Exception as e:
        print(f"Error getting invoices: {str(e)}")
        return jsonify({"error": str(e)}), 500

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

# =========================
# Company Invite Endpoints
# =========================

@bp.route('/companies/invites', methods=['POST'])
@login_required
@owner_required
@swag_from({
    'tags': ['Company Invites'],
    'summary': 'Create employee invite',
    'description': 'Create an invite for an employee to join the company (owner only)',
    'requestBody': {
        'required': True,
        'content': {
            'application/json': {
                'schema': {
                    'type': 'object',
                    'required': ['email'],
                    'properties': {
                        'email': {
                            'type': 'string',
                            'format': 'email',
                            'description': 'Email address of the employee to invite'
                        }
                    }
                }
            }
        }
    },
    'responses': {
        201: {
            'description': 'Invite created successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'message': {'type': 'string'},
                            'invite': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'email': {'type': 'string'},
                                    'expires_at': {'type': 'string', 'format': 'date-time'}
                                }
                            }
                        }
                    }
                }
            }
        },
        400: {'description': 'Invalid email or user already exists'},
        403: {'description': 'Only owners can create invites'},
        401: {'description': 'Not authenticated'}
    }
})
def create_company_invite():
    """Create an invite for an employee to join the company"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user or not user.company_id:
            return jsonify({"error": "User must belong to a company"}), 400
        
        data = request.get_json()
        email = (data.get('email') or '').strip().lower()
        
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        # Check if user with this email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({
                "error": "A user with this email already exists",
                "message": "This email is already registered. They can log in directly."
            }), 400
        
        # Check if there's already a pending invite for this email
        existing_invite = CompanyInvite.query.filter_by(
            email=email,
            company_id=user.company_id,
            used=False
        ).first()
        
        if existing_invite:
            # Check if it's expired
            if existing_invite.expires_at < datetime.now(timezone.utc):
                # Delete expired invite and create new one
                db.session.delete(existing_invite)
                db.session.flush()
            else:
                return jsonify({
                    "error": "An active invite already exists for this email",
                    "message": "Please wait for the existing invite to expire or cancel it first"
                }), 400
        
        # Generate secure token
        token = secrets.token_urlsafe(32)
        
        # Set expiration to 7 days from now
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        # Create invite
        invite = CompanyInvite(
            email=email,
            company_id=user.company_id,
            role='employee',
            token=token,
            expires_at=expires_at,
            used=False
        )
        
        db.session.add(invite)
        db.session.commit()
        
        # Send invite email
        try:
            _send_invite_email(invite, user)
        except Exception as e:
            print(f"Error sending invite email: {str(e)}")
            # Don't fail the request if email fails
        
        return jsonify({
            "success": True,
            "message": "Invite created and sent successfully",
            "invite": {
                "id": invite.id,
                "email": invite.email,
                "expires_at": invite.expires_at.isoformat()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@bp.route('/companies/invites/validate/<token>', methods=['GET'])
@swag_from({
    'tags': ['Company Invites'],
    'summary': 'Validate invite token',
    'description': 'Get invite details by token (public endpoint for signup)',
    'parameters': [
        {
            'name': 'token',
            'in': 'path',
            'required': True,
            'schema': {'type': 'string'}
        }
    ],
    'responses': {
        200: {
            'description': 'Invite details retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'email': {'type': 'string'},
                            'company_name': {'type': 'string'},
                            'valid': {'type': 'boolean'}
                        }
                    }
                }
            }
        },
        404: {'description': 'Invite not found or invalid'}
    }
})
def validate_invite_token(token):
    """Validate invite token and return email (public endpoint for signup)"""
    try:
        invite = CompanyInvite.query.filter_by(
            token=token,
            used=False
        ).first()
        
        if not invite:
            return jsonify({
                "success": False,
                "valid": False,
                "error": "Invalid or expired invite"
            }), 404
        
        # Check if invite is expired
        if invite.expires_at < datetime.now(timezone.utc):
            return jsonify({
                "success": False,
                "valid": False,
                "error": "Invite has expired"
            }), 404
        
        # Get company name
        company = Company.query.get(invite.company_id)
        company_name = company.name if company else "Company"
        
        return jsonify({
            "success": True,
            "valid": True,
            "email": invite.email,
            "company_name": company_name
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "valid": False,
            "error": str(e)
        }), 500

@bp.route('/companies/invites', methods=['GET'])
@login_required
@owner_required
@swag_from({
    'tags': ['Company Invites'],
    'summary': 'List company invites',
    'description': 'Get all invites for the current user\'s company (owner only)',
    'responses': {
        200: {
            'description': 'Invites retrieved successfully',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'success': {'type': 'boolean'},
                            'invites': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'id': {'type': 'integer'},
                                        'email': {'type': 'string'},
                                        'role': {'type': 'string'},
                                        'expires_at': {'type': 'string', 'format': 'date-time'},
                                        'accepted_at': {'type': 'string', 'format': 'date-time', 'nullable': True},
                                        'used': {'type': 'boolean'},
                                        'created_at': {'type': 'string', 'format': 'date-time'}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        401: {'description': 'Not authenticated'},
        403: {'description': 'Only owners can view invites'}
    }
})
def list_company_invites():
    """List all invites for the current user's company"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user or not user.company_id:
            return jsonify({"error": "User must belong to a company"}), 400
        
        invites = CompanyInvite.query.filter_by(company_id=user.company_id).order_by(
            CompanyInvite.created_at.desc()
        ).all()
        
        invites_data = [{
            "id": invite.id,
            "email": invite.email,
            "role": invite.role,
            "expires_at": invite.expires_at.isoformat(),
            "accepted_at": invite.accepted_at.isoformat() if invite.accepted_at else None,
            "used": invite.used,
            "created_at": invite.created_at.isoformat()
        } for invite in invites]
        
        return jsonify({
            "success": True,
            "invites": invites_data
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/companies/invites/<int:invite_id>', methods=['DELETE'])
@login_required
@owner_required
@swag_from({
    'tags': ['Company Invites'],
    'summary': 'Cancel invite',
    'description': 'Cancel/delete an invite (owner only)',
    'parameters': [
        {
            'name': 'invite_id',
            'in': 'path',
            'required': True,
            'schema': {'type': 'integer'}
        }
    ],
    'responses': {
        200: {'description': 'Invite cancelled successfully'},
        404: {'description': 'Invite not found'},
        403: {'description': 'Only owners can cancel invites'},
        401: {'description': 'Not authenticated'}
    }
})
def cancel_company_invite(invite_id):
    """Cancel an invite"""
    try:
        user_id = get_current_user_id()
        user = User.query.get(user_id)
        
        if not user or not user.company_id:
            return jsonify({"error": "User must belong to a company"}), 400
        
        invite = CompanyInvite.query.filter_by(
            id=invite_id,
            company_id=user.company_id
        ).first()
        
        if not invite:
            return jsonify({"error": "Invite not found"}), 404
        
        db.session.delete(invite)
        db.session.commit()
        
        return jsonify({
            "success": True,
            "message": "Invite cancelled successfully"
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

def _send_invite_email(invite, owner_user):
    """Send invite email to the employee"""
    from flask_mail import Message
    from app import mail
    from flask import url_for, current_app
    import os
    
    try:
        # Get company name
        company = Company.query.get(invite.company_id)
        company_name = company.name if company else "the company"
        
        # Generate invite link
        BASE_URL = current_app.config.get('BASE_URL', os.getenv("BASE_URL", "https://storyboom.ai"))
        invite_link = f"{BASE_URL}/signup?invite_token={invite.token}"
        
        # Create email message
        msg = Message(
            f'Invitation to join {company_name} on Storyboom.ai',
            recipients=[invite.email]
        )
        
        owner_name = f"{owner_user.first_name} {owner_user.last_name}".strip()
        msg.body = (
            f"Hi there,\n\n"
            f"{owner_name} has invited you to join {company_name} on Storyboom.ai as an employee.\n\n"
            f"Storyboom.ai helps teams create and share success stories. As an employee, you'll be able to:\n"
            f"- View and manage stories created by your team\n"
            f"- Collaborate on case studies\n\n"
            f"To accept this invitation, please click the link below to create your account:\n\n"
            f"{invite_link}\n\n"
            f"This invitation will expire in 7 days.\n\n"
            f"If you did not expect this invitation, you can safely ignore this email.\n\n"
            f"Best regards,\n"
            f"The Storyboom team"
        )
        
        mail.send(msg)
        print(f"Invite email sent to {invite.email}")
        
    except Exception as e:
        print(f"Error sending invite email: {str(e)}")
        raise
