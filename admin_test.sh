#!/bin/bash

BASE_URL="http://localhost:6000"

echo "Logging in as admin..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "admin123"
  }')

TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.token')

echo "Getting current user info..."
curl -s -X GET "$BASE_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Creating new invite..."
curl -s -X POST "$BASE_URL/invites/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newdev@test.com",
    "role": "dev"
  }' | jq '.'


echo "Creating new cluster..."
curl -s -X POST "$BASE_URL/clusters/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-cluster-3",
    "ram": 32,
    "cpu": 16,
    "gpu": 4
  }' | jq '.'

echo "Listing active clusters..."
curl -s -X GET "$BASE_URL/clusters/" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Listing all clusters including deleted..."
curl -s -X GET "$BASE_URL/clusters/?include_deleted=true" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Getting cluster 1 resources..."
curl -s -X GET "$BASE_URL/clusters/1/resources" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Deleting cluster 3..."
curl -s -X DELETE "$BASE_URL/clusters/3" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Creating high priority deployment..."
curl -s -X POST "$BASE_URL/deployments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "high-priority-deployment",
    "cluster_id": 1,
    "ram": 8,
    "cpu": 4,
    "gpu": 1,
    "priority": 5
  }' | jq '.'

echo "Creating low priority deployment..."
curl -s -X POST "$BASE_URL/deployments/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "low-priority-deployment",
    "cluster_id": 1,
    "ram": 4,
    "cpu": 2,
    "gpu": 0,
    "priority": 1
  }' | jq '.'

echo "Listing all deployments..."
curl -s -X GET "$BASE_URL/deployments/" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Listing deployments in cluster 1..."
curl -s -X GET "$BASE_URL/deployments/?cluster_id=1" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Listing all deployments including deleted..."
curl -s -X GET "$BASE_URL/deployments/?include_deleted=true" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Getting deployment 1 details..."
curl -s -X GET "$BASE_URL/deployments/1" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo "Getting organization details..."
curl -s -X GET "$BASE_URL/organisation/1" \
  -H "Authorization: Bearer $TOKEN" | jq '.' 