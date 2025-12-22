"""
Models package
"""
from .brands import Brand
from .amazon import AmazonCategory, AmazonProduct, AmazonRanking, ScheduleLog
from .social_media import (
    TikTokPost, TikTokMetric,
    YouTubeVideo, YouTubeMetric, YouTubeComment, YouTubeCaption,
    InstagramPost, InstagramMetric
)
from .events import (
    RankingEvent,
    EventContextSocial,
    EventContextReview,
    EventContextCompetitor,
    EventInsight
)
from .scenario import (
    ScenarioCategory,
    ScenarioProduct,
    ScenarioRanking,
    ScenarioRankingEvent
)
from .prompt_templates import PromptTemplate

__all__ = [
    "Brand",
    "AmazonCategory",
    "AmazonProduct",
    "AmazonRanking",
    "ScheduleLog",
    "TikTokPost",
    "TikTokMetric",
    "YouTubeVideo",
    "YouTubeMetric",
    "YouTubeComment",
    "YouTubeCaption",
    "InstagramPost",
    "InstagramMetric",
    "RankingEvent",
    "EventContextSocial",
    "EventContextReview",
    "EventContextCompetitor",
    "EventInsight",
    "ScenarioCategory",
    "ScenarioProduct",
    "ScenarioRanking",
    "ScenarioRankingEvent",
    "PromptTemplate"
]
