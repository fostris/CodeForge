```markdown
# Kanban Board Task Planner Specification

## Feature: Kanban Board Task Scheduler

### Goal

Build a web-based Kanban board task scheduler that allows users to create, organize, and manage tasks across customizable columns (e.g., To Do, In Progress, Done). The system should provide drag-and-drop functionality, real-time updates, and persistent storage with user authentication.

---

### Scope

#### IN (Features to Implement)

- **User Authentication**
  - User registration (email, password)
  - User login with JWT tokens
  - Password hashing with bcrypt
  - Token-based session management

- **Board Management**
  - Create multiple Kanban boards per user
  - Rename and delete boards
  - List all boards for a user
  - Board sharing via invite link (read-only access)

- **Column Management**
  - Create custom columns (e.g., Backlog, In Progress, Review, Done)
  - Rename columns
  - Reorder columns via drag-and-drop
  - Delete columns (with task migration prompt)
  - WIP (Work In Progress) limits per column

- **Task Management**
  - Create tasks with title, description, priority, due date, and labels
  - Edit task details inline and via modal
  - Delete tasks with confirmation
  - Move tasks between columns via drag-and-drop
  - Reorder tasks within a column
  - Task priority levels: Low, Medium, High, Critical
  - Task labels with customizable colors

- **User Experience**
  - Drag-and-drop interface for tasks and columns
  - Real-time visual feedback during drag operations
  - Task filtering by label, priority, or due date
  - Task search by title or description
  - Dark/Light theme toggle
  - Responsive design (desktop, tablet, mobile)

- **Data Persistence**
  - PostgreSQL database storage
  - RESTful API for all operations
  - Optimistic UI updates with rollback on failure

- **Notifications**
  - Due date reminders (in-app notification badge)
  - Overdue task highlighting

---

#### OUT (Future Phases)

- OAuth social login (Google, GitHub)
- Real-time collaboration (WebSocket sync between users)
- Task comments and attachments
- Task dependencies (blocking/blocked by)
- Time tracking and reporting
- Email notifications
- Mobile native applications
- Board templates
- Keyboard shortcuts
- Bulk task operations
- Export to CSV/JSON/Excel
- Slack/Discord integration
- GitHub/Jira integration

---

### Constraints

#### Stack

- **Frontend**: React 18+ with TypeScript
- **State Management**: Zustand or Redux Toolkit
- **UI Components**: Tailwind CSS + Headless UI
- **Drag-and-Drop**: @dnd-kit/core
- **HTTP Client**: Axios or Fetch API
- **Backend**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 14+
- **ORM**: SQLAlchemy 2.0+ with async support
- **Validation**: Pydantic v2
- **Authentication**: JWT (PyJWT) with access/refresh tokens
- **Password Hashing**: bcrypt (cost=12)
- **Migration Tool**: Alembic

#### Performance

- Initial page load: <2 seconds
- API response time (single operation): <200ms
- Drag-and-drop feedback latency: <50ms
- Board with 100+ tasks: smooth scrolling at 60fps
- Database query optimization: indexed columns, pagination

#### Security

- Passwords hashed with bcrypt (cost=12)
- JWT access tokens: 15-minute expiration
- JWT refresh tokens: 7-day expiration, stored in httpOnly cookie
- CORS policy: strict origin validation
- Input sanitization on all endpoints
- Rate limiting: 100 requests/minute per user
- HTTPS only in production
- CSRF protection enabled
- No sensitive data in JWT payload

#### Browser Support

- Chrome/Edge 90+
- Firefox 90+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Android)

---

### Acceptance Criteria

#### Authentication
- [ ] User can register with email and password (min 8 characters)
- [ ] User can login with valid credentials and receive JWT tokens
- [ ] Invalid credentials return 401 Unauthorized
- [ ] Duplicate email registration returns 409 Conflict
- [ ] Logout invalidates refresh token

#### Board Management
- [ ] Authenticated user can create a new board with a name
- [ ] User can view list of their boards on dashboard
- [ ] User can rename an existing board
- [ ] User can delete a board (cascade deletes columns and tasks)
- [ ] User cannot access another user's private boards

#### Column Management
- [ ] User can create a new column on a board
- [ ] Default board has 3 columns: To Do, In Progress, Done
- [ ] User can rename a column
- [ ] User can reorder columns via drag-and-drop
- [ ] User can delete a column (prompts to migrate or delete tasks)
- [ ] User can set WIP limit on a column
- [ ] Column shows warning when WIP limit exceeded

#### Task Management
- [ ] User can create a task with title (required), description, priority, due date, labels
- [ ] Task is created in the selected column
- [ ] User can edit task details via modal
- [ ] User can delete a task with confirmation dialog
- [ ] User can drag task to different column
- [ ] User can reorder tasks within the same column
- [ ] Task displays priority badge with color coding
- [ ] Task card shows due date and labels
- [ ] Overdue tasks have visual indicator (red border/icon)

#### Search and Filtering
- [ ] User can search tasks by title substring
- [ ] User can filter tasks by label
- [ ] User can filter tasks by priority level
- [ ] User can filter tasks by due date range
- [ ] Filters can be combined
- [ ] Clear filters button resets view

#### UI/UX
- [ ] Dark/Light theme toggle persists across sessions
- [ ] Responsive layout adapts to screen sizes
- [ ] Loading states shown during API calls
- [ ] Error messages displayed for failed operations
- [ ] Optimistic updates with rollback on failure

#### Testing
- [ ] All API endpoints have unit tests
- [ ] Frontend components have unit tests
- [ ] Drag-and-drop functionality has integration tests
- [ ] Test coverage: 80%+

---

### Open Questions

1. **Board visibility**: Should boards be private by default or public? (Recommendation: Private)
2. **WIP limit behavior**: Should exceeding WIP limit prevent adding tasks or just warn? (Recommendation: Warn only)
3. **Default columns**: Should we include a "Backlog" column or keep minimal 3-column setup?
4. **Task duplication**: Should users be able to duplicate tasks across boards?
5. **Undo/Redo**: Should we implement undo for drag-and-drop operations?
6. **Offline support**: Should we support offline mode with local storage?
7. **Guest mode**: Should unauthenticated users be able to create a temporary board?

---

### Architecture Decisions

- **JWT over sessions**: Stateless authentication scales better and works well with SPA
- **Optimistic UI updates**: Provides immediate feedback, improves perceived performance
- **Drag-and-drop library**: @dnd-kit offers accessibility support and modularity
- **Zustand over Redux**: Less boilerplate, built-in TypeScript support, smaller bundle
- **Async database operations**: Non-blocking I/O for better concurrency
- **Tailwind CSS**: Utility-first approach speeds up styling iteration
- **Pydantic for validation**: Automatic JSON schema generation, type safety

---

### Dependencies

#### Existing/Custom
- Database connection pool (from `config.py`)
- JWT utility module (from `src.auth.jwt_utils`)
- Password hashing service (from `src.auth.password`)
- Email validation utility (from `utils.validators`)

#### External Libraries
- React 18
- FastAPI
- SQLAlchemy (async)
- PostgreSQL 14+
- Tailwind CSS
- @dnd-kit/core
- Zustand
- Axios

---

### Data Models

#### User
```
- id: UUID (PK)
- email: String (unique, indexed)
- password_hash: String
- created_at: Timestamp
- updated_at: Timestamp
```

#### Board
```
- id: UUID (PK)
- user_id: UUID (FK -> User)
- name: String
- created_at: Timestamp
- updated_at: Timestamp
```

#### Column
```
- id: UUID (PK)
- board_id: UUID (FK -> Board)
- name: String
- position: Integer
- wip_limit: Integer (nullable)
- created_at: Timestamp
- updated_at: Timestamp
```

#### Task
```
- id: UUID (PK)
- column_id: UUID (FK -> Column)
- title: String
- description: Text (nullable)
- priority: Enum (low, medium, high, critical)
- due_date: Date (nullable)
- position: Integer
- created_at: Timestamp
- updated_at: Timestamp
```

#### Label
```
- id: UUID (PK)
- board_id: UUID (FK -> Board)
- name: String
- color: String (hex)
```

#### TaskLabel (Junction Table)
```
- task_id: UUID (FK -> Task)
- label_id: UUID (FK -> Label)
```

---

### API Endpoints

#### Authentication
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/refresh
POST /api/auth/logout
```

