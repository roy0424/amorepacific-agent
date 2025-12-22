"""
YouTube 크롤러
YouTube Data API v3 사용
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
from loguru import logger
import isodate


class YouTubeScraper:
    """YouTube Data API v3를 사용한 영상 검색 및 메트릭 수집"""

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: YouTube Data API v3 키 (없으면 환경변수에서 로드)
        """
        self.api_key = api_key or os.getenv("YOUTUBE_API_KEY")
        if not self.api_key:
            raise ValueError("YouTube API key not found. Set YOUTUBE_API_KEY environment variable.")

        self.youtube = build('youtube', 'v3', developerKey=self.api_key)
        logger.info("YouTube API client initialized")

    def search_videos(
        self,
        query: str,
        max_results: int = 50,
        order: str = "relevance",
        published_after: Optional[datetime] = None
    ) -> List[Dict]:
        """
        키워드로 영상 검색

        Args:
            query: 검색 키워드 (예: 'laneige')
            max_results: 최대 결과 수 (기본 50, 최대 50)
            order: 정렬 방식 ('relevance', 'date', 'viewCount', 'rating')
            published_after: 이후 날짜 필터 (datetime 객체)

        Returns:
            영상 정보 리스트
        """
        try:
            search_params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': min(max_results, 50),  # API 제한
                'order': order,
                'videoDefinition': 'any',
                'relevanceLanguage': 'en'  # 영어 우선 (글로벌)
            }

            # 날짜 필터 추가
            if published_after:
                search_params['publishedAfter'] = published_after.isoformat() + 'Z'

            logger.info(f"Searching YouTube: query='{query}', max={max_results}, order={order}")

            search_response = self.youtube.search().list(**search_params).execute()

            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]

            if not video_ids:
                logger.warning(f"No videos found for query: {query}")
                return []

            # 영상 상세 정보 및 통계 가져오기
            videos = self.get_video_details(video_ids)

            logger.info(f"Found {len(videos)} videos for query: {query}")
            return videos

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error searching YouTube videos: {e}")
            raise

    def get_video_details(self, video_ids: List[str]) -> List[Dict]:
        """
        영상 ID 리스트로 상세 정보 및 통계 가져오기

        Args:
            video_ids: YouTube 영상 ID 리스트

        Returns:
            영상 정보 및 통계 리스트
        """
        try:
            if not video_ids:
                return []

            # API는 한 번에 최대 50개까지 처리 가능
            videos = []

            for i in range(0, len(video_ids), 50):
                batch_ids = video_ids[i:i+50]

                video_response = self.youtube.videos().list(
                    part='snippet,statistics,contentDetails',
                    id=','.join(batch_ids)
                ).execute()

                for item in video_response.get('items', []):
                    video_data = self._parse_video_item(item)
                    videos.append(video_data)

            return videos

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting video details: {e}")
            raise

    def _parse_video_item(self, item: Dict) -> Dict:
        """
        YouTube API 응답을 파싱하여 구조화된 데이터로 변환

        Args:
            item: YouTube API videos.list() 응답 아이템

        Returns:
            파싱된 영상 데이터
        """
        snippet = item.get('snippet', {})
        statistics = item.get('statistics', {})
        content_details = item.get('contentDetails', {})

        # ISO 8601 duration 파싱 (예: PT1H2M10S -> 3730초)
        duration_iso = content_details.get('duration', 'PT0S')
        try:
            duration = isodate.parse_duration(duration_iso)
            duration_seconds = int(duration.total_seconds())
        except Exception:
            duration_seconds = 0

        # 발행일 파싱
        published_at_str = snippet.get('publishedAt')
        published_at = None
        if published_at_str:
            try:
                published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
            except Exception:
                pass

        # 태그 처리
        tags = snippet.get('tags', [])
        tags_str = ','.join(tags) if tags else None

        return {
            'video_id': item['id'],
            'channel_id': snippet.get('channelId'),
            'channel_title': snippet.get('channelTitle'),
            'title': snippet.get('title', ''),
            'description': snippet.get('description', ''),
            'tags': tags_str,
            'video_url': f"https://www.youtube.com/watch?v={item['id']}",
            'thumbnail_url': snippet.get('thumbnails', {}).get('high', {}).get('url'),
            'duration_seconds': duration_seconds,
            'published_at': published_at,
            # 메트릭
            'view_count': int(statistics.get('viewCount', 0)),
            'like_count': int(statistics.get('likeCount', 0)),
            'comment_count': int(statistics.get('commentCount', 0)),
            'favorite_count': int(statistics.get('favoriteCount', 0)),
        }

    def search_by_hashtag(self, hashtag: str, max_results: int = 50) -> List[Dict]:
        """
        해시태그로 영상 검색

        Args:
            hashtag: 해시태그 (# 포함 또는 미포함)
            max_results: 최대 결과 수

        Returns:
            영상 정보 리스트
        """
        # # 제거
        clean_tag = hashtag.lstrip('#')
        return self.search_videos(f"#{clean_tag}", max_results=max_results)

    def get_channel_videos(
        self,
        channel_id: str,
        max_results: int = 50
    ) -> List[Dict]:
        """
        특정 채널의 최신 영상 가져오기

        Args:
            channel_id: YouTube 채널 ID
            max_results: 최대 결과 수

        Returns:
            영상 정보 리스트
        """
        try:
            search_response = self.youtube.search().list(
                part='snippet',
                channelId=channel_id,
                type='video',
                maxResults=min(max_results, 50),
                order='date'
            ).execute()

            video_ids = [item['id']['videoId'] for item in search_response.get('items', [])]

            if not video_ids:
                logger.warning(f"No videos found for channel: {channel_id}")
                return []

            return self.get_video_details(video_ids)

        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting channel videos: {e}")
            raise

    def get_video_comments(
        self,
        video_id: str,
        max_results: int = 100
    ) -> List[Dict]:
        """
        영상의 댓글 가져오기

        Args:
            video_id: YouTube 영상 ID
            max_results: 최대 댓글 수 (기본 100, 최대 100)

        Returns:
            댓글 정보 리스트
        """
        try:
            logger.info(f"Fetching comments for video: {video_id}, max={max_results}")

            comments = []
            request = self.youtube.commentThreads().list(
                part='snippet,replies',
                videoId=video_id,
                maxResults=min(max_results, 100),
                order='relevance',  # 관련도 순 (인기 댓글 우선)
                textFormat='plainText'
            )

            while request and len(comments) < max_results:
                response = request.execute()

                for item in response.get('items', []):
                    top_comment = item['snippet']['topLevelComment']['snippet']

                    comment_data = {
                        'comment_id': item['snippet']['topLevelComment']['id'],
                        'author_name': top_comment.get('authorDisplayName'),
                        'author_channel_id': top_comment.get('authorChannelId', {}).get('value'),
                        'text': top_comment.get('textDisplay', ''),
                        'like_count': top_comment.get('likeCount', 0),
                        'published_at': self._parse_datetime(top_comment.get('publishedAt')),
                        'updated_at': self._parse_datetime(top_comment.get('updatedAt')),
                        'is_top_level': True,
                        'parent_comment_id': None,
                        'reply_count': item['snippet'].get('totalReplyCount', 0)
                    }
                    comments.append(comment_data)

                    # 대댓글도 수집 (있는 경우)
                    if 'replies' in item and len(comments) < max_results:
                        for reply in item['replies']['comments']:
                            reply_snippet = reply['snippet']
                            reply_data = {
                                'comment_id': reply['id'],
                                'author_name': reply_snippet.get('authorDisplayName'),
                                'author_channel_id': reply_snippet.get('authorChannelId', {}).get('value'),
                                'text': reply_snippet.get('textDisplay', ''),
                                'like_count': reply_snippet.get('likeCount', 0),
                                'published_at': self._parse_datetime(reply_snippet.get('publishedAt')),
                                'updated_at': self._parse_datetime(reply_snippet.get('updatedAt')),
                                'is_top_level': False,
                                'parent_comment_id': comment_data['comment_id'],
                                'reply_count': 0
                            }
                            comments.append(reply_data)

                            if len(comments) >= max_results:
                                break

                # 다음 페이지
                if 'nextPageToken' in response and len(comments) < max_results:
                    request = self.youtube.commentThreads().list_next(request, response)
                else:
                    break

            logger.info(f"Fetched {len(comments)} comments for video: {video_id}")
            return comments[:max_results]

        except HttpError as e:
            if 'commentsDisabled' in str(e):
                logger.warning(f"Comments disabled for video: {video_id}")
                return []
            logger.error(f"YouTube API error fetching comments: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting video comments: {e}")
            return []

    def get_video_captions(
        self,
        video_id: str,
        languages: List[str] = ['en', 'ko']
    ) -> List[Dict]:
        """
        영상의 자막 가져오기

        Args:
            video_id: YouTube 영상 ID
            languages: 선호하는 언어 리스트 (기본: ['en', 'ko'])

        Returns:
            자막 정보 리스트
        """
        try:
            logger.info(f"Fetching captions for video: {video_id}, languages={languages}")

            captions = []

            # 사용 가능한 자막 목록 가져오기
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            # 수동 생성 자막 우선
            for lang in languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    caption_data = transcript.fetch()

                    # 자막 텍스트 합치기
                    full_text = ' '.join([item['text'] for item in caption_data])

                    captions.append({
                        'video_id': video_id,
                        'language': transcript.language_code,
                        'caption_text': full_text,
                        'is_auto_generated': transcript.is_generated
                    })

                    logger.info(f"Found {transcript.language_code} caption (auto: {transcript.is_generated})")
                except NoTranscriptFound:
                    continue

            # 자막이 없으면 자동 생성 자막 시도
            if not captions:
                try:
                    for lang in languages:
                        try:
                            transcript = transcript_list.find_generated_transcript([lang])
                            caption_data = transcript.fetch()
                            full_text = ' '.join([item['text'] for item in caption_data])

                            captions.append({
                                'video_id': video_id,
                                'language': transcript.language_code,
                                'caption_text': full_text,
                                'is_auto_generated': True
                            })

                            logger.info(f"Found auto-generated {transcript.language_code} caption")
                        except NoTranscriptFound:
                            continue
                except Exception:
                    pass

            logger.info(f"Fetched {len(captions)} captions for video: {video_id}")
            return captions

        except TranscriptsDisabled:
            logger.warning(f"Captions disabled for video: {video_id}")
            return []
        except Exception as e:
            logger.warning(f"Error getting video captions: {e}")
            return []

    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """ISO 8601 날짜 문자열을 datetime 객체로 변환"""
        if not datetime_str:
            return None
        try:
            return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        except Exception:
            return None


# 유틸리티 함수
def format_view_count(count: int) -> str:
    """조회수 포맷팅 (예: 1,234,567)"""
    return f"{count:,}"


def estimate_api_quota_usage(num_searches: int, num_videos: int) -> int:
    """
    API 할당량 사용량 추정

    YouTube API 할당량: 10,000 units/day
    - search.list: 100 units
    - videos.list: 1 unit (per video, up to 50 per call)

    Args:
        num_searches: search 호출 횟수
        num_videos: video detail 조회 비디오 수

    Returns:
        예상 할당량 사용량
    """
    search_cost = num_searches * 100
    videos_cost = (num_videos // 50 + 1) * 1
    return search_cost + videos_cost
