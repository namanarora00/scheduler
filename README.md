# SimpliSmart Deployment Manager

A smart deployment management system that handles resource allocation and scheduling across multiple clusters with priority-based preemption.

## System Architecture

```mermaid
graph TD
    A[Client] --> B[Flask API Server]
    B --> C[Redis Queue]
    C --> D[Worker]
    D --> E[Scheduler]
    E --> F[Database]
    B --> F
    E --> G[Redis Lock]

    style A fill:#f9f,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style C fill:#dfd,stroke:#333,stroke-width:2px
    style D fill:#fdd,stroke:#333,stroke-width:2px
    style E fill:#ddf,stroke:#333,stroke-width:2px
    style F fill:#ffd,stroke:#333,stroke-width:2px
    style G fill:#dfd,stroke:#333,stroke-width:2px
```

## Deployment Workflow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Queue
    participant Worker
    participant Scheduler
    participant DB

    Client->>API: Create Deployment
    API->>DB: Save Deployment (PENDING)
    API->>Queue: Enqueue Deployment
    API->>Client: Return Deployment ID
    
    Queue->>Worker: Process Deployment
    Worker->>Scheduler: Try Schedule
    
    alt Can Schedule Directly
        Scheduler->>DB: Update Status (RUNNING)
    else Needs Preemption
        Scheduler->>DB: Preempt Lower Priority
        Scheduler->>DB: Update New Status (RUNNING)
        Scheduler->>Queue: Re-queue Preempted
    else Cannot Schedule
        Scheduler->>Queue: Re-queue with Delay
    end
```

## Features

- **Multi-Cluster Support**: Manage deployments across multiple clusters
- **Priority-Based Scheduling**: Higher priority deployments can preempt lower priority ones
- **Resource Management**: Efficient allocation of CPU, RAM, and GPU resources
- **Role-Based Access Control**: Admin and Developer roles with different permissions
- **Queue Management**: Redis-based queuing system with automatic retries
- **Distributed Locking**: Prevent race conditions in scheduling decisions

## Components

### API Server
- Flask-based REST API
- JWT Authentication
- Role-based access control
- Database operations via SQLAlchemy

### Scheduler
- Resource allocation algorithms
- Priority-based preemption
- Distributed locking with Redis
- Transaction management

### Worker
- Processes deployment requests from queue
- Handles scheduling attempts
- Automatic retries with delays
- Error handling and logging

### Queue Service
- Redis-based job queue
- Job status tracking
- Delayed job processing
- Multiple worker support

## API Documentation

### Authentication

#### Login
```bash
curl -X POST http://localhost:6000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@test.com",
    "password": "admin123"
  }'
```

#### Register
```bash
curl -X POST http://localhost:6000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@test.com",
    "password": "password123",
    "invite_code": "INVITE_CODE"
  }'
```

### Invites

#### Create Invite (Admin Only)
```bash
curl -X POST http://localhost:6000/invites/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@test.com",
    "role": "dev"
  }'
```

### Deployments

#### Create Deployment
```bash
curl -X POST http://localhost:6000/deployments/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-deployment",
    "cluster_id": 1,
    "ram": 4,
    "cpu": 2,
    "gpu": 0,
    "priority": 3
  }'
```

#### List Deployments
```bash
curl -X GET http://localhost:6000/deployments/ \
  -H "Authorization: Bearer TOKEN"
```

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Initialize database and test data:
```bash
python -c "from app.utils.init_test_data import init_test_data; init_test_data()"
```

4. Start services:
```bash
docker-compose up
```

## Development

### Database Models
- `Organisation`: Represents an organization
- `User`: User accounts with roles
- `Cluster`: Resource clusters with capacity
- `Deployment`: Deployment requests with resources and priority
- `InviteCode`: Invitation system for new users

### Key Services
- `DeploymentService`: Manages deployment lifecycle
- `SchedulerService`: Handles resource allocation
- `QueueService`: Manages job queue
- `AuthService`: Handles authentication
- `InviteService`: Manages invite system

## Testing

Run the test suite:
```bash
python -m pytest tests/
```

## Environment Variables

- `JWT_SECRET_KEY`: Secret key for JWT tokens
- `FLASK_APP`: Flask application entry point
- `FLASK_ENV`: Environment (development/production)
- `REDIS_HOST`: Redis server hostname
- `REDIS_PORT`: Redis server port
- `DATABASE_PATH`: SQLite database path

## Deployment Priority Levels

1. `LOWEST` (1): Lowest priority, first to be preempted
2. `LOW` (2): Low priority deployments
3. `MEDIUM` (3): Default priority level
4. `HIGH` (4): High priority deployments
5. `HIGHEST` (5): Highest priority, can preempt others

## Error Handling

The system uses custom exceptions:
- `ValidationError`: Input validation errors
- `AuthenticationError`: Authentication failures
- `AuthorizationError`: Permission issues
- `ServiceException`: General service errors

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License
