from app.models import CaseStudy, Label
from app.schemas.case_study_schemas import (
    CaseStudyResponseSchema, CaseStudyCreateSchema, CaseStudyUpdateSchema,
    CaseStudyListSchema, LabelResponseSchema, LabelCreateSchema, LabelUpdateSchema
)

class CaseStudyMapper:
    """Mapper for converting between CaseStudy models and DTOs"""
    
    @staticmethod
    def model_to_dto(case_study: CaseStudy) -> dict:
        """Convert CaseStudy model to DTO"""
        schema = CaseStudyResponseSchema()
        return schema.dump(case_study)
    
    @staticmethod
    def dto_to_model(case_study_data: dict) -> CaseStudy:
        """Convert DTO to CaseStudy model"""
        schema = CaseStudyCreateSchema()
        validated_data = schema.load(case_study_data)
        return CaseStudy(**validated_data)
    
    @staticmethod
    def update_model_from_dto(case_study: CaseStudy, case_study_data: dict) -> CaseStudy:
        """Update CaseStudy model from DTO"""
        schema = CaseStudyUpdateSchema()
        validated_data = schema.load(case_study_data, partial=True)
        
        for key, value in validated_data.items():
            setattr(case_study, key, value)
        
        return case_study
    
    @staticmethod
    def models_to_dto_list(case_studies: list) -> list:
        """Convert list of CaseStudy models to DTOs"""
        schema = CaseStudyResponseSchema(many=True)
        return schema.dump(case_studies)
    
    @staticmethod
    def models_to_dto_list_with_pagination(case_studies: list, total: int, page: int, per_page: int) -> dict:
        """Convert list of CaseStudy models to paginated DTO response"""
        case_studies_dto = CaseStudyMapper.models_to_dto_list(case_studies)
        return {
            'case_studies': case_studies_dto,
            'total': total,
            'page': page,
            'per_page': per_page
        }

class LabelMapper:
    """Mapper for converting between Label models and DTOs"""
    
    @staticmethod
    def model_to_dto(label: Label) -> dict:
        """Convert Label model to DTO"""
        schema = LabelResponseSchema()
        return schema.dump(label)
    
    @staticmethod
    def dto_to_model(label_data: dict) -> Label:
        """Convert DTO to Label model"""
        schema = LabelCreateSchema()
        validated_data = schema.load(label_data)
        return Label(**validated_data)
    
    @staticmethod
    def update_model_from_dto(label: Label, label_data: dict) -> Label:
        """Update Label model from DTO"""
        schema = LabelUpdateSchema()
        validated_data = schema.load(label_data)
        
        for key, value in validated_data.items():
            setattr(label, key, value)
        
        return label
    
    @staticmethod
    def models_to_dto_list(labels: list) -> list:
        """Convert list of Label models to DTOs"""
        schema = LabelResponseSchema(many=True)
        return schema.dump(labels) 