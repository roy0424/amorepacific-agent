"""
소셜미디어 데이터 모델
TikTok, YouTube, Instagram 포스트 및 메트릭
"""
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, Text, Index, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.core.database import Base


# ===========================
# TikTok 모델
# ===========================

class TikTokPost(Base):
    """TikTok 포스트 마스터 테이블"""
    __tablename__ = "tiktok_posts"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(100), unique=True, nullable=False, index=True)  # TikTok 고유 ID
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    author_username = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)  # JSON string으로 저장
    video_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)  # 실제 게시 시간
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_collected_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    brand = relationship("Brand", backref="tiktok_posts")
    metrics = relationship("TikTokMetric", back_populates="post")

    def __repr__(self):
        return f"<TikTokPost(video_id='{self.video_id}', author='{self.author_username}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "brand_id": self.brand_id,
            "author_username": self.author_username,
            "description": self.description,
            "hashtags": self.hashtags,
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_collected_at": self.last_collected_at.isoformat() if self.last_collected_at else None,
            "is_active": self.is_active
        }


class TikTokMetric(Base):
    """TikTok 메트릭 히스토리 테이블 (시계열 데이터)"""
    __tablename__ = "tiktok_metrics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("tiktok_posts.id"), nullable=False, index=True)
    view_count = Column(BigInteger, nullable=True)
    like_count = Column(BigInteger, nullable=True)
    comment_count = Column(Integer, nullable=True)
    share_count = Column(Integer, nullable=True)
    play_count = Column(BigInteger, nullable=True)  # 재생 수
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # 관계
    post = relationship("TikTokPost", back_populates="metrics")

    # 복합 인덱스
    __table_args__ = (
        Index('ix_tiktok_post_time', 'post_id', 'collected_at'),
    )

    def __repr__(self):
        return f"<TikTokMetric(post_id={self.post_id}, views={self.view_count})>"

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "share_count": self.share_count,
            "play_count": self.play_count,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None
        }


# ===========================
# YouTube 모델
# ===========================

class YouTubeVideo(Base):
    """YouTube 영상 마스터 테이블"""
    __tablename__ = "youtube_videos"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(50), unique=True, nullable=False, index=True)  # YouTube 영상 ID
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    channel_id = Column(String(100), nullable=True)
    channel_title = Column(String(200), nullable=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)  # JSON string으로 저장
    video_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)  # 실제 발행 시간
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_collected_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    brand = relationship("Brand", backref="youtube_videos")
    metrics = relationship("YouTubeMetric", back_populates="video")

    def __repr__(self):
        return f"<YouTubeVideo(video_id='{self.video_id}', title='{self.title[:50]}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "brand_id": self.brand_id,
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "duration_seconds": self.duration_seconds,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_collected_at": self.last_collected_at.isoformat() if self.last_collected_at else None,
            "is_active": self.is_active
        }


class YouTubeMetric(Base):
    """YouTube 메트릭 히스토리 테이블 (시계열 데이터)"""
    __tablename__ = "youtube_metrics"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("youtube_videos.id"), nullable=False, index=True)
    view_count = Column(BigInteger, nullable=True)
    like_count = Column(BigInteger, nullable=True)
    comment_count = Column(Integer, nullable=True)
    favorite_count = Column(Integer, nullable=True)  # YouTube API 제공
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # 관계
    video = relationship("YouTubeVideo", back_populates="metrics")

    # 복합 인덱스
    __table_args__ = (
        Index('ix_youtube_video_time', 'video_id', 'collected_at'),
    )

    def __repr__(self):
        return f"<YouTubeMetric(video_id={self.video_id}, views={self.view_count})>"

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "view_count": self.view_count,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "favorite_count": self.favorite_count,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None
        }


