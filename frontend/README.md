# Ticolops Frontend

React TypeScript frontend for the Ticolops student collaboration platform.

## Features

- **Authentication**: Login and registration with JWT tokens
- **Real-time Dashboard**: Live activity tracking and team presence
- **Project Management**: Create and manage student projects
- **Repository Integration**: Connect GitHub/GitLab repositories
- **Deployment Monitoring**: Track automated deployments
- **Team Collaboration**: Real-time notifications and activity feeds

## Tech Stack

- **React 19** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS** for styling
- **React Router** for navigation
- **TanStack Query** for data fetching
- **Socket.io** for real-time communication
- **Axios** for HTTP requests
- **Vitest** for testing

## Getting Started

1. Install dependencies:
   ```bash
   npm install
   ```

2. Copy environment variables:
   ```bash
   cp .env.example .env
   ```

3. Start development server:
   ```bash
   npm run dev
   ```

4. Build for production:
   ```bash
   npm run build
   ```

5. Run tests:
   ```bash
   npm run test
   ```

## Project Structure

```
src/
├── components/          # Reusable UI components
│   ├── ui/             # Base UI components (Button, Input, etc.)
│   ├── auth/           # Authentication components
│   └── layout/         # Layout components (Header, Sidebar)
├── contexts/           # React contexts (Auth, etc.)
├── pages/              # Page components
├── services/           # API services
├── lib/                # Utility functions
└── test/               # Test setup and utilities
```

## Environment Variables

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)
- `VITE_WS_URL`: WebSocket URL (default: ws://localhost:8000)

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run test` - Run tests
- `npm run test:run` - Run tests once
- `npm run lint` - Run ESLint