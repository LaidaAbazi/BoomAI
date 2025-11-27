from app.models import User
from app.schemas.user_schemas import UserResponseSchema, UserCreateSchema, UserUpdateSchema
from werkzeug.security import generate_password_hash

class UserMapper:
    """Mapper for converting between User models and DTOs"""
    
    @staticmethod
    def model_to_dto(user: User) -> dict:
        """Convert User model to DTO"""
        schema = UserResponseSchema()
        return schema.dump(user)
    
    @staticmethod
    def dto_to_model(user_data: dict) -> User:
        """Convert DTO to User model"""
        schema = UserCreateSchema()
        validated_data = schema.load(user_data)
        
        # Hash password if present
        if 'password' in validated_data:
            validated_data['password_hash'] = generate_password_hash(validated_data.pop('password'))
        
        # Remove invite_token - it's not a User model field, only used for validation
        validated_data.pop('invite_token', None)
        
        return User(**validated_data)
    
    @staticmethod
    def update_model_from_dto(user: User, user_data: dict) -> User:
        """Update User model from DTO"""
        schema = UserUpdateSchema()
        validated_data = schema.load(user_data, partial=True)
        
        for key, value in validated_data.items():
            setattr(user, key, value)
        
        return user
    
    @staticmethod
    def models_to_dto_list(users: list) -> list:
        """Convert list of User models to DTOs"""
        schema = UserResponseSchema(many=True)
        return schema.dump(users) 