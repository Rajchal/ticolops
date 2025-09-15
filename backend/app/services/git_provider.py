"""Small Git provider adapter with a mock GitHub connector for demos."""

from typing import Dict, Optional
import os
import logging

logger = logging.getLogger(__name__)


def get_repo_info_mock(url: str) -> Dict[str, Optional[str]]:
    """Return a mock repository metadata object based on the URL."""
    # Very small heuristic parsing of a GitHub-style URL
    repo_name = url.rsplit('/', 2)[-2:] if url else [None]
    owner = repo_name[0] if len(repo_name) >= 2 else None
    name = repo_name[-1] if repo_name else None
    return {
        "provider": "github",
        "owner": owner,
        "name": name,
        "url": url,
        "default_branch": "main",
        "description": "Demo repository (mock)",
        "stars": 0,
        "forks": 0,
    }


def get_repo_info(url: str) -> Dict[str, Optional[str]]:
    """Public function to get repository information. Uses mock unless
    a real GITHUB_TOKEN is provided in the environment, in which case
    a real GitHub call could be implemented. For local demos we keep the
    mock to avoid external network dependency.
    """
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        return get_repo_info_mock(url)

    # If token is present, attempt a simple GitHub API call (best-effort).
    # We intentionally avoid adding 'requests' to dependencies for now.
    try:
        import http.client
        import json
        # Very naive parsing; support only github.com URLs
        if 'github.com' not in url:
            return get_repo_info_mock(url)
        parts = url.rstrip('/').split('/')
        owner, name = parts[-2], parts[-1]
        conn = http.client.HTTPSConnection('api.github.com')
        headers = {
            'User-Agent': 'ticolops-demo',
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        conn.request('GET', f'/repos/{owner}/{name}', headers=headers)
        resp = conn.getresponse()
        data = resp.read().decode()
        if resp.status != 200:
            logger.warning('GitHub API responded %s: %s', resp.status, data[:200])
            return get_repo_info_mock(url)
        j = json.loads(data)
        return {
            'provider': 'github',
            'owner': owner,
            'name': name,
            'url': j.get('html_url'),
            'default_branch': j.get('default_branch'),
            'description': j.get('description'),
            'stars': j.get('stargazers_count'),
            'forks': j.get('forks_count')
        }
    except Exception:
        logger.exception('Failed to fetch real GitHub repo info, falling back to mock')
        return get_repo_info_mock(url)
