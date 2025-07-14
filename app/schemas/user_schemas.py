from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime

class UserCreateSchema(Schema):
    """Schema for user registration"""
    first_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    last_name = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8))
    company_name = fields.Str(validate=validate.Length(max=255))

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
    created_at = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True)

class UserUpdateSchema(Schema):
    """Schema for user updates"""
    first_name = fields.Str(validate=validate.Length(min=1, max=100))
    last_name = fields.Str(validate=validate.Length(min=1, max=100))
    company_name = fields.Str(validate=validate.Length(max=255)) 