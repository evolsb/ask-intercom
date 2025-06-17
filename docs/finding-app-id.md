# Finding Your Intercom App ID

The Intercom App ID (also called Workspace ID) is required to generate direct links to conversations. The Ask-Intercom tool will attempt to fetch this automatically, but you can also find it manually.

## Automatic Detection (Recommended)

The tool automatically fetches your app ID from the Intercom API when you run your first query. No configuration needed!

## Manual Methods

### Method 1: From the Intercom Web UI

1. Log into your Intercom account at https://app.intercom.com
2. Look at the URL in your browser
3. The app ID is the code after `/inbox/`:
   - Example URL: `https://app.intercom.com/a/inbox/sc3pepw3/inbox/...`
   - App ID: `sc3pepw3`

### Method 2: Using the API

Run this curl command with your Intercom access token:

```bash
curl https://api.intercom.io/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Accept: application/json" | jq '.app.id_code'
```

This will return your app ID (e.g., `"sc3pepw3"`).

### Method 3: Using the Test Script

We've included a test script that finds your app ID:

```bash
poetry run python test_app_id.py
```

Look for the output from the `/me` endpoint - it will show:
```json
"app": {
  "type": "app",
  "id_code": "sc3pepw3",  // <-- This is your app ID
  "name": "Your Workspace Name",
  ...
}
```

## Adding to Configuration

If automatic detection fails, add your app ID to the `.env` file:

```bash
INTERCOM_APP_ID=sc3pepw3
```

## Troubleshooting

- **No app ID found**: Ensure your API token has the correct permissions
- **Wrong workspace**: If you have multiple workspaces, make sure your API token is for the correct one
- **Links not working**: Verify the app ID matches what you see in the Intercom web UI

## Technical Details

The app ID is found in the Intercom API response at:
- Endpoint: `GET /me`
- Path: `response.app.id_code`
- Format: Short alphanumeric string (e.g., `sc3pepw3`)

This differs from the admin ID (`response.id`) which is numeric.
