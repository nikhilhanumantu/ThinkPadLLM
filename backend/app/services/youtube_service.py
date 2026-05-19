from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import re


def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/shorts\/([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_transcript(video_id: str) -> dict:
    """Fetch transcript for a YouTube video."""
    try:
        # Try to get English transcript first
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            transcript = transcript_list.find_transcript(['en', 'en-US', 'en-GB'])
        except NoTranscriptFound:
            # Fall back to auto-generated or translated
            try:
                transcript = transcript_list.find_generated_transcript(['en'])
            except:
                # Get the first available and translate
                transcript = transcript_list.find_transcript(
                    [t.language_code for t in transcript_list]
                )
                transcript = transcript.translate('en')
        
        entries = transcript.fetch()
        
        # Build full text
        full_text = ' '.join([entry['text'] for entry in entries])
        
        # Build timestamped segments (every 30 seconds)
        segments = []
        segment_text = []
        segment_start = 0
        segment_duration = 30

        for entry in entries:
            if entry['start'] - segment_start >= segment_duration and segment_text:
                segments.append({
                    "start": segment_start,
                    "start_formatted": format_time(segment_start),
                    "text": ' '.join(segment_text),
                })
                segment_start = entry['start']
                segment_text = [entry['text']]
            else:
                segment_text.append(entry['text'])
        
        if segment_text:
            segments.append({
                "start": segment_start,
                "start_formatted": format_time(segment_start),
                "text": ' '.join(segment_text),
            })
        
        return {
            "success": True,
            "transcript": full_text,
            "segments": segments,
            "duration": entries[-1]['start'] + entries[-1].get('duration', 0) if entries else 0,
            "word_count": len(full_text.split()),
        }
    
    except TranscriptsDisabled:
        return {
            "success": False,
            "error": "Transcripts are disabled for this video. Please try a different video.",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Could not fetch transcript: {str(e)}",
        }


def format_time(seconds: float) -> str:
    """Format seconds to MM:SS or HH:MM:SS."""
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
