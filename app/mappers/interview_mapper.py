from app.models import SolutionProviderInterview, ClientInterview, InviteToken
from app.schemas.interview_schemas import (
    InterviewSessionSchema, TranscriptSaveSchema, ProviderSummarySchema,
    ClientTranscriptSchema, ClientSummarySchema, ClientSummaryResponseSchema,
    NamesExtractionSchema, NamesResponseSchema, FullCaseStudySchema,
    FullCaseStudyResponseSchema, InviteTokenSchema, ClientInterviewLinkSchema,
    ClientInterviewLinkResponseSchema
)

class InterviewMapper:
    """Mapper for converting between Interview models and DTOs"""
    
    @staticmethod
    def session_to_dto(session_id: str) -> dict:
        """Convert session to DTO"""
        schema = InterviewSessionSchema()
        return schema.dump({
            'session_id': session_id,
            'status': 'created'
        })
    
    @staticmethod
    def transcript_save_to_dto(transcript: str, session_id: str) -> dict:
        """Convert transcript save data to DTO"""
        schema = TranscriptSaveSchema()
        return schema.dump({
            'transcript': transcript,
            'session_id': session_id
        })
    
    @staticmethod
    def provider_summary_to_dto(summary: str, session_id: str) -> dict:
        """Convert provider summary data to DTO"""
        schema = ProviderSummarySchema()
        return schema.dump({
            'summary': summary,
            'session_id': session_id
        })
    
    @staticmethod
    def client_transcript_to_dto(transcript: str, token: str) -> dict:
        """Convert client transcript data to DTO"""
        schema = ClientTranscriptSchema()
        return schema.dump({
            'transcript': transcript,
            'token': token
        })
    
    @staticmethod
    def client_summary_to_dto(transcript: str, token: str) -> dict:
        """Convert client summary data to DTO"""
        schema = ClientSummarySchema()
        return schema.dump({
            'transcript': transcript,
            'token': token
        })
    
    @staticmethod
    def client_summary_response_to_dto(client_summary: str) -> dict:
        """Convert client summary response to DTO"""
        schema = ClientSummaryResponseSchema()
        return schema.dump({
            'client_summary': client_summary,
            'status': 'success'
        })
    
    @staticmethod
    def names_extraction_to_dto(case_study_text: str) -> dict:
        """Convert names extraction data to DTO"""
        schema = NamesExtractionSchema()
        return schema.dump({
            'case_study_text': case_study_text
        })
    
    @staticmethod
    def names_response_to_dto(lead_entity: str, partner_entity: str, project_title: str) -> dict:
        """Convert names response to DTO"""
        schema = NamesResponseSchema()
        return schema.dump({
            'lead_entity': lead_entity,
            'partner_entity': partner_entity,
            'project_title': project_title
        })
    
    @staticmethod
    def full_case_study_to_dto(case_study_id: int) -> dict:
        """Convert full case study data to DTO"""
        schema = FullCaseStudySchema()
        return schema.dump({
            'case_study_id': case_study_id
        })
    
    @staticmethod
    def full_case_study_response_to_dto(full_case_study: str, pdf_path: str) -> dict:
        """Convert full case study response to DTO"""
        schema = FullCaseStudyResponseSchema()
        return schema.dump({
            'full_case_study': full_case_study,
            'pdf_path': pdf_path,
            'status': 'success'
        })
    
    @staticmethod
    def invite_token_to_dto(invite_token: InviteToken) -> dict:
        """Convert InviteToken model to DTO"""
        schema = InviteTokenSchema()
        return schema.dump(invite_token)
    
    @staticmethod
    def client_interview_link_to_dto(case_study_id: int) -> dict:
        """Convert client interview link data to DTO"""
        schema = ClientInterviewLinkSchema()
        return schema.dump({
            'case_study_id': case_study_id
        })
    
    @staticmethod
    def client_interview_link_response_to_dto(token: str, client_url: str) -> dict:
        """Convert client interview link response to DTO"""
        schema = ClientInterviewLinkResponseSchema()
        return schema.dump({
            'token': token,
            'client_url': client_url
        }) 