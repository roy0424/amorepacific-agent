"""
Instagram Collection Strategy for US Market
미국 시장 타겟 Instagram 수집 전략
"""

# ========================================
# Core Brand Hashtags (Priority: HIGH)
# ========================================
BRAND_HASHTAGS = [
    "laneige",
    "laneigeusa",
    "laneigebeauty",
    "laneigeus",
]

# ========================================
# Product-Specific Hashtags (Priority: HIGH)
# ========================================
PRODUCT_HASHTAGS = {
    # Lip Sleeping Mask (Best-seller in US)
    "lip_sleeping_mask": [
        "laneigelipsleepingmask",
        "lipsleepingmask",
        "laneigelipmask",
        "laneigegummybear",
        "laneigeberry",
    ],

    # Water Sleeping Mask
    "water_sleeping_mask": [
        "laneigewatersleepingmask",
        "watersleepingmask",
    ],

    # Cream Skin
    "cream_skin": [
        "laneigecreamskin",
        "creamskin",
    ],

    # Makeup
    "makeup": [
        "laneigeneo",
        "laneigecushion",
        "laneigefoundation",
    ],
}

# ========================================
# Category Hashtags (Priority: MEDIUM)
# ========================================
CATEGORY_HASHTAGS = [
    # K-Beauty
    "kbeauty",
    "koreanbeauty",
    "koreanskincare",
    "kskincare",

    # Skincare General
    "skincare",
    "skincareproducts",
    "skincareroutine",
    "glowyskin",

    # Lip Care
    "lipcare",
    "liptreatment",
    "chapstick",

    # Sleep Beauty
    "sleepingmask",
    "overnightmask",
    "nightskincare",
]

# ========================================
# US Influencers & Beauty Accounts (Priority: HIGH)
# ========================================
US_INFLUENCERS = [
    # Official & Retailers
    "laneige_us",
    "sephora",
    "target",
    "ulta",

    # Mega Influencers (10M+)
    "jamescharles",
    "nikkietutorials",
    "hudabeauty",

    # Beauty Influencers (1M+)
    "jackieaina",
    "patrickstarrr",
    "bretmanrock",
    "makeupbyjakejamie",

    # Skincare Experts
    "hyram",
    "skincarebyhyram",
    "labeautyologist",
    "fiftyshadeofsnail",

    # K-Beauty Specialists
    "soobeauty",
    "jella.pepper",
    "glowrecipe",
]

# ========================================
# Official Accounts (Priority: HIGH)
# ========================================
OFFICIAL_ACCOUNTS = [
    "laneige_us",
    "laneige_kr",
    "amorepacific",
]

# ========================================
# Competitor Brands (Priority: LOW)
# ========================================
COMPETITORS = {
    "korean_brands": [
        "sulwhasoo",
        "innisfree",
        "cosrx",
        "klairs",
        "etudehouse",
    ],
    "western_brands": [
        "drunkelephant",
        "glowrecipe",
        "tatcha",
        "fresh",
    ],
}

# ========================================
# Collection Configurations
# ========================================

# Daily Collection (Trend Monitoring)
DAILY_CONFIG = {
    "hashtags": BRAND_HASHTAGS + [
        "laneigelipsleepingmask",
        "laneigecreamskin",
    ],
    "max_posts_per_hashtag": 30,
    "priority": "HIGH",
}

# Weekly Collection (Detailed Analysis)
WEEKLY_CONFIG = {
    "hashtags": (
        BRAND_HASHTAGS +
        PRODUCT_HASHTAGS["lip_sleeping_mask"] +
        PRODUCT_HASHTAGS["cream_skin"] +
        ["kbeauty", "koreanbeauty", "skincare"]
    ),
    "max_posts_per_hashtag": 50,
    "priority": "MEDIUM",
}

# Monthly Collection (Market Research)
MONTHLY_CONFIG = {
    "hashtags": (
        CATEGORY_HASHTAGS +
        [comp for comp in COMPETITORS["korean_brands"]]
    ),
    "max_posts_per_hashtag": 100,
    "priority": "LOW",
}

# Influencer Monitoring (Weekly)
INFLUENCER_CONFIG = {
    "profiles": OFFICIAL_ACCOUNTS + US_INFLUENCERS[:15],  # Top 15
    "max_posts_per_profile": 10,
    "priority": "HIGH",
}

# ========================================
# US Market Specific Settings
# ========================================
US_MARKET_CONFIG = {
    "target_region": "US",
    "primary_language": "en",
    "timezone": "America/New_York",
    "target_demographics": {
        "age_range": "18-35",
        "gender": "F",
        "interests": ["beauty", "skincare", "kbeauty"],
    },
}

# ========================================
# Budget & Cost Management
# ========================================
BUDGET_CONFIG = {
    "monthly_apify_budget": 5.00,  # Shared with TikTok
    "cost_per_1000_posts": 2.70,  # Instagram is cheaper than TikTok
    "max_posts_per_month": 500,   # Leave room for TikTok

    # Daily allocation
    "daily_quota": 20,   # ~500/25 days
    "weekly_quota": 150,
    "monthly_quota": 500,
}

# ========================================
# Instagram-Specific Features
# ========================================
INSTAGRAM_FEATURES = {
    # Content types to focus on
    "content_types": ["photo", "carousel", "reel"],

    # Engagement metrics
    "min_engagement_rate": 0.02,  # 2% minimum

    # Post types to prioritize
    "prioritize_types": ["reel", "carousel"],  # Reels get more reach

    # Best posting times (EST)
    "peak_hours": [11, 13, 15, 19, 21],  # 11am, 1pm, 3pm, 7pm, 9pm
}