#### Boards
```
GET    /api/boards
POST   /api/boards
GET    /api/boards/{board_id}
PUT    /api/boards/{board_id}
DELETE /api/boards/{board_id}
```

#### Columns
```
GET    /api/boards/{board_id}/columns
POST   /api/boards/{board_id}/columns
PUT    /api/columns/{column_id}
DELETE /api/columns/{column_id}
PATCH  /api/columns/{column_id}/reorder
```

#### Tasks
```
GET    /api/columns/{column_id}/tasks
POST   /api/columns/{column_id}/tasks
GET    /api/tasks/{task_id}
PUT    /api/tasks/{task_id}
DELETE /api/tasks/{task_id}
PATCH  /api/tasks/{task_id}/move
PATCH  /api/tasks/{task_id}/reorder
```

#### Labels
```
GET    /api/boards/{board_id}/labels
POST   /api/boards/{board_id}/labels
PUT    /api/labels/{label_id}
DELETE /api/labels/{label_id}
```

---

### Timeline & Priority

| Phase | Description | Priority | Size | Duration |
|-------|-------------|----------|------|----------|
| 1 | Authentication & User Management | P0 | M | 1 sprint |
| 2 | Board CRUD & Basic Layout | P0 | M | 1 sprint |
| 3 | Column Management | P1 | S | 0.5 sprint |
| 4 | Task CRUD with Basic UI | P0 | L | 1.5 sprints |
| 5 | Drag-and-Drop Functionality | P0 | M | 1 sprint |
| 6 | Search, Filter & Labels | P1 | M | 1 sprint |
| 7 | Polish, Testing & Bug Fixes | P1 | M | 1 sprint |

