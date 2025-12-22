"""
TikTok 크롤러
Playwright를 사용한 웹 크롤링 (공식 API 없음)
"""
import asyncio
import re
import json
import random
from typing import List, Dict, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser
from loguru import logger
from src.scrapers.amazon.anti_bot import get_random_user_agent


class TikTokScraper:
    """Playwright를 사용한 TikTok 해시태그 및 영상 크롤링"""

    def __init__(self, headless: bool = True):
        """
        초기화

        Args:
            headless: 헤드리스 모드 여부
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        logger.info("TikTok scraper initialized")

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 진입"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.close()

    async def start(self):
        """브라우저 시작"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        logger.info("TikTok browser started")

    async def close(self):
        """브라우저 종료"""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("TikTok browser closed")

    async def search_hashtag(
        self,
        hashtag: str,
        max_videos: int = 30,
        scroll_count: int = 3
    ) -> List[Dict]:
        """
        해시태그로 영상 검색

        Args:
            hashtag: 해시태그 (# 제외)
            max_videos: 최대 수집 영상 수
            scroll_count: 스크롤 횟수 (더 많이 스크롤할수록 더 많은 영상)

        Returns:
            영상 정보 리스트
        """
        clean_tag = hashtag.lstrip('#')
        url = f"https://www.tiktok.com/tag/{clean_tag}"

        logger.info(f"Searching TikTok hashtag: #{clean_tag}, url={url}")

        try:
            context = await self.browser.new_context(
                user_agent=get_random_user_agent(),
                viewport={'width': 1920, 'height': 1080},
                locale='en-US',
                timezone_id='America/New_York',
                permissions=['geolocation'],
                geolocation={'latitude': 40.7128, 'longitude': -74.0060},
                color_scheme='light',
                device_scale_factor=1
            )

            page = await context.new_page()

            # 봇 감지 회피 - 더 많은 속성 위장
            await page.add_init_script("""
                // Webdriver 속성 제거
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Plugins 추가
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                // Languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });

                // Chrome runtime
                window.chrome = {
                    runtime: {}
                };

                // Permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            await page.goto(url, wait_until='networkidle', timeout=60000)
            logger.info("Page loaded, waiting for content to render...")

            # 마우스를 랜덤하게 움직여서 봇 감지 회피
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await asyncio.sleep(2)

            # 초기 대기
            await asyncio.sleep(5)

            # 스크롤하여 더 많은 영상 로드 (더 자연스럽게)
            for i in range(scroll_count):
                # 랜덤한 스크롤 거리 (더 자연스럽게)
                scroll_distance = random.randint(800, 1200)
                await page.evaluate(f'window.scrollBy(0, {scroll_distance})')

                # 랜덤 대기 시간 (2-4초)
                await asyncio.sleep(random.uniform(2.0, 4.0))
                logger.debug(f"Scrolled {i+1}/{scroll_count}")

            # 최종 렌더링 대기
            await asyncio.sleep(3)

            # 영상 데이터 추출
            videos = await self._extract_videos_from_page(page, max_videos)

            await context.close()

            logger.info(f"Found {len(videos)} TikTok videos for #{clean_tag}")
            return videos

        except Exception as e:
            logger.error(f"Error searching TikTok hashtag: {e}")
            return []

    async def _extract_videos_from_page(self, page: Page, max_videos: int) -> List[Dict]:
        """
        페이지에서 영상 정보 추출

        Args:
            page: Playwright 페이지 객체
            max_videos: 최대 수집 영상 수

        Returns:
            영상 정보 리스트
        """
        videos = []

        try:
            # 먼저 JavaScript에서 데이터 추출 시도 (가장 안정적)
            logger.info("Trying to extract data from JavaScript state...")
            js_videos = await self._extract_from_js_state(page)
            if js_videos:
                logger.info(f"Found {len(js_videos)} videos from JavaScript state")
                return js_videos[:max_videos]

            # JavaScript 추출 실패시 DOM 셀렉터 시도
            logger.info("Trying DOM selectors...")

            # 여러 셀렉터 시도 (TikTok은 자주 변경됨)
            selectors_to_try = [
                'div[data-e2e="challenge-item"]',
                'div[data-e2e="search_top-item"]',
                'div[class*="DivItemContainer"]',
                'div[class*="ItemModule"]',
                'div[class*="VideoCard"]',
            ]

            video_containers = []
            for selector in selectors_to_try:
                video_containers = await page.query_selector_all(selector)
                if video_containers:
                    logger.info(f"Found {len(video_containers)} containers with selector: {selector}")
                    break
                logger.debug(f"Selector '{selector}' found nothing, trying next...")

            # 모든 셀렉터 실패시 링크 기반 접근
            if not video_containers:
                logger.warning("All container selectors failed, trying link-based approach...")
                video_links = await page.query_selector_all('a[href*="/video/"]')
                logger.info(f"Found {len(video_links)} video links (fallback method)")

                # 링크에서 직접 비디오 데이터 추출
                for link in video_links[:max_videos]:
                    try:
                        href = await link.get_attribute('href')
                        if href and '/video/' in href:
                            video_id = self._extract_video_id(href)
                            if video_id:
                                videos.append({
                                    'video_id': video_id,
                                    'video_url': href if href.startswith('http') else f"https://www.tiktok.com{href}",
                                    'author_username': '',
                                    'description': '',
                                    'hashtags': None,
                                    'thumbnail_url': None,
                                    'view_count': 0,
                                    'like_count': 0,
                                    'comment_count': 0,
                                    'share_count': 0,
                                })
                    except Exception as e:
                        logger.debug(f"Error parsing link: {e}")
                        continue

                return videos

            # 컨테이너에서 데이터 파싱
            for container in video_containers[:max_videos]:
                try:
                    video_data = await self._parse_video_container(page, container)
                    if video_data:
                        videos.append(video_data)
                except Exception as e:
                    logger.warning(f"Error parsing video container: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting videos from page: {e}")

        return videos

    async def _extract_from_js_state(self, page: Page) -> List[Dict]:
        """
        페이지의 JavaScript 상태에서 비디오 데이터 추출
        TikTok은 __UNIVERSAL_DATA_FOR_REHYDRATION__ 또는 SIGI_STATE에 데이터를 저장

        Args:
            page: Playwright 페이지

        Returns:
            비디오 데이터 리스트
        """
        try:
            # TikTok의 주요 데이터 저장소 확인
            js_data = await page.evaluate("""
                () => {
                    // Try __UNIVERSAL_DATA_FOR_REHYDRATION__
                    if (window.__UNIVERSAL_DATA_FOR_REHYDRATION__) {
                        return JSON.stringify(window.__UNIVERSAL_DATA_FOR_REHYDRATION__);
                    }
                    // Try SIGI_STATE
                    if (window.SIGI_STATE) {
                        return JSON.stringify(window.SIGI_STATE);
                    }
                    // Try finding script tags with data
                    const scripts = document.querySelectorAll('script');
                    for (const script of scripts) {
                        const text = script.textContent;
                        if (text && text.includes('ItemModule')) {
                            return text;
                        }
                    }
                    return null;
                }
            """)

            if not js_data:
                return []

            # JSON 파싱
            import json
            try:
                data = json.loads(js_data)
            except json.JSONDecodeError:
                # script 태그 내용일 수 있음
                logger.debug("JavaScript data is not pure JSON, trying to extract...")
                return []

            # 데이터 구조 탐색 (TikTok의 구조에 따라 조정 필요)
            videos = []

            # __UNIVERSAL_DATA_FOR_REHYDRATION__ 구조
            if '__DEFAULT_SCOPE__' in data:
                default_scope = data.get('__DEFAULT_SCOPE__', {})
                item_module = default_scope.get('ItemModule', {})

                for video_id, video_data in item_module.items():
                    try:
                        parsed = self._parse_js_video_data(video_data)
                        if parsed:
                            videos.append(parsed)
                    except Exception as e:
                        logger.debug(f"Error parsing video from JS: {e}")
                        continue

            # SIGI_STATE 구조
            elif 'ItemModule' in data:
                item_module = data.get('ItemModule', {})
                for video_id, video_data in item_module.items():
                    try:
                        parsed = self._parse_js_video_data(video_data)
                        if parsed:
                            videos.append(parsed)
                    except Exception as e:
                        logger.debug(f"Error parsing video from JS: {e}")
                        continue

            return videos

        except Exception as e:
            logger.debug(f"Error extracting from JavaScript state: {e}")
            return []

    def _parse_js_video_data(self, video_data: Dict) -> Optional[Dict]:
        """
        JavaScript 상태에서 추출한 비디오 데이터 파싱

        Args:
            video_data: JavaScript에서 추출한 비디오 데이터

        Returns:
            파싱된 비디오 데이터
        """
        try:
            video_id = video_data.get('id', '')
            if not video_id:
                return None

            author = video_data.get('author', {})
            author_username = author.get('uniqueId', '') if isinstance(author, dict) else ''

            desc = video_data.get('desc', '')

            # 해시태그 추출
            hashtags = []
            challenges = video_data.get('challenges', [])
            if challenges:
                hashtags = [c.get('title', '') for c in challenges if isinstance(c, dict)]
            else:
                # desc에서 추출
                hashtags = self._extract_hashtags(desc)

            stats = video_data.get('stats', {})

            return {
                'video_id': str(video_id),
                'video_url': f"https://www.tiktok.com/@{author_username}/video/{video_id}",
                'author_username': author_username,
                'description': desc,
                'hashtags': ','.join(hashtags) if hashtags else None,
                'thumbnail_url': video_data.get('video', {}).get('cover', '') if isinstance(video_data.get('video'), dict) else None,
                'view_count': stats.get('playCount', 0) if isinstance(stats, dict) else 0,
                'like_count': stats.get('diggCount', 0) if isinstance(stats, dict) else 0,
                'comment_count': stats.get('commentCount', 0) if isinstance(stats, dict) else 0,
                'share_count': stats.get('shareCount', 0) if isinstance(stats, dict) else 0,
            }

        except Exception as e:
            logger.debug(f"Error parsing JS video data: {e}")
            return None

    async def _parse_video_container(self, page: Page, container) -> Optional[Dict]:
        """
        영상 컨테이너에서 데이터 파싱

        Args:
            page: Playwright 페이지
            container: 영상 컨테이너 요소

        Returns:
            파싱된 영상 데이터
        """
        try:
            # 링크 추출 (여러 셀렉터 시도)
            link_element = await container.query_selector('a[href*="/video/"]')
            if not link_element:
                link_element = await container.query_selector('a')
            if not link_element:
                logger.debug("No link element found in container")
                return None

            video_url = await link_element.get_attribute('href')
            if not video_url or '/video/' not in video_url:
                logger.debug(f"Invalid video URL: {video_url}")
                return None

            # 전체 URL 생성
            if video_url.startswith('/'):
                video_url = f"https://www.tiktok.com{video_url}"

            # video_id 추출 (URL에서)
            video_id = self._extract_video_id(video_url)
            if not video_id:
                logger.debug(f"Could not extract video ID from: {video_url}")
                return None

            # 설명/캡션 추출 (여러 방법 시도)
            description = ""
            desc_selectors = [
                'div[data-e2e="challenge-item-desc"]',
                'div[data-e2e*="desc"]',
                'div[class*="desc"]'
            ]
            for selector in desc_selectors:
                desc_element = await container.query_selector(selector)
                if desc_element:
                    description = await desc_element.inner_text()
                    break

            # 작성자 추출
            author_username = ""
            author_selectors = [
                'a[data-e2e="challenge-item-username"]',
                'a[href^="/@"]',
                'span[data-e2e*="username"]'
            ]
            for selector in author_selectors:
                author_element = await container.query_selector(selector)
                if author_element:
                    author_username = await author_element.inner_text()
                    break

            # 썸네일 추출
            img_element = await container.query_selector('img')
            thumbnail_url = await img_element.get_attribute('src') if img_element else None

            # 해시태그 추출
            hashtags = self._extract_hashtags(description)

            # 메트릭 추출 시도 (항상 성공하지는 않음)
            metrics = await self._try_extract_metrics(container)

            video_data = {
                'video_id': video_id,
                'video_url': video_url,
                'author_username': author_username.lstrip('@').strip(),
                'description': description.strip(),
                'hashtags': ','.join(hashtags) if hashtags else None,
                'thumbnail_url': thumbnail_url,
                'view_count': metrics.get('views', 0),
                'like_count': metrics.get('likes', 0),
                'comment_count': metrics.get('comments', 0),
                'share_count': metrics.get('shares', 0),
            }

            logger.debug(f"Parsed video: {video_id} by @{video_data['author_username']}")
            return video_data

        except Exception as e:
            logger.warning(f"Error parsing video container: {e}")
            return None

    async def _try_extract_metrics(self, container) -> Dict:
        """
        메트릭 추출 시도 (항상 성공하지는 않음)

        Args:
            container: 영상 컨테이너

        Returns:
            메트릭 딕셔너리
        """
        metrics = {
            'views': 0,
            'likes': 0,
            'comments': 0,
            'shares': 0
        }

        try:
            # 메트릭 요소들 찾기 (TikTok UI 구조에 따라 다를 수 있음)
            metric_elements = await container.query_selector_all('strong[data-e2e*="count"]')

            for elem in metric_elements:
                text = await elem.inner_text()
                # 숫자 파싱 (예: "1.2M" -> 1200000)
                value = self._parse_count(text)

                # data-e2e 속성으로 메트릭 종류 구분
                attr = await elem.get_attribute('data-e2e')
                if 'like' in attr.lower():
                    metrics['likes'] = value
                elif 'comment' in attr.lower():
                    metrics['comments'] = value
                elif 'share' in attr.lower():
                    metrics['shares'] = value

        except Exception as e:
            logger.debug(f"Could not extract metrics: {e}")

        return metrics

    def _extract_video_id(self, url: str) -> str:
        """
        URL에서 video_id 추출

        Args:
            url: TikTok 영상 URL

        Returns:
            video_id
        """
        # 예: https://www.tiktok.com/@user/video/1234567890123456789
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)

        # URL 자체를 ID로 사용 (fallback)
        return url.split('/')[-1] or url

    def _extract_hashtags(self, text: str) -> List[str]:
        """
        텍스트에서 해시태그 추출

        Args:
            text: 설명 텍스트

        Returns:
            해시태그 리스트 (# 제외)
        """
        if not text:
            return []

        # #hashtag 패턴 찾기
        hashtags = re.findall(r'#(\w+)', text)
        return hashtags

    def _parse_count(self, text: str) -> int:
        """
        카운트 텍스트 파싱 (예: "1.2M" -> 1200000)

        Args:
            text: 카운트 텍스트

        Returns:
            정수 값
        """
        if not text:
            return 0

        text = text.strip().upper()

        # 숫자와 단위 분리
        match = re.match(r'([\d.]+)([KMB]?)', text)
        if not match:
            return 0

        number = float(match.group(1))
        unit = match.group(2)

        multipliers = {
            'K': 1_000,
            'M': 1_000_000,
            'B': 1_000_000_000,
        }

        return int(number * multipliers.get(unit, 1))


# 유틸리티 함수
async def search_tiktok_hashtag(hashtag: str, max_videos: int = 30) -> List[Dict]:
    """
    해시태그 검색 헬퍼 함수

    Args:
        hashtag: 해시태그
        max_videos: 최대 영상 수

    Returns:
        영상 리스트
    """
    async with TikTokScraper(headless=True) as scraper:
        return await scraper.search_hashtag(hashtag, max_videos=max_videos)
