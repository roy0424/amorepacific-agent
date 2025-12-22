"""
TikTok Collection Strategy for US Market
미국 시장 타겟 TikTok 수집 전략
"""

# ========================================
# Core Brand Hashtags (Priority: HIGH)
# ========================================
BRAND_HASHTAGS = [
    "laneige",
    "laneigeusa",
    "laneigeus",
    "laneigebeauty",
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
        "laneigegummybear",  # Popular flavor
        "laneigeberry",      # Popular flavor
    ],

    # Water Sleeping Mask
    "water_sleeping_mask": [
        "laneigewatersleepingmask",
        "watersleepingmask",
        "laneigesleepmask",
    ],

    # Cream Skin
    "cream_skin": [
        "laneigecreamskin",
        "creamskin",
        "laneigecreamskintoner",
    ],

    # Cushion & Makeup
    "makeup": [
        "laneigeneo",
        "laneigecushion",
        "laneigefoundation",
    ],

    # Water Bank Line
    "waterbank": [
        "laneigewaterbank",
        "waterbankhydro",
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
    "lipbalm",
    "chappedlips",

    # Sleep Beauty
    "sleepingmask",
    "overnightmask",
    "nightskincare",
]

# ========================================
# US Influencers & Beauty Gurus (Priority: HIGH)
# ========================================
US_INFLUENCERS = [
    # Major Beauty Influencers
    "jamescharles",
    "nikkietutorials",
    "jackieaina",
    "patrickstarrr",
    "bretmanrock",
    "hyram",
    "skindoctorhyram",

    # K-Beauty Specialists
    "soobeauty",
    "jella.pepper",
    "gothamista",

    # Dermatologists
    "dermdoctor",
    "drdrayzday",
]

# ========================================
# Official Accounts (Priority: HIGH)
# ========================================
OFFICIAL_ACCOUNTS = [
    "laneige_us",
    "laneige",
    "amorepacific",
    "sephora",           # Major US retailer
    "target",            # Sells Laneige
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
        "hanskin",
    ],
    "western_brands": [
        "drunk_elephant",
        "glow_recipe",
        "tatcha",
        "fresh",
        "korres",
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
    "max_videos_per_hashtag": 50,
    "min_likes": 1000,          # Viral content only
    "date_range_days": 1,
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
    "max_videos_per_hashtag": 100,
    "min_likes": 500,           # Popular content
    "date_range_days": 7,
    "priority": "MEDIUM",
}

# Monthly Collection (Market Research)
MONTHLY_CONFIG = {
    "hashtags": (
        CATEGORY_HASHTAGS +
        [f"#{comp}" for comp in COMPETITORS["korean_brands"]]
    ),
    "max_videos_per_hashtag": 200,
    "min_likes": 5000,          # Mega viral only
    "date_range_days": 30,
    "priority": "LOW",
}

# Influencer Monitoring (Weekly)
INFLUENCER_CONFIG = {
    "profiles": OFFICIAL_ACCOUNTS + US_INFLUENCERS[:10],  # Top 10
    "max_videos_per_profile": 20,
    "min_likes": 0,             # Get all their content
    "date_range_days": 7,
    "priority": "HIGH",
}

# ========================================
# Search Keywords (Apify keyword search)
# ========================================
SEARCH_KEYWORDS = [
    # Product searches
    "laneige lip sleeping mask",
    "laneige lip mask review",
    "best korean lip mask",
    "laneige water sleeping mask",
    "laneige cream skin",

    # Comparison searches
    "laneige vs drunk elephant",
    "laneige vs glow recipe",
    "best k-beauty products",

    # Tutorial/How-to
    "laneige routine",
    "how to use laneige",
    "korean skincare routine",
]

# ========================================
# Engagement Thresholds for Analysis
# ========================================
ENGAGEMENT_TIERS = {
    "mega_viral": {
        "min_likes": 100000,
        "min_views": 1000000,
    },
    "viral": {
        "min_likes": 10000,
        "min_views": 100000,
    },
    "popular": {
        "min_likes": 1000,
        "min_views": 10000,
    },
    "normal": {
        "min_likes": 100,
        "min_views": 1000,
    },
}

# ========================================
# US Market Specific Settings
# ========================================
US_MARKET_CONFIG = {
    "target_region": "US",
    "primary_language": "en",
    "timezone": "America/New_York",
    "peak_hours": [18, 19, 20, 21, 22],  # 6pm-10pm EST
    "target_demographics": {
        "age_range": "18-35",
        "gender": "F",  # Primary but not exclusive
        "interests": ["beauty", "skincare", "kbeauty"],
    },
}

# ========================================
# Budget & Cost Management
# ========================================
BUDGET_CONFIG = {
    "monthly_apify_budget": 5.00,  # Free tier
    "cost_per_1000_results": 5.00,
    "max_videos_per_month": 1000,  # Stay within free tier

    # Daily allocation
    "daily_quota": 35,  # ~1000/30 days
    "weekly_quota": 250,
    "monthly_quota": 1000,
}
