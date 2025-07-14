from app.models import Feedback
from app.schemas.feedback_schemas import (
    FeedbackCreateSchema, FeedbackResponseSchema, FeedbackListSchema, FeedbackSessionSchema
)

class FeedbackMapper:
    """Mapper for converting between Feedback models and DTOs"""
    
    @staticmethod
    def model_to_dto(feedback: Feedback) -> dict:
        """Convert Feedback model to DTO"""
        schema = FeedbackResponseSchema()
        return schema.dump(feedback)
    
    @staticmethod
    def dto_to_model(feedback_data: dict) -> Feedback:
        """Convert DTO to Feedback model"""
        schema = FeedbackCreateSchema()
        validated_data = schema.load(feedback_data)
        return Feedback(**validated_data)
    
    @staticmethod
    def models_to_dto_list(feedbacks: list) -> list:
        """Convert list of Feedback models to DTOs"""
        schema = FeedbackResponseSchema(many=True)
        return schema.dump(feedbacks)
    
    @staticmethod
    def models_to_dto_list_with_pagination(feedbacks: list, total: int, page: int, per_page: int) -> dict:
        """Convert list of Feedback models to paginated DTO response"""
        feedbacks_dto = FeedbackMapper.models_to_dto_list(feedbacks)
        return {
            'feedbacks': feedbacks_dto,
            'total': total,
            'page': page,
            'per_page': per_page
        }
    
    @staticmethod
    def session_to_dto(session_id: str) -> dict:
        """Convert feedback session to DTO"""
        schema = FeedbackSessionSchema()
        return schema.dump({
            'session_id': session_id,
            'status': 'started'
        }) 