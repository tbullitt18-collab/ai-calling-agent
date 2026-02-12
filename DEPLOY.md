# Deploying Rain Check

Click the button below to deploy to Render:
[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/tbullitt18-collab/ai-calling-agent)

## Environment Variables

When prompted, fill in the values from your `.env` file.
For `VONAGE_PRIVATE_KEY`, copy the entire content of `private.key` including the BEGIN/END headers.

## After Deployment
Update your Vonage Dashboard webhooks to point to your new Render URL.
Example: `https://your-app-name.onrender.com/answer`
