#!/usr/bin/env python3
"""
WordCamp Favorite Sessions Extractor
Extracts favorite session data from WordCamp schedule URLs and generates ICS calendar files.
"""

import requests
import re
from urllib.parse import urlparse, parse_qs
from datetime import datetime
import sys

def extract_favorite_ids(schedule_url):
    """Extract favorite session IDs from WordCamp schedule URL."""
    parsed_url = urlparse(schedule_url)
    query_params = parse_qs(parsed_url.query)
    
    fav_sessions = query_params.get('fav-sessions', [])
    if not fav_sessions:
        print("No favorite sessions found in URL")
        return []
    
    # Split comma-separated IDs
    session_ids = fav_sessions[0].split(',')
    return [id.strip() for id in session_ids]

def get_wordcamp_base_url(schedule_url):
    """Extract base WordCamp URL from schedule URL."""
    parsed_url = urlparse(schedule_url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path.rstrip('/schedule/')}"
    return base_url

def fetch_session_data(base_url, session_ids):
    """Fetch session data from WordCamp REST API."""
    api_url = f"{base_url}/wp-json/wp/v2/sessions"
    
    # WordPress REST API has limits on include parameter length
    # Split into chunks if too many IDs
    chunk_size = 10
    all_sessions = []
    
    for i in range(0, len(session_ids), chunk_size):
        chunk = session_ids[i:i + chunk_size]
        params = {'include': ','.join(chunk)}
        
        try:
            response = requests.get(api_url, params=params, timeout=30)
            response.raise_for_status()
            sessions = response.json()
            all_sessions.extend(sessions)
        except requests.exceptions.RequestException as e:
            print(f"Error fetching sessions {chunk}: {e}")
            continue
    
    return all_sessions

def extract_session_info(session_data):
    """Extract title, speaker, location, and time from session data."""
    sessions = []
    
    for session in session_data:
        # Extract basic info
        title = session.get('title', {}).get('rendered', 'Unknown Title')
        
        # Extract speaker names from meta or content
        speakers = []
        if 'meta' in session:
            # Try different meta fields that might contain speakers
            speaker_fields = ['_wcpt_speaker_id', 'speakers', '_wcb_session_speakers']
            for field in speaker_fields:
                if field in session['meta'] and session['meta'][field]:
                    speakers.extend(session['meta'][field] if isinstance(session['meta'][field], list) else [session['meta'][field]])
        
        # Fallback: extract from content if no speakers found
        if not speakers and 'content' in session:
            content = session['content'].get('rendered', '')
            # Simple regex to find speaker names (this might need adjustment)
            speaker_matches = re.findall(r'Speaker[s]?:\s*([^<\n]+)', content, re.IGNORECASE)
            if speaker_matches:
                speakers = [match.strip() for match in speaker_matches]
        
        # Extract location/track
        location = "Unknown Location"
        if 'meta' in session:
            location_fields = ['_wcpt_track_id', 'track', 'location', '_wcb_session_track']
            for field in location_fields:
                if field in session['meta'] and session['meta'][field]:
                    location = session['meta'][field]
                    break
        
        # Extract date and time
        date_time = session.get('date', '')
        
        sessions.append({
            'id': session.get('id'),
            'title': title,
            'speakers': speakers if speakers else ['Unknown Speaker'],
            'location': location,
            'datetime': date_time
        })
    
    return sessions

def generate_ics_calendar(sessions, output_file="wordcamp_favorites.ics"):
    """Generate ICS calendar file from session data."""
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//WordCamp Favorites//Session Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH

BEGIN:VTIMEZONE
TZID:America/Los_Angeles
BEGIN:DAYLIGHT
TZOFFSETFROM:-0800
TZOFFSETTO:-0700
TZNAME:PDT
DTSTART:20250309T020000
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:-0700
TZOFFSETTO:-0800
TZNAME:PST
DTSTART:20251102T020000
RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU
END:STANDARD
END:VTIMEZONE

"""

    for session in sessions:
        # Format speakers
        speaker_list = ', '.join(session['speakers'])
        
        # Create event entry
        ics_content += f"""BEGIN:VEVENT
UID:{session['id']}@wordcamp-favorites
DTSTART;TZID=America/Los_Angeles:{session.get('datetime', '20250101T120000').replace('-', '').replace(':', '').replace('T', 'T')}
DTEND;TZID=America/Los_Angeles:{session.get('datetime', '20250101T130000').replace('-', '').replace(':', '').replace('T', 'T')}
SUMMARY:{session['title']}
DESCRIPTION:Speaker(s): {speaker_list}
LOCATION:{session['location']}
END:VEVENT

"""

    ics_content += "END:VCALENDAR"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(ics_content)
    
    print(f"Calendar saved to: {output_file}")

def main():
    """Main function to run the WordCamp favorites extractor."""
    if len(sys.argv) != 2:
        print("Usage: python wordcamp_favorites.py <schedule_url>")
        print("Example: python wordcamp_favorites.py 'https://us.wordcamp.org/2025/schedule/?fav-sessions=1834,1952'")
        sys.exit(1)
    
    schedule_url = sys.argv[1]
    
    print(f"Processing WordCamp schedule: {schedule_url}")
    
    # Extract favorite session IDs
    session_ids = extract_favorite_ids(schedule_url)
    if not session_ids:
        sys.exit(1)
    
    print(f"Found {len(session_ids)} favorite sessions: {', '.join(session_ids)}")
    
    # Get base URL for API calls
    base_url = get_wordcamp_base_url(schedule_url)
    print(f"WordCamp API base: {base_url}")
    
    # Fetch session data
    session_data = fetch_session_data(base_url, session_ids)
    if not session_data:
        print("No session data retrieved")
        sys.exit(1)
    
    print(f"Retrieved {len(session_data)} sessions")
    
    # Extract session information
    sessions = extract_session_info(session_data)
    
    # Display sessions
    print("\nFavorite Sessions:")
    print("-" * 50)
    for session in sessions:
        speaker_list = ', '.join(session['speakers'])
        print(f"• {session['title']}")
        print(f"  Speaker(s): {speaker_list}")
        print(f"  Location: {session['location']}")
        print(f"  DateTime: {session['datetime']}")
        print()
    
    # Generate calendar file
    output_file = "wordcamp_favorites.ics"
    generate_ics_calendar(sessions, output_file)

if __name__ == "__main__":
    main()