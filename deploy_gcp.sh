#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Deploying Code Research Assistant to GCP Cloud Run..."
echo ""

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo -e "${RED}❌ .env file not found!${NC}"
    exit 1
fi

# Check required variables
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}❌ GCP_PROJECT_ID not set in .env${NC}"
    exit 1
fi

if [ -z "$GROQ_API_KEY" ]; then
    echo -e "${RED}❌ GROQ_API_KEY not set in .env${NC}"
    exit 1
fi

# Set default values
GCP_REGION=${GCP_REGION:-us-central1}
GCP_SERVICE_NAME=${GCP_SERVICE_NAME:-code-research-assistant}

echo -e "${GREEN}📋 Deployment Configuration:${NC}"
echo "   Project ID: $GCP_PROJECT_ID"
echo "   Region: $GCP_REGION"
echo "   Service Name: $GCP_SERVICE_NAME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found!${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set GCP project
echo -e "${YELLOW}🔧 Setting GCP project...${NC}"
gcloud config set project $GCP_PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}🔧 Enabling required GCP APIs...${NC}"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    --project=$GCP_PROJECT_ID

# Build container image
echo -e "${YELLOW}🏗️  Building container image...${NC}"
gcloud builds submit \
    --tag gcr.io/$GCP_PROJECT_ID/$GCP_SERVICE_NAME \
    --project=$GCP_PROJECT_ID

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

# Deploy to Cloud Run
echo -e "${YELLOW}🚀 Deploying to Cloud Run...${NC}"
gcloud run deploy $GCP_SERVICE_NAME \
    --image gcr.io/$GCP_PROJECT_ID/$GCP_SERVICE_NAME \
    --platform managed \
    --region $GCP_REGION \
    --allow-unauthenticated \
    --set-env-vars "GROQ_API_KEY=$GROQ_API_KEY" \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080 \
    --project=$GCP_PROJECT_ID

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Deployment failed!${NC}"
    exit 1
fi

# Get service URL
SERVICE_URL=$(gcloud run services describe $GCP_SERVICE_NAME \
    --region $GCP_REGION \
    --format 'value(status.url)' \
    --project=$GCP_PROJECT_ID)

echo ""
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo "📝 API Docs: $SERVICE_URL/docs"
echo "🏥 Health Check: $SERVICE_URL/health"
echo ""
echo -e "${YELLOW}📊 View logs:${NC}"
echo "   gcloud run services logs read $GCP_SERVICE_NAME --region $GCP_REGION --project $GCP_PROJECT_ID"
echo ""
echo -e "${YELLOW}🔄 Update deployment:${NC}"
echo "   ./deploy_gcp.sh"
echo ""
echo -e "${YELLOW}🗑️  Delete service:${NC}"
echo "   gcloud run services delete $GCP_SERVICE_NAME --region $GCP_REGION --project $GCP_PROJECT_ID"
echo ""