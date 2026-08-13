# Real-time Drawing Sharing System

This module provides WebSocket-based real-time drawing functionality for stream monitors, allowing multiple users to collaborate on drawings in real-time.

## Features

- Real-time collaborative drawing
- Multiple drawing tools (line, rectangle, circle, polygon, text, arrow)
- User authentication via JWT
- Session management
- Drawing persistence
- Participant tracking
- Cursor position sharing

## API Endpoints

### Drawing Sessions

#### Get Drawing Sessions

```
GET /api/stream-monitors/drawing/sessions
Query Parameters:
- stream_monitor_id: int (optional) - Filter by stream monitor
```

#### Create Drawing Session

```
POST /api/stream-monitors/drawing/sessions
Headers: Authorization: Bearer <token>
Body: {
  "name": "Session Name",
  "stream_monitor_id": 1
}
```

#### Get Session Detail

```
GET /api/stream-monitors/drawing/sessions/{session_id}
```

#### Update Session

```
PUT /api/stream-monitors/drawing/sessions/{session_id}
Headers: Authorization: Bearer <token>
Body: {
  "name": "Updated Name",
  "is_active": true
}
```

#### Delete Session

```
DELETE /api/stream-monitors/drawing/sessions/{session_id}
Headers: Authorization: Bearer <token>
```

#### Join Session

```
POST /api/stream-monitors/drawing/sessions/{session_id}/join
Headers: Authorization: Bearer <token>
Response: {
  "data": {
    "websocket_url": "/ws/drawing/session/{session_id}/"
  }
}
```

#### Leave Session

```
POST /api/stream-monitors/drawing/sessions/{session_id}/leave
Headers: Authorization: Bearer <token>
```

#### Clear Session Elements

```
POST /api/stream-monitors/drawing/sessions/{session_id}/clear
Headers: Authorization: Bearer <token>
```

### Drawing Elements

#### Create Element

```
POST /api/stream-monitors/drawing/elements
Headers: Authorization: Bearer <token>
Body: {
  "session_id": 1,
  "element_type": "line",
  "data": {
    "points": [[x1, y1], [x2, y2]],
    "color": "#000000",
    "width": 2
  }
}
```

#### Update Element

```
PUT /api/stream-monitors/drawing/elements/{element_id}
Headers: Authorization: Bearer <token>
Body: {
  "data": {
    "points": [[x1, y1], [x2, y2]],
    "color": "#ff0000",
    "width": 3
  }
}
```

#### Delete Element

```
DELETE /api/stream-monitors/drawing/elements/{element_id}
Headers: Authorization: Bearer <token>
```

## WebSocket Connection

### Connection URL

```
ws://localhost:8000/ws/drawing/session/{session_id}/?token={jwt_token}
```

### Message Types

#### Client to Server Messages

**Draw Element**

```json
{
  "type": "draw_element",
  "element_type": "line",
  "element_data": {
    "points": [
      [100, 100],
      [200, 200]
    ],
    "color": "#000000",
    "width": 2
  }
}
```

**Update Element**

```json
{
  "type": "update_element",
  "element_id": 123,
  "element_data": {
    "points": [
      [100, 100],
      [250, 250]
    ],
    "color": "#ff0000",
    "width": 3
  }
}
```

**Delete Element**

```json
{
  "type": "delete_element",
  "element_id": 123
}
```

**Clear All Elements**

```json
{
  "type": "clear_all"
}
```

**Cursor Position**

```json
{
  "type": "cursor_position",
  "cursor_data": {
    "x": 150,
    "y": 200
  }
}
```

#### Server to Client Messages

**Initial State**

```json
{
  "type": "initial_state",
  "elements": [
    {
      "id": 1,
      "type": "line",
      "data": {
        "points": [
          [100, 100],
          [200, 200]
        ]
      },
      "created_by": "username",
      "created_at": "2023-12-01T10:00:00Z"
    }
  ],
  "participants": ["user1", "user2"]
}
```

**Element Added**

```json
{
  "type": "element_added",
  "element": {
    "id": 2,
    "type": "rectangle",
    "data": { "x": 50, "y": 50, "width": 100, "height": 75 },
    "created_by": "username",
    "created_at": "2023-12-01T10:05:00Z"
  }
}
```

**Element Updated**

```json
{
  "type": "element_updated",
  "element_id": 2,
  "element_data": { "x": 60, "y": 60, "width": 120, "height": 85 },
  "updated_by": "username"
}
```

**Element Deleted**

```json
{
  "type": "element_deleted",
  "element_id": 2,
  "deleted_by": "username"
}
```

**Drawing Cleared**

```json
{
  "type": "drawing_cleared",
  "cleared_by": "username"
}
```

**Cursor Position**

```json
{
  "type": "cursor_position",
  "user": "username",
  "cursor_data": { "x": 150, "y": 200 }
}
```

