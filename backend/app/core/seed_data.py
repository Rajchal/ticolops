"""Seed data for default build configurations and deployment settings."""

from app.models.deployment import BuildConfiguration, ProjectType


DEFAULT_BUILD_CONFIGURATIONS = [
    {
        "project_type": ProjectType.REACT,
        "name": "React Application",
        "description": "Standard React application built with Create React App",
        "build_command": "npm run build",
        "output_directory": "build",
        "install_command": "npm install",
        "detection_files": ["package.json", "src/App.js", "src/App.jsx", "src/App.tsx", "public/index.html"],
        "detection_patterns": {
            "dependencies": ["react", "react-dom"],
            "scripts": ["start", "build", "test"]
        },
        "default_env_vars": {
            "NODE_ENV": "production",
            "GENERATE_SOURCEMAP": "false"
        },
        "node_version": "18"
    },
    {
        "project_type": ProjectType.NEXTJS,
        "name": "Next.js Application",
        "description": "Next.js React framework application",
        "build_command": "npm run build",
        "output_directory": ".next",
        "install_command": "npm install",
        "detection_files": ["package.json", "next.config.js", "pages/index.js", "app/page.js"],
        "detection_patterns": {
            "dependencies": ["next", "react"],
            "scripts": ["dev", "build", "start"]
        },
        "default_env_vars": {
            "NODE_ENV": "production"
        },
        "node_version": "18"
    },
    {
        "project_type": ProjectType.VUE,
        "name": "Vue.js Application",
        "description": "Vue.js application built with Vue CLI or Vite",
        "build_command": "npm run build",
        "output_directory": "dist",
        "install_command": "npm install",
        "detection_files": ["package.json", "src/App.vue", "vue.config.js", "vite.config.js"],
        "detection_patterns": {
            "dependencies": ["vue"],
            "scripts": ["serve", "build"]
        },
        "default_env_vars": {
            "NODE_ENV": "production"
        },
        "node_version": "18"
    },
    {
        "project_type": ProjectType.ANGULAR,
        "name": "Angular Application",
        "description": "Angular application built with Angular CLI",
        "build_command": "npm run build",
        "output_directory": "dist",
        "install_command": "npm install",
        "detection_files": ["package.json", "angular.json", "src/app/app.component.ts"],
        "detection_patterns": {
            "dependencies": ["@angular/core", "@angular/cli"],
            "scripts": ["ng", "start", "build"]
        },
        "default_env_vars": {
            "NODE_ENV": "production"
        },
        "node_version": "18"
    },
    {
        "project_type": ProjectType.NODE,
        "name": "Node.js Application",
        "description": "Node.js server application",
        "build_command": "npm install",
        "output_directory": ".",
        "install_command": "npm install",
        "detection_files": ["package.json", "server.js", "app.js", "index.js"],
        "detection_patterns": {
            "dependencies": ["express", "fastify", "koa", "hapi"],
            "scripts": ["start"]
        },
        "default_env_vars": {
            "NODE_ENV": "production",
            "PORT": "3000"
        },
        "node_version": "18"
    },
    {
        "project_type": ProjectType.PYTHON,
        "name": "Python Application",
        "description": "Generic Python application",
        "build_command": "pip install -r requirements.txt",
        "output_directory": ".",
        "install_command": "pip install -r requirements.txt",
        "detection_files": ["requirements.txt", "setup.py", "pyproject.toml", "main.py"],
        "detection_patterns": {},
        "default_env_vars": {
            "PYTHONPATH": ".",
            "PYTHONUNBUFFERED": "1"
        },
        "python_version": "3.11"
    },
    {
        "project_type": ProjectType.DJANGO,
        "name": "Django Application",
        "description": "Django web framework application",
        "build_command": "pip install -r requirements.txt && python manage.py collectstatic --noinput",
        "output_directory": "staticfiles",
        "install_command": "pip install -r requirements.txt",
        "detection_files": ["requirements.txt", "manage.py", "settings.py"],
        "detection_patterns": {
            "requirements": ["django"]
        },
        "default_env_vars": {
            "DJANGO_SETTINGS_MODULE": "settings",
            "PYTHONPATH": ".",
            "PYTHONUNBUFFERED": "1"
        },
        "python_version": "3.11"
    },
    {
        "project_type": ProjectType.FLASK,
        "name": "Flask Application",
        "description": "Flask web framework application",
        "build_command": "pip install -r requirements.txt",
        "output_directory": ".",
        "install_command": "pip install -r requirements.txt",
        "detection_files": ["requirements.txt", "app.py", "wsgi.py"],
        "detection_patterns": {
            "requirements": ["flask"]
        },
        "default_env_vars": {
            "FLASK_ENV": "production",
            "PYTHONPATH": ".",
            "PYTHONUNBUFFERED": "1"
        },
        "python_version": "3.11"
    },
    {
        "project_type": ProjectType.FASTAPI,
        "name": "FastAPI Application",
        "description": "FastAPI web framework application",
        "build_command": "pip install -r requirements.txt",
        "output_directory": ".",
        "install_command": "pip install -r requirements.txt",
        "detection_files": ["requirements.txt", "main.py", "app.py"],
        "detection_patterns": {
            "requirements": ["fastapi", "uvicorn"]
        },
        "default_env_vars": {
            "PYTHONPATH": ".",
            "PYTHONUNBUFFERED": "1"
        },
        "python_version": "3.11"
    },
    {
        "project_type": ProjectType.STATIC,
        "name": "Static Website",
        "description": "Static HTML/CSS/JavaScript website",
        "build_command": "",
        "output_directory": ".",
        "install_command": "",
        "detection_files": ["index.html", "style.css", "script.js"],
        "detection_patterns": {},
        "default_env_vars": {}
    }
]


async def seed_build_configurations(db_session):
    """Seed default build configurations into the database."""
    from sqlalchemy import select
    
    for config_data in DEFAULT_BUILD_CONFIGURATIONS:
        # Check if configuration already exists
        query = select(BuildConfiguration).where(
            BuildConfiguration.project_type == config_data["project_type"],
            BuildConfiguration.name == config_data["name"]
        )
        result = await db_session.execute(query)
        existing_config = result.scalar_one_or_none()
        
        if not existing_config:
            # Create new configuration
            config = BuildConfiguration(**config_data)
            db_session.add(config)
    
    await db_session.commit()
    print(f"Seeded {len(DEFAULT_BUILD_CONFIGURATIONS)} build configurations")