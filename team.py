import requests
import csv
import os
from datetime import datetime

# Get enterprise slug from environment variable
ENTERPRISE_SLUG = os.getenv('ENTERPRISE_SLUG')  # Set your enterprise slug here
AUTH_TOKEN = os.getenv('AUTH_TOKEN')  # Set your auth token here

if not ENTERPRISE_SLUG:
    raise ValueError("ENTERPRISE_SLUG environment variable must be set")
if not AUTH_TOKEN:
    raise ValueError("GH_ADMIN_TOKEN environment variable must be set")

headers = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28"
}

def get_teams():
    url = f"https://api.github.com/enterprises/{ENTERPRISE_SLUG}/teams"
    teams = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            teams.extend(data)
            url = response.links.get('next', {}).get('url')
        else:
            raise Exception(f"Error fetching teams: {response.status_code} {response.text}")
    return teams

def get_team_memberships(team_slug):
    url = f"https://api.github.com/enterprises/{ENTERPRISE_SLUG}/teams/{team_slug}/memberships"
    members = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            members.extend(data)
            url = response.links.get('next', {}).get('url')
        else:
            raise Exception(f"Error fetching team memberships: {response.status_code} {response.text}")
    return members

def get_copilot_billing_seats():
    url = f"https://api.github.com/enterprises/{ENTERPRISE_SLUG}/copilot/billing/seats"
    seats = []
    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            seats.extend(data['seats'])
            url = response.links.get('next', {}).get('url')
        else:
            raise Exception(f"Error fetching copilot seats: {response.status_code} {response.text}")
    return seats

def get_user_details(username):
    url = f"https://api.github.com/users/{username}"
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return {
            'email': data.get('email', ''),  # May be None if private
            'created_at': data.get('created_at', '')
        }
    else:
        return {'email': '', 'created_at': ''}

def main():
    teams = get_teams()
    print(f"Fetched {len(teams)} teams")
    copilot_seats = get_copilot_billing_seats()
    print(f"Fetched {len(copilot_seats)} Copilot seats")
    output_data = []

    for team in teams:
        team_slug = team['slug']
        members = get_team_memberships(team_slug)
        print(f"Team '{team['name']}' has {len(members)} members")
        for member in members:
            if member['type'] == 'User':
                username = member['login']
                copilot_info = next((seat for seat in copilot_seats if seat.get('assignee', {}).get('login') == username), None)
                user_info = get_user_details(username)
                if copilot_info:
                    output_data.append({
                        'enterprise_name': ENTERPRISE_SLUG,
                        'team_name': team['name'],
                        'user_name': username,
                        'Email': user_info['email'],
                        'Created At': user_info['created_at'],
                        'Last Activity At': copilot_info.get('last_activity_at', ''),
                        'Last Active Editor': copilot_info.get('last_activity_editor', ''),
                        'Editor Version': copilot_info.get('editor_version', ''),
                        'Plugin': copilot_info.get('plugin', ''),
                        'Plugin Version': copilot_info.get('plugin_version', ''),
                        'status': 'active' if copilot_info.get('last_activity_editor') else 'inactive'
                    })
    if not output_data:
        print("No data to write to CSV")
    else:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        csv_file_name = f"teams_{timestamp}.csv"
        fieldnames = [
            'enterprise_name', 'team_name', 'user_name', 'Email', 'Created At',
            'Last Activity At', 'Last Active Editor', 'Editor Version', 'Plugin', 'Plugin Version', 'status'
        ]
        with open(csv_file_name, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for row in output_data:
                writer.writerow(row)
        print(f"Data written to {csv_file_name}")

if __name__ == "__main__":
    main()