class YouTubeComment(Base):
    """YouTube 댓글 테이블"""
    __tablename__ = "youtube_comments"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("youtube_videos.id"), nullable=False, index=True)
    comment_id = Column(String(100), unique=True, nullable=False, index=True)  # YouTube 댓글 ID
    author_name = Column(String(200), nullable=True)
    author_channel_id = Column(String(100), nullable=True)
    text = Column(Text, nullable=False)  # 댓글 내용
    like_count = Column(Integer, nullable=True)
    reply_count = Column(Integer, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    is_top_level = Column(Boolean, default=True)  # 대댓글 구분
    parent_comment_id = Column(String(100), nullable=True)  # 대댓글인 경우 원댓글 ID
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    video = relationship("YouTubeVideo", backref="comments")

    # 인덱스
    __table_args__ = (
        Index('ix_youtube_comment_video', 'video_id', 'published_at'),
    )

    def __repr__(self):
        return f"<YouTubeComment(comment_id='{self.comment_id}', author='{self.author_name}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "comment_id": self.comment_id,
            "author_name": self.author_name,
            "text": self.text,
            "like_count": self.like_count,
            "reply_count": self.reply_count,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "is_top_level": self.is_top_level
        }


class YouTubeCaption(Base):
    """YouTube 자막 테이블"""
    __tablename__ = "youtube_captions"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("youtube_videos.id"), nullable=False, index=True)
    language = Column(String(10), nullable=False)  # 'en', 'ko' 등
    caption_text = Column(Text, nullable=False)  # 전체 자막 텍스트
    is_auto_generated = Column(Boolean, default=False)  # 자동 생성 자막 여부
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    video = relationship("YouTubeVideo", backref="captions")

    # 인덱스
    __table_args__ = (
        Index('ix_youtube_caption_video_lang', 'video_id', 'language'),
    )

    def __repr__(self):
        return f"<YouTubeCaption(video_id={self.video_id}, language='{self.language}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "language": self.language,
            "caption_text": self.caption_text[:200] + "..." if len(self.caption_text) > 200 else self.caption_text,
            "is_auto_generated": self.is_auto_generated,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None
        }


# ===========================
# Instagram 모델
# ===========================

class InstagramPost(Base):
    """Instagram 포스트 마스터 테이블"""
    __tablename__ = "instagram_posts"

    id = Column(Integer, primary_key=True, index=True)
    shortcode = Column(String(50), unique=True, nullable=False, index=True)  # Instagram 고유 ID
    brand_id = Column(Integer, ForeignKey("brands.id"), nullable=True)
    owner_username = Column(String(100), nullable=True)
    owner_id = Column(String(100), nullable=True)
    caption = Column(Text, nullable=True)
    hashtags = Column(Text, nullable=True)  # JSON string으로 저장
    post_url = Column(Text, nullable=True)
    media_type = Column(String(20), nullable=True)  # 'photo', 'video', 'carousel'
    media_url = Column(Text, nullable=True)
    posted_at = Column(DateTime(timezone=True), nullable=True)  # 실제 게시 시간
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_collected_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 관계
    brand = relationship("Brand", backref="instagram_posts")
    metrics = relationship("InstagramMetric", back_populates="post")

    def __repr__(self):
        return f"<InstagramPost(shortcode='{self.shortcode}', owner='{self.owner_username}')>"

    def to_dict(self):
        return {
            "id": self.id,
            "shortcode": self.shortcode,
            "brand_id": self.brand_id,
            "owner_username": self.owner_username,
            "owner_id": self.owner_id,
            "caption": self.caption,
            "hashtags": self.hashtags,
            "post_url": self.post_url,
            "media_type": self.media_type,
            "media_url": self.media_url,
            "posted_at": self.posted_at.isoformat() if self.posted_at else None,
            "first_seen_at": self.first_seen_at.isoformat() if self.first_seen_at else None,
            "last_collected_at": self.last_collected_at.isoformat() if self.last_collected_at else None,
            "is_active": self.is_active
        }


class InstagramMetric(Base):
    """Instagram 메트릭 히스토리 테이블 (시계열 데이터)"""
    __tablename__ = "instagram_metrics"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("instagram_posts.id"), nullable=False, index=True)
    like_count = Column(BigInteger, nullable=True)
    comment_count = Column(Integer, nullable=True)
    video_view_count = Column(BigInteger, nullable=True)  # 동영상인 경우
    collected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # 관계
    post = relationship("InstagramPost", back_populates="metrics")

    # 복합 인덱스
    __table_args__ = (
        Index('ix_instagram_post_time', 'post_id', 'collected_at'),
    )

    def __repr__(self):
        return f"<InstagramMetric(post_id={self.post_id}, likes={self.like_count})>"

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "like_count": self.like_count,
            "comment_count": self.comment_count,
            "video_view_count": self.video_view_count,
            "collected_at": self.collected_at.isoformat() if self.collected_at else None
        }