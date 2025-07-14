from marshmallow import Schema, fields, validate
from datetime import datetime

class CaseStudyCreateSchema(Schema):
    """Schema for creating a case study"""
    title = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    final_summary = fields.Str(required=True)

class CaseStudyUpdateSchema(Schema):
    """Schema for updating a case study"""
    title = fields.Str(validate=validate.Length(min=1, max=200))
    final_summary = fields.Str()
    meta_data_text = fields.Str()
    linkedin_post = fields.Str()

class CaseStudyResponseSchema(Schema):
    """Schema for case study response"""
    id = fields.Int(dump_only=True)
    title = fields.Str()
    final_summary = fields.Str()
    final_summary_pdf_path = fields.Str(dump_only=True)
    meta_data_text = fields.Str()
    linkedin_post = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    
    # Media fields
    video_id = fields.Str(dump_only=True)
    video_url = fields.Str(dump_only=True)
    video_status = fields.Str(dump_only=True)
    video_created_at = fields.DateTime(dump_only=True)
    
    pictory_storyboard_id = fields.Str(dump_only=True)
    pictory_render_id = fields.Str(dump_only=True)
    pictory_video_url = fields.Str(dump_only=True)
    pictory_video_status = fields.Str(dump_only=True)
    pictory_video_created_at = fields.DateTime(dump_only=True)
    
    podcast_job_id = fields.Str(dump_only=True)
    podcast_url = fields.Str(dump_only=True)
    podcast_status = fields.Str(dump_only=True)
    podcast_created_at = fields.DateTime(dump_only=True)
    podcast_script = fields.Str(dump_only=True)
    
    # Relationships
    labels = fields.Nested('LabelResponseSchema', many=True, dump_only=True)

class CaseStudyListSchema(Schema):
    """Schema for case study list response"""
    case_studies = fields.Nested(CaseStudyResponseSchema, many=True)
    total = fields.Int()
    page = fields.Int()
    per_page = fields.Int()

class LabelSchema(Schema):
    """Schema for labels"""
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64))
    created_at = fields.DateTime(dump_only=True)

class LabelResponseSchema(Schema):
    """Schema for label response"""
    id = fields.Int(dump_only=True)
    name = fields.Str()
    created_at = fields.DateTime(dump_only=True)

class LabelCreateSchema(Schema):
    """Schema for creating a label"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64))

class LabelUpdateSchema(Schema):
    """Schema for updating a label"""
    name = fields.Str(required=True, validate=validate.Length(min=1, max=64)) 