**Participant Joined**

```json
{
  "type": "participant_joined",
  "user": "new_user",
  "participants": ["user1", "user2", "new_user"]
}
```

**Participant Left**

```json
{
  "type": "participant_left",
  "user": "old_user",
  "participants": ["user1", "user2"]
}
```

## Element Types and Data Formats

### Line

```json
{
  "points": [[x1, y1], [x2, y2], ...],
  "color": "#000000",
  "width": 2,
  "opacity": 1.0
}
```

### Rectangle

```json
{
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 150,
  "color": "#000000",
  "fill": "#ffffff",
  "width": 2,
  "opacity": 1.0
}
```

### Circle

```json
{
  "cx": 150,
  "cy": 150,
  "radius": 50,
  "color": "#000000",
  "fill": "#ffffff",
  "width": 2,
  "opacity": 1.0
}
```

### Polygon

```json
{
  "points": [[x1, y1], [x2, y2], [x3, y3], ...],
  "color": "#000000",
  "fill": "#ffffff",
  "width": 2,
  "opacity": 1.0
}
```

### Text

```json
{
  "x": 100,
  "y": 100,
  "text": "Hello World",
  "font_size": 16,
  "font_family": "Arial",
  "color": "#000000",
  "opacity": 1.0
}
```

### Arrow

```json
{
  "start": [x1, y1],
  "end": [x2, y2],
  "color": "#000000",
  "width": 2,
  "arrow_size": 10,
  "opacity": 1.0
}
```

## Frontend Implementation Example

```javascript
class DrawingClient {
  constructor(sessionId, token) {
    this.sessionId = sessionId;
    this.token = token;
    this.ws = null;
    this.elements = [];
    this.participants = [];
  }

  connect() {
    const wsUrl = `ws://localhost:8000/ws/drawing/session/${this.sessionId}/?token=${this.token}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("Connected to drawing session");
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onclose = () => {
      console.log("Disconnected from drawing session");
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }

  handleMessage(data) {
    switch (data.type) {
      case "initial_state":
        this.elements = data.elements;
        this.participants = data.participants;
        this.renderElements();
        break;
      case "element_added":
        this.elements.push(data.element);
        this.renderElement(data.element);
        break;
      case "element_updated":
        const index = this.elements.findIndex((e) => e.id === data.element_id);
        if (index !== -1) {
          this.elements[index].data = data.element_data;
          this.renderElements();
        }
        break;
      case "element_deleted":
        this.elements = this.elements.filter((e) => e.id !== data.element_id);
        this.renderElements();
        break;
      case "drawing_cleared":
        this.elements = [];
        this.renderElements();
        break;
      case "cursor_position":
        this.updateCursor(data.user, data.cursor_data);
        break;
      case "participant_joined":
      case "participant_left":
        this.participants = data.participants;
        this.updateParticipantsList();
        break;
    }
  }

  drawLine(points, color = "#000000", width = 2) {
    const message = {
      type: "draw_element",
      element_type: "line",
      element_data: { points, color, width },
    };
    this.ws.send(JSON.stringify(message));
  }

  drawRectangle(x, y, width, height, color = "#000000", fill = null) {
    const message = {
      type: "draw_element",
      element_type: "rectangle",
      element_data: { x, y, width, height, color, fill },
    };
    this.ws.send(JSON.stringify(message));
  }

  clearAll() {
    const message = { type: "clear_all" };
    this.ws.send(JSON.stringify(message));
  }

  sendCursorPosition(x, y) {
    const message = {
      type: "cursor_position",
      cursor_data: { x, y },
    };
    this.ws.send(JSON.stringify(message));
  }

  renderElements() {
    // Implement canvas/SVG rendering logic here
    // This will depend on your frontend drawing library
  }

  renderElement(element) {
    // Render single element
  }

  updateCursor(username, position) {
    // Update cursor position for user
  }

  updateParticipantsList() {
    // Update UI showing current participants
  }
}

// Usage
const drawingClient = new DrawingClient(sessionId, jwtToken);
drawingClient.connect();
```

## Installation and Setup

1. Install required packages:

```bash
pip install channels==4.0.0 channels-redis==4.2.0
```

2. Run migrations:

```bash
python manage.py makemigrations stream_monitors
python manage.py migrate
```

3. Make sure Redis is running for WebSocket message passing

4. Configure permissions in Django admin for drawing models

## Security Considerations

- JWT authentication is required for WebSocket connections
- Users can only modify their own drawing elements by default
- Session creators have additional permissions (delete session, clear all elements)
- WebSocket connections are validated against allowed hosts
- All drawing data is validated before persistence

## Performance Notes

- Drawing elements are stored in the database for persistence
- Real-time events are sent through Redis channels
- Consider implementing rate limiting for drawing operations
- Large sessions with many elements may require pagination
- Implement cleanup for old, inactive sessions