- **Total Estimated Duration**: 6-7 sprints (12-14 weeks)
- **MVP Scope**: Phases 1-5 (user auth, board, columns, tasks, drag-and-drop)
- **Post-MVP**: Phases 6-7 (filtering, polish, testing)

---

## How This Feeds the Pipeline

After normalization, this spec will be passed to:

1. **Architecture Stage**
   - Design folder structure (frontend: components, hooks, store, api)
   - Design backend structure (routers, models, schemas, services)
   - Define database schema migrations

2. **Decomposition**
   - Break into discrete tasks:
     - T001: User model + database migration
     - T002: JWT authentication service
     - T003: Auth endpoints (register, login, refresh, logout)
     - T004: Board model + CRUD endpoints
     - T005: Column model + CRUD endpoints
     - T006: Task model + CRUD endpoints
     - T007: Label model + CRUD endpoints
     - T008: Frontend auth context + login/register forms
     - T009: Board list dashboard
     - T010: Kanban board layout with columns
     - T011: Task card component
     - T012: Drag-and-drop implementation
     - T013: Search and filter functionality
     - T014: Theme toggle
     - T015: E2E tests

3. **TDD**
   - Write tests for each backend endpoint
   - Write component tests for critical UI elements

4. **Implementation**
   - Generate code per task with test-driven iteration
   - Frontend-first for UI components, backend-first for API

5. **Review**
   - Verify all acceptance criteria are met
   - Performance testing with 100+ tasks
   - Cross-browser testing

---

## Using This Specification

Copy this content to:
```
artifacts/SPEC.md
```

Then run:
```bash
python -m src.cli run --spec artifacts/SPEC.md
```

The pipeline will:
1. Normalize the spec (human review checkpoint)
2. Design the architecture
3. Decompose into tasks
4. Generate tests
5. Implement features
6. Run final review

Each stage has human checkpoints where approval is required before proceeding.
```