from marshmallow import Schema, fields, validate
from datetime import datetime

class VideoGenerationSchema(Schema):
    """Schema for video generation"""
    case_study_id = fields.Int(required=True)

class VideoGenerationResponseSchema(Schema):
    """Schema for video generation response"""
    video_id = fields.Str()
    status = fields.Str()

class VideoStatusResponseSchema(Schema):
    """Schema for video status response"""
    status = fields.Str()
    video_url = fields.Str()

class PictoryVideoSchema(Schema):
    """Schema for Pictory video generation"""
    case_study_id = fields.Int(required=True)

class PictoryVideoResponseSchema(Schema):
    """Schema for Pictory video response"""
    storyboard_id = fields.Str()
    status = fields.Str()

class PictoryStatusResponseSchema(Schema):
    """Schema for Pictory status response"""
    status = fields.Str()
    video_url = fields.Str()

class PodcastGenerationSchema(Schema):
    """Schema for podcast generation"""
    case_study_id = fields.Int(required=True)

class PodcastGenerationResponseSchema(Schema):
    """Schema for podcast generation response"""
    job_id = fields.Str()
    status = fields.Str()

class PodcastStatusResponseSchema(Schema):
    """Schema for podcast status response"""
    status = fields.Str()
    audio_url = fields.Str()

class LinkedInPostSchema(Schema):
    """Schema for LinkedIn post generation"""
    case_study_id = fields.Int(required=True)

class LinkedInPostResponseSchema(Schema):
    """Schema for LinkedIn post response"""
    linkedin_post = fields.Str()
    status = fields.Str()

class MediaJobSchema(Schema):
    """Schema for media job tracking"""
    job_id = fields.Str(required=True)
    job_type = fields.Str(required=True, validate=validate.OneOf(['video', 'pictory', 'podcast']))
    status = fields.Str()
    created_at = fields.DateTime(dump_only=True)
    completed_at = fields.DateTime(dump_only=True)
    result_url = fields.Str(dump_only=True) 