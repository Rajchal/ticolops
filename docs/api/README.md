# Ticolops API Documentation

This document provides comprehensive documentation for the Ticolops Student Collaboration Platform API.

## Base URL

```
Production: https://api.ticolops.com
Staging: https://staging-api.ticolops.com
Development: http://localhost:3000
```

## Authentication

The API uses JWT (JSON Web Tokens) for authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

## Response Format

All API responses follow a consistent format:

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "message": "Operation completed successfully"
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // Additional error details
    }
  }
}
```

## HTTP Status Codes

- `200` - OK: Request successful
- `201` - Created: Resource created successfully
- `400` - Bad Request: Invalid request data
- `401` - Unauthorized: Authentication required
- `403` - Forbidden: Insufficient permissions
- `404` - Not Found: Resource not found
- `409` - Conflict: Resource already exists
- `422` - Unprocessable Entity: Validation errors
- `500` - Internal Server Error: Server error

## Rate Limiting

API requests are rate limited to prevent abuse:

- **Authenticated users**: 1000 requests per hour
- **Unauthenticated users**: 100 requests per hour

Rate limit headers are included in responses:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640995200
```

## Pagination

List endpoints support pagination using query parameters:

```
GET /api/projects?page=1&limit=20&sort=createdAt&order=desc
```

### Pagination Response
```json
{
  "success": true,
  "data": {
    "items": [...],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "pages": 5,
      "hasNext": true,
      "hasPrev": false
    }
  }
}
```

## WebSocket Events

Real-time features use WebSocket connections:

```javascript
const ws = new WebSocket('wss://api.ticolops.com/ws');

// Authentication
ws.send(JSON.stringify({
  type: 'auth',
  token: 'your-jwt-token'
}));

// Join project room
ws.send(JSON.stringify({
  type: 'join_project',
  projectId: 'project-123'
}));
```

### WebSocket Event Types

- `activity_event` - Team activity updates
- `presence_update` - User presence changes
- `conflict_alert` - Merge conflict notifications
- `deployment_update` - Deployment status changes
- `collaboration_suggestion` - AI-generated collaboration suggestions

## API Endpoints

### Authentication

#### POST /api/auth/register
Register a new user account.

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "password": "securepassword123",
  "role": "student"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user-123",
      "name": "John Doe",
      "email": "john@example.com",
      "role": "student",
      "createdAt": "2024-01-15T10:00:00Z"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### POST /api/auth/login
Authenticate user and get access token.

**Request Body:**
```json
{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user-123",
      "name": "John Doe",
      "email": "john@example.com",
      "role": "student"
    },
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

#### POST /api/auth/logout
Invalidate current session token.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

#### GET /api/auth/me
Get current user information.

**Headers:** `Authorization: Bearer <token>`

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user-123",
      "name": "John Doe",
      "email": "john@example.com",
      "role": "student",
      "createdAt": "2024-01-15T10:00:00Z",
      "lastLoginAt": "2024-01-16T09:30:00Z"
    }
  }
}
```

### Projects

#### GET /api/projects
Get list of projects for the authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (number): Page number (default: 1)
- `limit` (number): Items per page (default: 20, max: 100)
- `search` (string): Search term
- `status` (string): Filter by status (active, archived, draft)
- `visibility` (string): Filter by visibility (public, private)
- `sort` (string): Sort field (name, createdAt, lastActivity)
- `order` (string): Sort order (asc, desc)

**Response:**
```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "project-123",
        "name": "E-commerce Platform",
        "description": "A modern e-commerce platform",
        "ownerId": "user-123",
        "ownerName": "John Doe",
        "memberCount": 5,
        "repositoryCount": 3,
        "status": "active",
        "visibility": "private",
        "createdAt": "2024-01-01T10:00:00Z",
        "lastActivity": "2024-01-15T14:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 1,
      "pages": 1,
      "hasNext": false,
      "hasPrev": false
    }
  }
}
```

For complete API documentation including all endpoints, examples, and SDKs, visit: https://docs.ticolops.com/api