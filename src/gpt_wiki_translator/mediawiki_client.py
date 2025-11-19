from __future__ import annotations
import re
import requests
from typing import Any
from .config import get_settings
from .logging_utils import get_logger

logger = get_logger()

class MediaWikiClient:
    def __init__(self, endpoint: str, verify_ssl: bool = True):
        self.settings = get_settings()
        if not endpoint:
            raise ValueError('MediaWiki endpoint is required')
        self.endpoint = endpoint
        self.session = requests.Session()
        self.verify_ssl = verify_ssl
        self._csrf_token: str | None = None
        
        # Disable SSL warnings if verification is disabled
        if not verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            logger.info('SSL verification disabled for %s', endpoint)
        
        # Login if credentials provided
        if self.settings.mediawiki_username and self.settings.mediawiki_password:
            try:
                self.login(self.settings.mediawiki_username, self.settings.mediawiki_password)
            except Exception as e:
                logger.warning('Login failed on %s: %s', endpoint, e)

    def _get_token(self) -> str:
        if self._csrf_token:
            return self._csrf_token
        params = {
            'action': 'query',
            'meta': 'tokens',
            'format': 'json'
        }
        r = self.session.get(self.endpoint, params=params, timeout=30, verify=self.verify_ssl)
        r.raise_for_status()
        data = r.json()
        token = data['query']['tokens']['csrftoken']
        self._csrf_token = token
        return token

    def login(self, username: str, password: str) -> None:
        # Obtain login token
        r = self.session.get(self.endpoint, params={
            'action': 'query', 'meta': 'tokens', 'type': 'login', 'format': 'json'
        }, timeout=30, verify=self.verify_ssl)
        r.raise_for_status()
        login_token = r.json()['query']['tokens']['logintoken']
        # Legacy action=login
        r2 = self.session.post(self.endpoint, data={
            'action': 'login', 'lgname': username, 'lgpassword': password,
            'lgtoken': login_token, 'format': 'json'
        }, timeout=30, verify=self.verify_ssl)
        r2.raise_for_status()
        data = r2.json()
        if data.get('login', {}).get('result') != 'Success':
            raise RuntimeError(f"Login failed: {data}")

    def fetch_page_wikitext(self, title: str) -> str | None:
        params = {
            'action': 'query',
            'prop': 'revisions',
            'rvslots': 'main',
            'rvprop': 'content',
            'titles': title,
            'format': 'json'
        }
        r = self.session.get(self.endpoint, params=params, timeout=30, verify=self.verify_ssl)
        r.raise_for_status()
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for page in pages.values():
            if 'revisions' in page:
                return page['revisions'][0]['slots']['main']['*']
        return None

    def page_exists(self, title: str) -> bool:
        """Check if a page exists."""
        params = {
            'action': 'query',
            'titles': title,
            'format': 'json'
        }
        r = self.session.get(self.endpoint, params=params, timeout=30, verify=self.verify_ssl)
        r.raise_for_status()
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            # If page_id is negative, the page doesn't exist
            return int(page_id) > 0
        return False

    def is_redirect(self, title: str) -> bool:
        """Check if a page is a redirect."""
        params = {
            'action': 'query',
            'titles': title,
            'format': 'json'
        }
        r = self.session.get(self.endpoint, params=params, timeout=30, verify=self.verify_ssl)
        r.raise_for_status()
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for page in pages.values():
            return 'redirect' in page
        return False

    def resolve_redirect(self, title: str) -> str | None:
        """Resolve a redirect to its final target page.
        
        Returns:
            - Final target page title if redirect exists and target exists
            - Original title if not a redirect and page exists
            - None if page doesn't exist (or redirect target doesn't exist)
        """
        params = {
            'action': 'query',
            'titles': title,
            'redirects': '1',
            'format': 'json'
        }
        r = self.session.get(self.endpoint, params=params, timeout=30, verify=self.verify_ssl)
        r.raise_for_status()
        data = r.json()
        
        # Check if page exists by looking at the pages dict
        pages = data.get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            # If page has 'missing' key or negative ID, page doesn't exist
            if 'missing' in page or int(page_id) < 0:
                return None
            # Page exists, check if there was a redirect
            redirects = data.get('query', {}).get('redirects', [])
            if redirects:
                # Return the final target (last in chain)
                return redirects[-1]['to']
            # No redirect, return original title
            return title
        
        return None

    def get_langlinks(self, title: str) -> dict[str, str]:
        langlinks: dict[str, str] = {}
        continue_params = {}
        
        while True:
            params = {
                'action': 'query',
                'titles': title,
                'prop': 'langlinks',
                'lllimit': '500',
                'format': 'json'
            }
            # Add continuation parameters from previous response
            params.update(continue_params)
            
            r = self.session.get(self.endpoint, params=params, timeout=30, verify=self.verify_ssl)
            r.raise_for_status()
            data = r.json()
            pages = data.get('query', {}).get('pages', {})
            for page in pages.values():
                for ll in page.get('langlinks', []) or []:
                    langlinks[ll['lang']] = ll['*']
            
            # Get entire continue structure for next request
            continue_params = data.get('continue', {})
            if not continue_params:
                break
                
        return langlinks

    def create_or_update_page(self, title: str, wikitext: str, summary: str = 'Automated translation') -> dict[str, Any]:
        token = self._get_token()
        data = {
            'action': 'edit',
            'title': title,
            'text': wikitext,
            'format': 'json',
            'minor': '1',
            'token': token,
            'summary': summary,
            'watchlist': 'nochange'
        }
        r = self.session.post(self.endpoint, data=data, timeout=30, verify=self.verify_ssl)
        r.raise_for_status()
        return r.json()

    def create_or_update_json_page(self, title: str, json_text: str, summary: str = 'Automated JSON translation') -> dict[str, Any]:
        """Create or update a JSON content page. Uses appropriate content model if supported."""
        token = self._get_token()
        data = {
            'action': 'edit',
            'title': title,
            'text': json_text,
            'format': 'json',
            'contentmodel': 'json',
            'minor': '1',
            'contentformat': 'application/json',
            'token': token,
            'summary': summary,
            'watchlist': 'nochange'
        }
        r = self.session.post(self.endpoint, data=data, timeout=30, verify=self.verify_ssl)
        r.raise_for_status()
        return r.json()

    def add_or_update_interwiki_link(self, title: str, interwiki_marker: str, summary: str = 'Add interwiki link') -> dict[str, Any]:
        # Fetch current
        content = self.fetch_page_wikitext(title) or ''
        # If exact marker already present, skip
        if interwiki_marker in content:
            return {'skip': True, 'reason': 'already present'}

        # Try to detect the language from the marker and replace any existing link for that language
        # Accept both forms [[en:Page]] and [[:en:Page]]
        m = re.match(r"\[\[:?([a-zA-Z-]+):([^\]]+)\]\]", interwiki_marker)
        if m:
            lang = m.group(1)
            # Pattern to find any existing interwiki link for the same language
            pattern = re.compile(rf"\[\[:?{re.escape(lang)}:[^\]]+\]\]")
            if pattern.search(content):
                new_content = pattern.sub(interwiki_marker, content, count=1)
                return self.create_or_update_page(title, new_content, summary=summary)

        # Otherwise, append at the end
        sep = "\n" if not content.endswith("\n") else ""
        new_content = content + f"{sep}{interwiki_marker}\n"
        return self.create_or_update_page(title, new_content, summary=summary)
