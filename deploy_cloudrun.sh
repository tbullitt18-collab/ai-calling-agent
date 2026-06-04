#!/bin/bash
# Deploy Rain Check to Google Cloud Run
# Usage: ./deploy_cloudrun.sh [project-id] [region]
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. APIs enabled: Cloud Run, Artifact Registry, Vertex AI, Speech-to-Text, Text-to-Speech
#   3. Service account with necessary permissions

set -e

PROJECT_ID="${1:-$(gcloud config get-value project)}"
REGION="${2:-us-central1}"
SERVICE_NAME="raincheck-api"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=== Rain Check → Google Cloud Run ==="
echo "Project: ${PROJECT_ID}"
echo "Region:  ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Enable required APIs
echo "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    aiplatform.googleapis.com \
    speech.googleapis.com \
    texttospeech.googleapis.com \
    --project="${PROJECT_ID}" \
    --quiet

# Build and push container image
echo "Building container image..."
gcloud builds submit \
    --tag "${IMAGE}" \
    --project="${PROJECT_ID}" \
    --quiet

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 3 \
    --timeout 120 \
    --set-env-vars "FLASK_ENV=production" \
    --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --set-env-vars "GOOGLE_CLOUD_LOCATION=${REGION}" \
    --project="${PROJECT_ID}" \
    --quiet

# Get service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --region "${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo ""
echo "=== Deployment Complete ==="
echo "URL: ${SERVICE_URL}"
echo ""
echo "Next steps:"
echo "  1. Set secrets (run each line):"
echo "     gcloud run services update ${SERVICE_NAME} --region ${REGION} \\"
echo "       --set-env-vars VONAGE_API_KEY=xxx,VONAGE_API_SECRET=xxx,VONAGE_NUMBER=xxx \\"
echo "       --set-env-vars VONAGE_APPLICATION_ID=xxx \\"
echo "       --set-env-vars VONAGE_PRIVATE_KEY='...' \\"
echo "       --set-env-vars ELEVENLABS_API_KEY=xxx,ELEVENLABS_VOICE_ID=xxx \\"
echo "       --set-env-vars MONGODB_URI='mongodb+srv://...' \\"
echo "       --set-env-vars BASE_URL=${SERVICE_URL}"
echo ""
echo "  2. Update Vonage webhooks:"
echo "     Answer URL: ${SERVICE_URL}/webhook/answer"
echo "     Event URL:  ${SERVICE_URL}/webhook/events"
echo ""
echo "  3. Test health: curl ${SERVICE_URL}/health"
