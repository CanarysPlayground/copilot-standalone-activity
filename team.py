import requests
import csv
import os
from datetime import datetime

# Get enterprise slug and token from environment variables
ENTERPRISE_SLUG = os.getenv('ENTERPRISE_SLUG')  # e.g., 'ltimghce'
AUTH_TOKEN = os.getenv('AUTH_TOKEN')  # GitHub PAT with necessary scopes

# Validate environment variables
if not ENTERPRISE_SLUG:
    raise ValueError("ENTERPRISE_SLUG environment variable must be set")
if not AUTH_TOKEN:
    raise ValueError("AUTH_TOKEN environment variable must be set")

# Request headers
headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28"
}

# Fetch all teams under the enterprise
def get_teams():
    url = f"https://api.github.com/enterprises/{ENTERPRISE_SLUG}/teams"
    teams = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            teams.extend(response.json())
            url = response.links.get('next', {}).get('url')
        else:
            raise Exception(f"Error fetching teams: {response.status_code} {response.text}")
    return teams

# Fetch all members of a given team
def get_team_memberships(team_slug):
    url = f"https://api.github.com/enterprises/{ENTERPRISE_SLUG}/teams/{team_slug}/memberships"
    members = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            members.extend(response.json())
            url = response.links.get('next', {}).get('url')
        else:
            raise Exception(f"Error fetching memberships for team {team_slug}: {response.status_code} {response.text}")
    return members

# Fetch Copilot seat details for all users
def get_copilot_billing_seats():
    url = f"https://api.github.com/enterprises/{ENTERPRISE_SLUG}/copilot/billing/seats"
    seats = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            seats.extend(response.json().get('seats', []))
            url = response.links.get('next', {}).get('url')
        else:
            raise Exception(f"Error fetching Copilot seats: {response.status_code} {response.text}")
    return seats

# Get user's public details
def get_user_details(username):
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return {
            'email': data.get('email') or 'N/A',
            'created_at': data.get('created_at', 'N/A')
        }
    else:
        return {'email': 'N/A', 'created_at': 'N/A'}

# Main logic
def main():
    teams = get_teams()
    print(f"✅ Fetched {len(teams)} teams")

    copilot_seats = get_copilot_billing_seats()
    print(f"✅ Fetched {len(copilot_seats)} Copilot seats")

    output_data = []

    for team in teams:
        team_slug = team['slug']
        members = get_team_memberships(team_slug)
        print(f"🔍 Team '{team['name']}' has {len(members)} members")

        for member in members:
            if member.get('type') == 'User':
                username = member['login']
                user_info = get_user_details(username)
                copilot_info = next(
                    (seat for seat in copilot_seats if seat.get('assignee', {}).get('login') == username),
                    {}
                )

                output_data.append({
                    'enterprise_name': ENTERPRISE_SLUG,
                    'team_name': team['name'],
                    'user_name': username,
                    'Email': user_info['email'],
                    'Created At': user_info['created_at'],
                    'Last Activity At': copilot_info.get('last_activity_at', 'N/A'),
                    'Last Active Editor': copilot_info.get('last_activity_editor', 'N/A'),
                    'Editor Version': copilot_info.get('editor_version', 'N/A'),
                    'Plugin': copilot_info.get('plugin', 'N/A'),
                    'Plugin Version': copilot_info.get('plugin_version', 'N/A'),
                    'status': 'active' if copilot_info.get('last_activity_editor') else 'inactive'
                })

    # Write to CSV
    if not output_data:
        print("⚠️ No data to write to CSV")
    else:
        # Write to a fixed name for workflow artifact upload
        csv_file_name = "copilot_billing_seats.csv"
        fieldnames = [
            'enterprise_name', 'team_name', 'user_name', 'Email', 'Created At',
            'Last Activity At', 'Last Active Editor', 'Editor Version',
            'Plugin', 'Plugin Version', 'status'
        ]
        with open(csv_file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_data)
        print(f"✅ Data written to `{csv_file_name}`")

if __name__ == "__main__":
    main()
