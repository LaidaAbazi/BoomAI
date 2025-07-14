from app.models import CaseStudy
from app.schemas.media_schemas import (
    VideoGenerationSchema, VideoGenerationResponseSchema, VideoStatusResponseSchema,
    PictoryVideoSchema, PictoryVideoResponseSchema, PictoryStatusResponseSchema,
    PodcastGenerationSchema, PodcastGenerationResponseSchema, PodcastStatusResponseSchema,
    LinkedInPostSchema, LinkedInPostResponseSchema, MediaJobSchema
)

class MediaMapper:
    """Mapper for converting between Media models and DTOs"""
    
    @staticmethod
    def video_generation_to_dto(case_study_id: int) -> dict:
        """Convert video generation data to DTO"""
        schema = VideoGenerationSchema()
        return schema.dump({
            'case_study_id': case_study_id
        })
    
    @staticmethod
    def video_generation_response_to_dto(video_id: str) -> dict:
        """Convert video generation response to DTO"""
        schema = VideoGenerationResponseSchema()
        return schema.dump({
            'video_id': video_id,
            'status': 'processing'
        })
    
    @staticmethod
    def video_status_response_to_dto(status: str, video_url: str = None) -> dict:
        """Convert video status response to DTO"""
        schema = VideoStatusResponseSchema()
        return schema.dump({
            'status': status,
            'video_url': video_url
        })
    
    @staticmethod
    def pictory_video_to_dto(case_study_id: int) -> dict:
        """Convert Pictory video generation data to DTO"""
        schema = PictoryVideoSchema()
        return schema.dump({
            'case_study_id': case_study_id
        })
    
    @staticmethod
    def pictory_video_response_to_dto(storyboard_id: str) -> dict:
        """Convert Pictory video response to DTO"""
        schema = PictoryVideoResponseSchema()
        return schema.dump({
            'storyboard_id': storyboard_id,
            'status': 'processing'
        })
    
    @staticmethod
    def pictory_status_response_to_dto(status: str, video_url: str = None) -> dict:
        """Convert Pictory status response to DTO"""
        schema = PictoryStatusResponseSchema()
        return schema.dump({
            'status': status,
            'video_url': video_url
        })
    
    @staticmethod
    def podcast_generation_to_dto(case_study_id: int) -> dict:
        """Convert podcast generation data to DTO"""
        schema = PodcastGenerationSchema()
        return schema.dump({
            'case_study_id': case_study_id
        })
    
    @staticmethod
    def podcast_generation_response_to_dto(job_id: str) -> dict:
        """Convert podcast generation response to DTO"""
        schema = PodcastGenerationResponseSchema()
        return schema.dump({
            'job_id': job_id,
            'status': 'processing'
        })
    
    @staticmethod
    def podcast_status_response_to_dto(status: str, audio_url: str = None) -> dict:
        """Convert podcast status response to DTO"""
        schema = PodcastStatusResponseSchema()
        return schema.dump({
            'status': status,
            'audio_url': audio_url
        })
    
    @staticmethod
    def linkedin_post_to_dto(case_study_id: int) -> dict:
        """Convert LinkedIn post generation data to DTO"""
        schema = LinkedInPostSchema()
        return schema.dump({
            'case_study_id': case_study_id
        })
    
    @staticmethod
    def linkedin_post_response_to_dto(linkedin_post: str) -> dict:
        """Convert LinkedIn post response to DTO"""
        schema = LinkedInPostResponseSchema()
        return schema.dump({
            'linkedin_post': linkedin_post,
            'status': 'success'
        })
    
    @staticmethod
    def media_job_to_dto(job_id: str, job_type: str, status: str, 
                        created_at=None, completed_at=None, result_url=None) -> dict:
        """Convert media job to DTO"""
        schema = MediaJobSchema()
        return schema.dump({
            'job_id': job_id,
            'job_type': job_type,
            'status': status,
            'created_at': created_at,
            'completed_at': completed_at,
            'result_url': result_url
        }) 