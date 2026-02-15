"""
Update checker for Helldivers Numpad Macros
Checks GitHub releases for updates
"""

import json
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from packaging import version as version_parser


def extract_version(tag_or_version):
    """
    Extract semantic version from a tag string.
    Examples:
        "v1.0.0" -> "1.0.0"
        "beta0.1.6" -> "0.1.6"
        "v0.1.6-beta" -> "0.1.6"
        "release-1.2.3" -> "1.2.3"
    """
    # Match semantic version pattern (X.Y.Z with optional pre-release info)
    match = re.search(r'(\d+\.\d+\.\d+)', tag_or_version)
    if match:
        return match.group(1)
    return tag_or_version.lstrip('v')


def compare_versions(current, latest):
    """
    Compare two version strings
    Returns: 1 if latest > current, 0 if equal, -1 if current > latest
    """
    try:
        current_v = version_parser.parse(current)
        latest_v = version_parser.parse(latest)
        
        if latest_v > current_v:
            return 1
        elif latest_v == current_v:
            return 0
        else:
            return -1
    except:
        # Fallback to string comparison if parsing fails
        if latest > current:
            return 1
        elif latest == current:
            return 0
        else:
            return -1


def check_for_updates(current_version, repo_owner, repo_name, timeout=5):
    """
    Check GitHub for the latest release
    
    Args:
        current_version: Current app version (e.g., "1.0.0")
        repo_owner: GitHub repository owner
        repo_name: GitHub repository name
        timeout: Request timeout in seconds
    
    Returns:
        dict with keys:
            - success: bool
            - has_update: bool (only if success=True)
            - latest_version: str (only if success=True)
            - download_url: str (only if success=True)
            - release_url: str (only if success=True)
            - release_notes: str (only if success=True)
            - error: str (only if success=False)
    """
    api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
    
    try:
        # Create request with user agent (required by GitHub API)
        request = Request(api_url, headers={'User-Agent': 'HelldiversMacro-UpdateChecker'})
        
        # Fetch latest release info
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode())
        
        # Extract version from tag (handle various formats like v0.1.6, beta0.1.6, etc.)
        tag_name = data.get('tag_name', '')
        latest_version = extract_version(tag_name)
        
        # Get release info
        release_notes = data.get('body', 'No release notes available.')
        release_url = data.get('html_url', '')
        
        # Find installer asset (prefer setup executable)
        download_url = None
        assets = data.get('assets', [])
        
        # Look for setup executable first
        for asset in assets:
            name = asset.get('name', '').lower()
            if 'setup' in name and name.endswith('.exe'):
                download_url = asset.get('browser_download_url')
                break
        
        # Fallback to any .exe file
        if not download_url:
            for asset in assets:
                name = asset.get('name', '').lower()
                if name.endswith('.exe'):
                    download_url = asset.get('browser_download_url')
                    break
        
        # If no assets, use release page
        if not download_url:
            download_url = release_url
        
        # Compare versions (extract numeric parts from both)
        current_numeric = extract_version(current_version)
        latest_numeric = extract_version(tag_name)
        has_update = compare_versions(current_numeric, latest_numeric) > 0
        
        return {
            'success': True,
            'has_update': has_update,
            'latest_version': latest_version,
            'tag_name': tag_name,
            'current_version': current_version,
            'download_url': download_url,
            'release_url': release_url,
            'release_notes': release_notes,
            'assets': assets  # Include assets for installer download
        }
        
    except HTTPError as e:
        if e.code == 404:
            return {
                'success': False,
                'error': 'Repository or release not found. Check repository settings.'
            }
        else:
            return {
                'success': False,
                'error': f'HTTP error {e.code}: {e.reason}'
            }
    
    except URLError as e:
        return {
            'success': False,
            'error': f'Network error: {str(e.reason)}'
        }
    
    except json.JSONDecodeError:
        return {
            'success': False,
            'error': 'Failed to parse GitHub API response.'
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }


def format_release_notes(notes, max_length=500):
    """
    Format release notes for display (truncate if too long)
    """
    if len(notes) <= max_length:
        return notes
    
    return notes[:max_length] + "..."
