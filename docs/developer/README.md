# Ticolops Developer Documentation

This guide helps developers understand, contribute to, and extend the Ticolops Student Collaboration Platform.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [API Integration](#api-integration)
5. [Frontend Development](#frontend-development)
6. [Backend Development](#backend-development)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Contributing](#contributing)

## Architecture Overview

Ticolops follows a modern full-stack architecture:

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context + Hooks
- **Routing**: React Router v6
- **Real-time**: WebSocket connections
- **Testing**: Vitest + Playwright

### Backend
- **Runtime**: Node.js with Express
- **Language**: TypeScript
- **Database**: PostgreSQL with Prisma ORM
- **Authentication**: JWT tokens
- **Real-time**: Socket.io
- **File Storage**: AWS S3 or local storage
- **Deployment**: Docker containers

### Infrastructure
- **Hosting**: Vercel (Frontend) + Railway/Heroku (Backend)
- **Database**: PostgreSQL (managed service)
- **CDN**: Vercel Edge Network
- **Monitoring**: Built-in analytics
- **CI/CD**: GitHub Actions

## Development Setup

### Prerequisites

- Node.js 18+ and npm
- PostgreSQL 14+
- Git
- Docker (optional)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/ticolops/platform.git
   cd platform
   ```

2. **Install dependencies**
   ```bash
   # Install frontend dependencies
   cd frontend
   npm install
   
   # Install backend dependencies
   cd ../backend
   npm install
   ```

3. **Environment setup**
   ```bash
   # Frontend (.env.local)
   VITE_API_URL=http://localhost:3000
   VITE_WS_URL=ws://localhost:3000
   
   # Backend (.env)
   DATABASE_URL=postgresql://user:password@localhost:5432/ticolops
   JWT_SECRET=your-secret-key
   PORT=3000
   NODE_ENV=development
   ```

4. **Database setup**
   ```bash
   cd backend
   npx prisma migrate dev
   npx prisma db seed
   ```

5. **Start development servers**
   ```bash
   # Terminal 1 - Backend
   cd backend
   npm run dev
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

### Docker Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Project Structure

```
ticolops/
├── frontend/                 # React frontend application
│   ├── src/
│   │   ├── components/      # Reusable UI components
│   │   ├── pages/          # Page components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── contexts/       # React contexts
│   │   ├── services/       # API service functions
│   │   ├── types/          # TypeScript type definitions
│   │   └── utils/          # Utility functions
│   ├── public/             # Static assets
│   ├── e2e/               # End-to-end tests
│   └── package.json
├── backend/                 # Node.js backend API
│   ├── src/
│   │   ├── controllers/    # Route controllers
│   │   ├── middleware/     # Express middleware
│   │   ├── models/         # Database models
│   │   ├── routes/         # API routes
│   │   ├── services/       # Business logic
│   │   ├── utils/          # Utility functions
│   │   └── types/          # TypeScript types
│   ├── prisma/             # Database schema and migrations
│   ├── tests/              # Backend tests
│   └── package.json
├── docs/                   # Documentation
│   ├── api/               # API documentation
│   ├── user-guide/        # User guides
│   └── developer/         # Developer documentation
├── docker-compose.yml      # Docker configuration
└── README.md
```

## API Integration

### Authentication

All API requests require authentication via JWT tokens:

```typescript
// services/api.ts
const API_BASE_URL = import.meta.env.VITE_API_URL;

class ApiService {
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...options.headers,
    };

    const response = await fetch(url, { ...options, headers });
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Auth methods
  async login(email: string, password: string) {
    return this.request<AuthResponse>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  }

  // Project methods
  async getProjects(params?: ProjectListParams) {
    const query = new URLSearchParams(params as any).toString();
    return this.request<ProjectListResponse>(`/api/projects?${query}`);
  }
}

export const apiService = new ApiService();
```

### WebSocket Integration

```typescript
// services/websocket.ts
class WebSocketService {
  private ws: WebSocket | null = null;
  private listeners: Map<string, Function[]> = new Map();

  connect(token: string) {
    const wsUrl = import.meta.env.VITE_WS_URL;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.send({ type: 'auth', token });
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.emit(data.type, data);
    };

    this.ws.onclose = () => {
      // Implement reconnection logic
      setTimeout(() => this.connect(token), 5000);
    };
  }

  on(event: string, callback: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, []);
    }
    this.listeners.get(event)!.push(callback);
  }

  private emit(event: string, data: any) {
    const callbacks = this.listeners.get(event) || [];
    callbacks.forEach(callback => callback(data));
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }
}

export const wsService = new WebSocketService();
```

## Frontend Development

### Component Architecture

Components follow a consistent structure:

```typescript
// components/ProjectCard.tsx
import React from 'react';
import { Project } from '../types/project';

interface ProjectCardProps {
  project: Project;
  onEdit?: (project: Project) => void;
  onDelete?: (projectId: string) => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onEdit,
  onDelete
}) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold mb-2">{project.name}</h3>
      <p className="text-gray-600 mb-4">{project.description}</p>
      
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-500">
          {project.memberCount} members
        </span>
        
        <div className="space-x-2">
          {onEdit && (
            <button
              onClick={() => onEdit(project)}
              className="px-3 py-1 bg-blue-500 text-white rounded"
            >
              Edit
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(project.id)}
              className="px-3 py-1 bg-red-500 text-white rounded"
            >
              Delete
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
```

### Custom Hooks

```typescript
// hooks/useProjects.ts
import { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import { Project } from '../types/project';

export const useProjects = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProjects = async () => {
    try {
      setLoading(true);
      const response = await apiService.getProjects();
      setProjects(response.data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const createProject = async (projectData: CreateProjectData) => {
    try {
      const response = await apiService.createProject(projectData);
      setProjects(prev => [...prev, response.data.project]);
      return response.data.project;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
      throw err;
    }
  };

  return {
    projects,
    loading,
    error,
    fetchProjects,
    createProject
  };
};
```

### State Management

```typescript
// contexts/AuthContext.tsx
import React, { createContext, useContext, useReducer } from 'react';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  loading: boolean;
}

type AuthAction =
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'LOGOUT' }
  | { type: 'SET_LOADING'; payload: boolean };

const authReducer = (state: AuthState, action: AuthAction): AuthState => {
  switch (action.type) {
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        loading: false
      };
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        loading: false
      };
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    default:
      return state;
  }
};

const AuthContext = createContext<{
  state: AuthState;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
} | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children
}) => {
  const [state, dispatch] = useReducer(authReducer, {
    user: null,
    token: localStorage.getItem('auth_token'),
    isAuthenticated: false,
    loading: true
  });

  const login = async (email: string, password: string) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const response = await apiService.login(email, password);
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user: response.data.user,
          token: response.data.token
        }
      });
      apiService.setToken(response.data.token);
    } catch (error) {
      dispatch({ type: 'SET_LOADING', payload: false });
      throw error;
    }
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    dispatch({ type: 'LOGOUT' });
  };

  return (
    <AuthContext.Provider value={{ state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
```

## Backend Development

### API Route Structure

```typescript
// routes/projects.ts
import { Router } from 'express';
import { ProjectController } from '../controllers/ProjectController';
import { authMiddleware } from '../middleware/auth';
import { validateRequest } from '../middleware/validation';
import { createProjectSchema } from '../schemas/project';

const router = Router();
const projectController = new ProjectController();

// Apply authentication to all routes
router.use(authMiddleware);

router.get('/', projectController.getProjects);
router.post('/', validateRequest(createProjectSchema), projectController.createProject);
router.get('/:id', projectController.getProject);
router.put('/:id', projectController.updateProject);
router.delete('/:id', projectController.deleteProject);
router.post('/:id/invite', projectController.inviteMembers);

export { router as projectRoutes };
```

### Controller Implementation

```typescript
// controllers/ProjectController.ts
import { Request, Response } from 'express';
import { ProjectService } from '../services/ProjectService';
import { AuthenticatedRequest } from '../types/auth';

export class ProjectController {
  private projectService = new ProjectService();

  getProjects = async (req: AuthenticatedRequest, res: Response) => {
    try {
      const userId = req.user!.id;
      const params = req.query;
      
      const result = await this.projectService.getProjectsForUser(userId, params);
      
      res.json({
        success: true,
        data: result
      });
    } catch (error) {
      res.status(500).json({
        success: false,
        error: {
          code: 'INTERNAL_ERROR',
          message: 'Failed to fetch projects'
        }
      });
    }
  };

  createProject = async (req: AuthenticatedRequest, res: Response) => {
    try {
      const userId = req.user!.id;
      const projectData = req.body;
      
      const project = await this.projectService.createProject(userId, projectData);
      
      res.status(201).json({
        success: true,
        data: { project }
      });
    } catch (error) {
      res.status(400).json({
        success: false,
        error: {
          code: 'VALIDATION_ERROR',
          message: error.message
        }
      });
    }
  };
}
```

### Service Layer

```typescript
// services/ProjectService.ts
import { PrismaClient } from '@prisma/client';
import { CreateProjectData, ProjectListParams } from '../types/project';

export class ProjectService {
  private prisma = new PrismaClient();

  async getProjectsForUser(userId: string, params: ProjectListParams) {
    const {
      page = 1,
      limit = 20,
      search,
      status,
      visibility,
      sort = 'createdAt',
      order = 'desc'
    } = params;

    const where = {
      OR: [
        { ownerId: userId },
        { members: { some: { userId } } }
      ],
      ...(search && {
        OR: [
          { name: { contains: search, mode: 'insensitive' } },
          { description: { contains: search, mode: 'insensitive' } }
        ]
      }),
      ...(status && { status }),
      ...(visibility && { visibility })
    };

    const [projects, total] = await Promise.all([
      this.prisma.project.findMany({
        where,
        include: {
          owner: { select: { id: true, name: true } },
          _count: {
            select: {
              members: true,
              repositories: true
            }
          }
        },
        orderBy: { [sort]: order },
        skip: (page - 1) * limit,
        take: limit
      }),
      this.prisma.project.count({ where })
    ]);

    return {
      items: projects.map(project => ({
        ...project,
        ownerName: project.owner.name,
        memberCount: project._count.members,
        repositoryCount: project._count.repositories
      })),
      pagination: {
        page,
        limit,
        total,
        pages: Math.ceil(total / limit),
        hasNext: page * limit < total,
        hasPrev: page > 1
      }
    };
  }

  async createProject(userId: string, data: CreateProjectData) {
    return this.prisma.project.create({
      data: {
        ...data,
        ownerId: userId,
        members: {
          create: [
            { userId, role: 'owner' },
            ...(data.initialMembers || []).map(member => ({
              email: member.email,
              role: member.role || 'member',
              status: 'pending'
            }))
          ]
        }
      },
      include: {
        owner: { select: { id: true, name: true } },
        _count: {
          select: {
            members: true,
            repositories: true
          }
        }
      }
    });
  }
}
```

## Testing

### Unit Tests (Frontend)

```typescript
// components/__tests__/ProjectCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { ProjectCard } from '../ProjectCard';
import { mockProject } from '../../__mocks__/project';

describe('ProjectCard', () => {
  it('renders project information', () => {
    render(<ProjectCard project={mockProject} />);
    
    expect(screen.getByText(mockProject.name)).toBeInTheDocument();
    expect(screen.getByText(mockProject.description)).toBeInTheDocument();
    expect(screen.getByText(`${mockProject.memberCount} members`)).toBeInTheDocument();
  });

  it('calls onEdit when edit button is clicked', () => {
    const onEdit = vi.fn();
    render(<ProjectCard project={mockProject} onEdit={onEdit} />);
    
    fireEvent.click(screen.getByText('Edit'));
    expect(onEdit).toHaveBeenCalledWith(mockProject);
  });

  it('calls onDelete when delete button is clicked', () => {
    const onDelete = vi.fn();
    render(<ProjectCard project={mockProject} onDelete={onDelete} />);
    
    fireEvent.click(screen.getByText('Delete'));
    expect(onDelete).toHaveBeenCalledWith(mockProject.id);
  });
});
```

### Integration Tests (Backend)

```typescript
// tests/integration/projects.test.ts
import request from 'supertest';
import { app } from '../../src/app';
import { createTestUser, createAuthToken } from '../helpers/auth';

describe('Projects API', () => {
  let authToken: string;
  let userId: string;

  beforeEach(async () => {
    const user = await createTestUser();
    userId = user.id;
    authToken = createAuthToken(user);
  });

  describe('GET /api/projects', () => {
    it('returns projects for authenticated user', async () => {
      const response = await request(app)
        .get('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.success).toBe(true);
      expect(response.body.data.items).toBeInstanceOf(Array);
      expect(response.body.data.pagination).toBeDefined();
    });

    it('returns 401 for unauthenticated requests', async () => {
      await request(app)
        .get('/api/projects')
        .expect(401);
    });
  });

  describe('POST /api/projects', () => {
    it('creates a new project', async () => {
      const projectData = {
        name: 'Test Project',
        description: 'A test project',
        visibility: 'private'
      };

      const response = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .send(projectData)
        .expect(201);

      expect(response.body.success).toBe(true);
      expect(response.body.data.project.name).toBe(projectData.name);
      expect(response.body.data.project.ownerId).toBe(userId);
    });

    it('validates required fields', async () => {
      const response = await request(app)
        .post('/api/projects')
        .set('Authorization', `Bearer ${authToken}`)
        .send({})
        .expect(400);

      expect(response.body.success).toBe(false);
      expect(response.body.error.code).toBe('VALIDATION_ERROR');
    });
  });
});
```

### End-to-End Tests

E2E tests are already created in the `frontend/e2e/` directory using Playwright. Run them with:

```bash
cd frontend
npx playwright test
```

## Deployment

### Frontend Deployment (Vercel)

1. **Connect repository to Vercel**
2. **Configure build settings**:
   - Build Command: `npm run build`
   - Output Directory: `dist`
   - Install Command: `npm install`

3. **Environment variables**:
   ```
   VITE_API_URL=https://api.ticolops.com
   VITE_WS_URL=wss://api.ticolops.com
   ```

### Backend Deployment (Railway/Heroku)

1. **Dockerfile**:
   ```dockerfile
   FROM node:18-alpine
   WORKDIR /app
   COPY package*.json ./
   RUN npm ci --only=production
   COPY . .
   RUN npx prisma generate
   EXPOSE 3000
   CMD ["npm", "start"]
   ```

2. **Environment variables**:
   ```
   DATABASE_URL=postgresql://...
   JWT_SECRET=your-production-secret
   NODE_ENV=production
   PORT=3000
   ```

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        run: |
          cd frontend && npm ci
          cd ../backend && npm ci
      
      - name: Run tests
        run: |
          cd frontend && npm test
          cd ../backend && npm test
      
      - name: Run E2E tests
        run: |
          cd frontend && npx playwright test

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Vercel
        uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Railway
        uses: railway-app/railway-action@v1
        with:
          token: ${{ secrets.RAILWAY_TOKEN }}
```

## Contributing

### Development Workflow

1. **Fork the repository**
2. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
4. **Write tests** for new functionality
5. **Run the test suite**:
   ```bash
   npm test
   ```

6. **Submit a pull request**

### Code Standards

- **TypeScript**: Strict mode enabled
- **ESLint**: Airbnb configuration
- **Prettier**: Automatic code formatting
- **Conventional Commits**: Use conventional commit messages

### Pull Request Guidelines

- Include a clear description of changes
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass
- Follow the existing code style

---

For more information, visit our [GitHub repository](https://github.com/ticolops/platform) or contact the development team.