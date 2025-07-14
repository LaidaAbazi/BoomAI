from marshmallow import Schema, fields, validate
from datetime import datetime

class InterviewSessionSchema(Schema):
    """Schema for interview session creation"""
    session_id = fields.Str(dump_only=True)
    status = fields.Str(dump_only=True)

class TranscriptSaveSchema(Schema):
    """Schema for saving transcript"""
    transcript = fields.Str(required=True)
    session_id = fields.Str(required=True)

class ProviderSummarySchema(Schema):
    """Schema for provider summary"""
    summary = fields.Str(required=True)
    session_id = fields.Str(required=True)

class ClientTranscriptSchema(Schema):
    """Schema for client transcript"""
    transcript = fields.Str(required=True)
    token = fields.Str(required=True)

class ClientSummarySchema(Schema):
    """Schema for client summary generation"""
    transcript = fields.Str(required=True)
    token = fields.Str(required=True)

class ClientSummaryResponseSchema(Schema):
    """Schema for client summary response"""
    client_summary = fields.Str()
    status = fields.Str()

class NamesExtractionSchema(Schema):
    """Schema for name extraction"""
    case_study_text = fields.Str(required=True)

class NamesResponseSchema(Schema):
    """Schema for extracted names response"""
    lead_entity = fields.Str()
    partner_entity = fields.Str()
    project_title = fields.Str()

class FullCaseStudySchema(Schema):
    """Schema for full case study generation"""
    case_study_id = fields.Int(required=True)

class FullCaseStudyResponseSchema(Schema):
    """Schema for full case study response"""
    full_case_study = fields.Str()
    pdf_path = fields.Str()
    status = fields.Str()

class InviteTokenSchema(Schema):
    """Schema for invite token"""
    token = fields.Str(dump_only=True)
    used = fields.Bool(dump_only=True)
    created_at = fields.DateTime(dump_only=True)

class ClientInterviewLinkSchema(Schema):
    """Schema for client interview link generation"""
    case_study_id = fields.Int(required=True)

class ClientInterviewLinkResponseSchema(Schema):
    """Schema for client interview link response"""
    token = fields.Str()
    client_url = fields.Str() 