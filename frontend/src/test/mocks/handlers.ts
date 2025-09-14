import { rest } from 'msw';

const API_URL = 'http://localhost:3000';

export const handlers = [
  // Auth endpoints
  rest.post(`${API_URL}/api/auth/login`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          user: {
            id: 'user-1',
            name: 'Test User',
            email: 'test@example.com',
            role: 'student'
          },
          token: 'mock-jwt-token'
        }
      })
    );
  }),

  rest.post(`${API_URL}/api/auth/register`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        success: true,
        data: {
          user: {
            id: 'user-1',
            name: 'Test User',
            email: 'test@example.com',
            role: 'student'
          },
          token: 'mock-jwt-token'
        }
      })
    );
  }),

  rest.get(`${API_URL}/api/auth/me`, (req, res, ctx) => {
    const authHeader = req.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res(ctx.status(401), ctx.json({ error: 'Unauthorized' }));
    }

    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          user: {
            id: 'user-1',
            name: 'Test User',
            email: 'test@example.com',
            role: 'student'
          }
        }
      })
    );
  }),

  // Projects endpoints
  rest.get(`${API_URL}/api/projects`, (req, res, ctx) => {
    const page = req.url.searchParams.get('page') || '1';
    const limit = req.url.searchParams.get('limit') || '20';
    const search = req.url.searchParams.get('search');

    let projects = [
      {
        id: 'project-1',
        name: 'E-commerce Platform',
        description: 'A modern e-commerce platform built with React and Node.js',
        ownerId: 'user-1',
        ownerName: 'Test User',
        memberCount: 3,
        repositoryCount: 2,
        status: 'active',
        visibility: 'private',
        createdAt: '2024-01-01T10:00:00Z',
        lastActivity: '2024-01-15T14:30:00Z'
      },
      {
        id: 'project-2',
        name: 'Task Management App',
        description: 'A collaborative task management application',
        ownerId: 'user-1',
        ownerName: 'Test User',
        memberCount: 2,
        repositoryCount: 1,
        status: 'active',
        visibility: 'private',
        createdAt: '2024-01-05T10:00:00Z',
        lastActivity: '2024-01-14T16:20:00Z'
      }
    ];

    if (search) {
      projects = projects.filter(project =>
        project.name.toLowerCase().includes(search.toLowerCase()) ||
        project.description.toLowerCase().includes(search.toLowerCase())
      );
    }

    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          items: projects,
          pagination: {
            page: parseInt(page),
            limit: parseInt(limit),
            total: projects.length,
            pages: Math.ceil(projects.length / parseInt(limit)),
            hasNext: false,
            hasPrev: false
          }
        }
      })
    );
  }),

  rest.post(`${API_URL}/api/projects`, (req, res, ctx) => {
    return res(
      ctx.status(201),
      ctx.json({
        success: true,
        data: {
          project: {
            id: 'project-new',
            name: 'New Project',
            description: 'A newly created project',
            ownerId: 'user-1',
            ownerName: 'Test User',
            memberCount: 1,
            repositoryCount: 0,
            status: 'draft',
            visibility: 'private',
            createdAt: new Date().toISOString(),
            lastActivity: new Date().toISOString()
          }
        }
      })
    );
  }),

  rest.get(`${API_URL}/api/projects/:id`, (req, res, ctx) => {
    const { id } = req.params;
    
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          project: {
            id,
            name: 'E-commerce Platform',
            description: 'A modern e-commerce platform built with React and Node.js',
            ownerId: 'user-1',
            ownerName: 'Test User',
            memberCount: 3,
            repositoryCount: 2,
            status: 'active',
            visibility: 'private',
            createdAt: '2024-01-01T10:00:00Z',
            lastActivity: '2024-01-15T14:30:00Z',
            members: [
              {
                id: 'user-1',
                name: 'Test User',
                email: 'test@example.com',
                role: 'owner',
                joinedAt: '2024-01-01T10:00:00Z'
              }
            ],
            repositories: [
              {
                id: 'repo-1',
                name: 'ecommerce-frontend',
                url: 'https://github.com/user/ecommerce-frontend',
                provider: 'github',
                branch: 'main',
                isConnected: true,
                lastSync: '2024-01-15T14:00:00Z'
              }
            ]
          }
        }
      })
    );
  }),

  // Deployments endpoints
  rest.get(`${API_URL}/api/deployments`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          items: [
            {
              id: 'deploy-1',
              repositoryId: 'repo-1',
              repositoryName: 'ecommerce-frontend',
              projectId: 'project-1',
              projectName: 'E-commerce Platform',
              branch: 'main',
              commitHash: 'a1b2c3d',
              commitMessage: 'Add shopping cart functionality',
              status: 'success',
              environment: 'production',
              url: 'https://ecommerce-frontend-abc123.vercel.app',
              buildDuration: 180,
              createdAt: '2024-01-15T14:00:00Z',
              completedAt: '2024-01-15T14:03:00Z'
            },
            {
              id: 'deploy-2',
              repositoryId: 'repo-2',
              repositoryName: 'ecommerce-backend',
              projectId: 'project-1',
              projectName: 'E-commerce Platform',
              branch: 'main',
              commitHash: 'b2c3d4e',
              commitMessage: 'Update API endpoints',
              status: 'building',
              environment: 'staging',
              url: null,
              buildDuration: null,
              createdAt: '2024-01-15T15:00:00Z',
              completedAt: null
            }
          ],
          pagination: {
            page: 1,
            limit: 20,
            total: 2,
            pages: 1,
            hasNext: false,
            hasPrev: false
          }
        }
      })
    );
  }),

  rest.get(`${API_URL}/api/deployments/:id/logs`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          logs: [
            {
              timestamp: '2024-01-15T14:00:00Z',
              level: 'info',
              message: 'Starting build process'
            },
            {
              timestamp: '2024-01-15T14:01:30Z',
              level: 'info',
              message: 'Installing dependencies'
            },
            {
              timestamp: '2024-01-15T14:02:45Z',
              level: 'info',
              message: 'Build completed successfully'
            }
          ]
        }
      })
    );
  }),

  // Activity endpoints
  rest.get(`${API_URL}/api/activity`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          items: [
            {
              id: 'activity-1',
              type: 'commit',
              message: 'Test User pushed 3 commits to ecommerce-frontend',
              userId: 'user-1',
              userName: 'Test User',
              projectId: 'project-1',
              projectName: 'E-commerce Platform',
              createdAt: '2024-01-15T14:00:00Z'
            }
          ],
          pagination: {
            page: 1,
            limit: 20,
            total: 1,
            pages: 1,
            hasNext: false,
            hasPrev: false
          }
        }
      })
    );
  }),

  // Analytics endpoints
  rest.get(`${API_URL}/api/analytics/dashboard`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          stats: {
            totalProjects: 5,
            activeProjects: 3,
            totalDeployments: 25,
            successfulDeployments: 23,
            teamMembers: 8,
            activeNow: 3
          },
          deploymentStats: {
            total: 25,
            successful: 23,
            failed: 2,
            inProgress: 0,
            successRate: 92
          }
        }
      })
    );
  }),

  // Team presence endpoints
  rest.get(`${API_URL}/api/team/presence`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          members: [
            {
              id: 'user-1',
              name: 'Test User',
              email: 'test@example.com',
              status: 'online',
              lastSeen: '2024-01-16T10:00:00Z',
              currentProject: {
                id: 'project-1',
                name: 'E-commerce Platform'
              }
            }
          ]
        }
      })
    );
  }),

  // Collaboration suggestions endpoints
  rest.get(`${API_URL}/api/collaboration/suggestions`, (req, res, ctx) => {
    return res(
      ctx.status(200),
      ctx.json({
        success: true,
        data: {
          suggestions: [
            {
              id: 'suggestion-1',
              type: 'skill_match',
              title: 'Connect with React Expert',
              description: 'Jane Smith has extensive React experience and is working on a similar component',
              targetUser: {
                id: 'user-2',
                name: 'Jane Smith',
                skills: ['React', 'TypeScript', 'UI/UX']
              },
              createdAt: '2024-01-16T09:00:00Z'
            }
          ]
        }
      })
    );
  }),

  // Error handlers
  rest.get(`${API_URL}/api/*`, (req, res, ctx) => {
    return res(
      ctx.status(404),
      ctx.json({
        success: false,
        error: {
          code: 'NOT_FOUND',
          message: 'Endpoint not found'
        }
      })
    );
  }),

  rest.post(`${API_URL}/api/*`, (req, res, ctx) => {
    return res(
      ctx.status(404),
      ctx.json({
        success: false,
        error: {
          code: 'NOT_FOUND',
          message: 'Endpoint not found'
        }
      })
    );
  })
];