from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime

class UserCreateSchema(Schema):
    """Schema for user registration"""
    first_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    company_name = fields.Str(validate=validate.Length(max=255))
    invite_token = fields.Str(validate=validate.Length(max=255))  # Optional: for employee signup via invite

class UserLoginSchema(Schema):
    """Schema for user login"""
    email = fields.Email(required=True)
    password = fields.Str(required=True)

class UserResponseSchema(Schema):
    """Schema for user response"""
    id = fields.Int(dump_only=True)
    first_name = fields.Str()
    last_name = fields.Str()
    email = fields.Email()
    company_name = fields.Str()
    role = fields.Str()  # 'owner' or 'employee'
    company_id = fields.Int()  # Company ID the user belongs to
    created_at = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True)
    stories_used_this_month = fields.Int()
    extra_credits = fields.Int()
    last_reset_date = fields.Date()
    has_active_subscription = fields.Bool()
    subscription_start_date = fields.Date()

class UserUpdateSchema(Schema):
    """Schema for user updates"""
    first_name = fields.Str(validate=validate.Length(min=1, max=100))
    last_name = fields.Str(validate=validate.Length(min=1, max=100))
    company_name = fields.Str(validate=validate.Length(max=255)) 