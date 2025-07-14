import os
import requests
import json
from datetime import datetime, UTC

class MediaService:
    def __init__(self):
        # HeyGen API configuration
        self.heygen_api_key = os.getenv("HEYGEN_API_KEY")
        self.heygen_api_base_url = "https://api.heygen.com/v2"
        self.heygen_avatar_id = "Tuba_Casual_Front_public"
        self.heygen_voice_id = "ea5493f87c244e0e99414ca6bd4af709"
        
        # Pictory API configuration
        self.pictory_client_id = os.getenv("PICTORY_CLIENT_ID")
        self.pictory_client_secret = os.getenv("PICTORY_CLIENT_SECRET")
        self.pictory_user_id = os.getenv("PICTORY_USER_ID")
        self.pictory_api_base_url = "https://api.pictory.ai"
        
        # Wondercraft API configuration
        self.wondercraft_api_key = os.getenv("WONDERCRAFT_API_KEY")
        self.wondercraft_api_base_url = "https://api.wondercraft.ai/v1"
    
    def generate_heygen_input_text(self, final_summary):
        """Generate input text for HeyGen video"""
        try:
            # Limit text to reasonable length for video
            if len(final_summary) > 1000:
                summary = final_summary[:1000] + "..."
            else:
                summary = final_summary
            
            # Format for video narration
            video_text = f"""
            {summary}
            
            This case study demonstrates how innovative solutions can transform business outcomes and drive success.
            """
            
            return video_text.strip()
            
        except Exception as e:
            print(f"Error generating HeyGen input text: {str(e)}")
            return "This case study demonstrates successful business transformation through innovative solutions."
    
    def generate_heygen_video(self, case_study):
        """Generate HeyGen video from case study"""
        try:
            if not self.heygen_api_key:
                return {"error": "HeyGen API key not configured"}
            
            # Generate input text
            input_text = self.generate_heygen_input_text(case_study.final_summary)
            
            # Prepare video generation request
            payload = {
                "video_inputs": [
                    {
                        "character": {
                            "type": "avatar",
                            "avatar_id": self.heygen_avatar_id,
                            "input_text": input_text,
                            "voice_id": self.heygen_voice_id
                        }
                    }
                ],
                "test": False,
                "aspect_ratio": "16:9"
            }
            
            headers = {
                "X-Api-Key": self.heygen_api_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.heygen_api_base_url}/video/generate",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "video_id": result.get("data", {}).get("video_id"),
                    "status": "processing"
                }
            else:
                return {"error": f"HeyGen API error: {response.status_code}"}
                
        except Exception as e:
            print(f"Error generating HeyGen video: {str(e)}")
            return {"error": str(e)}
    
    def check_heygen_video_status(self, video_id):
        """Check status of HeyGen video generation"""
        try:
            if not self.heygen_api_key:
                return {"error": "HeyGen API key not configured"}
            
            headers = {
                "X-Api-Key": self.heygen_api_key
            }
            
            response = requests.get(
                f"{self.heygen_api_base_url}/video/{video_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                data = result.get("data", {})
                
                status = data.get("status", "unknown")
                video_url = data.get("video_url") if status == "completed" else None
                
                return {
                    "status": status,
                    "video_url": video_url
                }
            else:
                return {"error": f"HeyGen API error: {response.status_code}"}
                
        except Exception as e:
            print(f"Error checking HeyGen video status: {str(e)}")
            return {"error": str(e)}
    
    def get_pictory_access_token(self):
        """Get access token from Pictory API."""
        try:
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "client_id": self.pictory_client_id,
                "client_secret": self.pictory_client_secret
            }
            
            response = requests.post(
                f"{self.pictory_api_base_url}/pictoryapis/v1/oauth2/token",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json().get("access_token")
            else:
                print(f"Pictory token error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error getting Pictory access token: {str(e)}")
            return None
    
    def generate_pictory_scenes_text(self, final_summary):
        """Generate scenes text for Pictory video"""
        try:
            # Split summary into scenes
            paragraphs = final_summary.split('\n\n')
            scenes = []
            
            for i, paragraph in enumerate(paragraphs[:5]):  # Limit to 5 scenes
                if paragraph.strip():
                    scenes.append({
                        "scene_number": i + 1,
                        "text": paragraph.strip()[:200]  # Limit text per scene
                    })
            
            return scenes
            
        except Exception as e:
            print(f"Error generating Pictory scenes: {str(e)}")
            return [{"scene_number": 1, "text": "Case study summary"}]
    
    def create_pictory_storyboard(self, token, scenes, video_name):
        """Create a storyboard using Pictory API."""
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Pictory-User-Id": self.pictory_user_id,
                "Content-Type": "application/json"
            }
            
            # Debug: Print the scenes being sent
            print(f"Generated scenes for Pictory:")
            for i, scene in enumerate(scenes, 1):
                print(f"Scene {i}: {scene}")
            
            # Create scenes array for Pictory
            # Combine all scenes into one story and let Pictory handle scene creation
            combined_story = " ".join(scenes)
            print(f"Combined story: {combined_story}")
            
            pictory_scenes = [{
                "story": combined_story,
                "createSceneOnNewLine": False,
                "createSceneOnEndOfSentence": True  # Create scenes at sentence boundaries
            }]
            
            payload = {
                "videoName": video_name,
                "videoWidth": 1080,
                "videoHeight": 1920,  # Vertical format for short-form
                "language": "en",
                "saveProject": True,
                "scenes": pictory_scenes,
                "voiceOver": {
                    "enabled": True,
                    "aiVoices": [
                        {
                            "speaker": "Adison",
                            "speed": 100,  # Must be >= 50 according to API
                            "amplificationLevel": 0
                        }
                    ]
                },
                "backgroundMusic": {
                    "enabled": True,
                    "autoMusic": True,
                    "volume": 0.3  # Low volume as requested
                }
            }
            
            response = requests.post(
                f"{self.pictory_api_base_url}/pictoryapis/v2/video/storyboard",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                return response.json().get("data", {}).get("jobId")
            else:
                print(f"Pictory storyboard error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error creating Pictory storyboard: {str(e)}")
            return None
    
    def render_pictory_video(self, token, storyboard_job_id):
        """Render the storyboard to video using Pictory API."""
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Pictory-User-Id": self.pictory_user_id,
                "Content-Type": "application/json"
            }
            
            response = requests.put(
                f"{self.pictory_api_base_url}/pictoryapis/v2/video/render/{storyboard_job_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json().get("data", {}).get("jobId")
            else:
                print(f"Pictory render error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error rendering Pictory video: {str(e)}")
            return None
    
    def check_pictory_job_status(self, token, job_id):
        """Check the status of a Pictory job."""
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "X-Pictory-User-Id": self.pictory_user_id,
                "accept": "application/json",
                "Content-Type": "application/json"
            }
            
            print(f"Checking Pictory job status for job_id: {job_id}")
            print(f"Using headers: {headers}")
            
            # Use the "Get Job" endpoint from the Jobs section
            response = requests.get(
                f"{self.pictory_api_base_url}/pictoryapis/v1/jobs/{job_id}",
                headers=headers
            )
            
            print(f"Pictory job status response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                data = response.json().get("data", {})
                print(f"Pictory job data: {data}")
                return data
            else:
                print(f"Pictory job status error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error checking Pictory job status: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def generate_pictory_video(self, case_study):
        """Generate Pictory video from case study"""
        try:
            # Get access token
            token = self.get_pictory_access_token()
            if not token:
                return {"error": "Failed to get Pictory access token"}
            
            # Generate scenes
            scenes = self.generate_pictory_scenes_text(case_study.final_summary)
            video_name = f"Case Study - {case_study.id}"
            
            # Create storyboard
            storyboard_job_id = self.create_pictory_storyboard(token, scenes, video_name)
            if not storyboard_job_id:
                return {"error": "Failed to create Pictory storyboard"}
            
            # Render video
            render_job_id = self.render_pictory_video(token, storyboard_job_id)
            if not render_job_id:
                return {"error": "Failed to render Pictory video"}
            
            return {
                "storyboard_id": storyboard_job_id,
                "render_id": render_job_id,
                "status": "processing"
            }
            
        except Exception as e:
            print(f"Error generating Pictory video: {str(e)}")
            return {"error": str(e)}
    
    def check_pictory_video_status(self, storyboard_job_id):
        """Check status of Pictory video generation"""
        try:
            # Get access token
            token = self.get_pictory_access_token()
            if not token:
                return {"error": "Failed to get Pictory access token"}
            
            # Check storyboard status
            storyboard_status = self.check_pictory_job_status(token, storyboard_job_id)
            
            if storyboard_status == "completed":
                # Check render status if available
                # This would require storing the render_job_id somewhere
                return {
                    "status": "completed",
                    "video_url": f"https://pictory.ai/video/{storyboard_job_id}"  # Example URL
                }
            else:
                return {
                    "status": storyboard_status
                }
                
        except Exception as e:
            print(f"Error checking Pictory video status: {str(e)}")
            return {"error": str(e)}
    
    def generate_wondercraft_podcast(self, script):
        """Generate Wondercraft podcast from script"""
        try:
            if not self.wondercraft_api_key:
                return {"error": "Wondercraft API key not configured"}
            
            headers = {
                "Authorization": f"Bearer {self.wondercraft_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "script": script,
                "voice_ids": [
                    "f79709a9-6b2c-4333-9bdf-dd5973a1d55b",
                    "3b650d7d-4918-402d-a9fe-b28b50cc5bee"
                ],
                "format": "mp3"
            }
            
            response = requests.post(
                f"{self.wondercraft_api_base_url}/podcast/generate",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "job_id": result.get("job_id"),
                    "status": "processing"
                }
            else:
                return {"error": f"Wondercraft API error: {response.status_code}"}
                
        except Exception as e:
            print(f"Error generating Wondercraft podcast: {str(e)}")
            return {"error": str(e)}
    
    def check_wondercraft_podcast_status(self, job_id):
        """Check status of Wondercraft podcast generation"""
        try:
            if not self.wondercraft_api_key:
                return {"error": "Wondercraft API key not configured"}
            
            headers = {
                "Authorization": f"Bearer {self.wondercraft_api_key}"
            }
            
            response = requests.get(
                f"{self.wondercraft_api_base_url}/podcast/{job_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                result = response.json()
                
                status = result.get("status", "unknown")
                audio_url = result.get("audio_url") if status == "completed" else None
                
                return {
                    "status": status,
                    "audio_url": audio_url
                }
            else:
                return {"error": f"Wondercraft API error: {response.status_code}"}
                
        except Exception as e:
            print(f"Error checking Wondercraft podcast status: {str(e)}")
            return {"error": str(e)} 