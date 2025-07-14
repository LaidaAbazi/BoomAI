from marshmallow import Schema, fields, validate
from datetime import datetime

class FeedbackCreateSchema(Schema):
    """Schema for creating feedback"""
    content = fields.Str(required=True, validate=validate.Length(min=1))
    rating = fields.Int(validate=validate.Range(min=1, max=5))
    feedback_type = fields.Str(validate=validate.OneOf(['feature', 'bug', 'improvement', 'general']))

class FeedbackResponseSchema(Schema):
    """Schema for feedback response"""
    id = fields.Int(dump_only=True)
    content = fields.Str()
    rating = fields.Int()
    feedback_type = fields.Str()
    status = fields.Str()
    created_at = fields.DateTime(dump_only=True)

class FeedbackListSchema(Schema):
    """Schema for feedback list response"""
    feedbacks = fields.Nested(FeedbackResponseSchema, many=True)
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()

class FeedbackSessionSchema(Schema):
    """Schema for feedback session"""
    session_id = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True) 