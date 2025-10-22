# Specification: [Component/Feature Name]

**Status:** [Draft | In Review | Approved | Implemented]
**Version:** X.Y.Z
**Author:** [Name/Team]
**Date:** YYYY-MM-DD
**Last Updated:** YYYY-MM-DD

## Overview

[Brief summary of what this specification covers and its purpose]

**Scope:** [What is included in this specification]

**Audience:** [Who should read/implement this - developers, AI agents, etc.]

## Related Documents

- Requirements: [link to requirements/]
- Design: [link to design/]
- Architecture: [link to architecture/]

---

## API Specification

### Endpoints

#### `[METHOD] /api/resource`

**Description:** [What this endpoint does]

**Authentication:** [Required | Not Required | OAuth | API Key]

**Request:**

**Headers:**
```
Content-Type: application/json
Authorization: Bearer {token}
[Other headers]
```

**Path Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | [Description] |

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `limit` | integer | No | 10 | [Description] |
| `offset` | integer | No | 0 | [Description] |

**Request Body:**
```json
{
  "field1": "string",
  "field2": 123,
  "nested": {
    "subfield": "value"
  }
}
```

**Request Schema:**
```typescript
interface RequestBody {
  field1: string;           // Description
  field2: number;           // Description
  nested: {
    subfield: string;       // Description
  };
}
```

**Response:**

**Success (200 OK):**
```json
{
  "id": "uuid",
  "field1": "string",
  "field2": 123,
  "createdAt": "2025-01-01T00:00:00Z"
}
```

**Response Schema:**
```typescript
interface SuccessResponse {
  id: string;               // Unique identifier
  field1: string;           // Description
  field2: number;           // Description
  createdAt: string;        // ISO 8601 timestamp
}
```

**Error Responses:**

**400 Bad Request:**
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Validation failed",
    "details": [
      {
        "field": "field1",
        "issue": "Required field missing"
      }
    ]
  }
}
```

**401 Unauthorized:**
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or missing authentication token"
  }
}
```

**404 Not Found:**
```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found"
  }
}
```

**500 Internal Server Error:**
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred"
  }
}
```

**Example Usage:**

**cURL:**
```bash
curl -X POST https://api.example.com/api/resource \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "field1": "value",
    "field2": 123
  }'
```

**JavaScript/TypeScript:**
```typescript
const response = await fetch('https://api.example.com/api/resource', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    field1: 'value',
    field2: 123
  })
});

const data = await response.json();
```

**Python:**
```python
import requests

response = requests.post(
    'https://api.example.com/api/resource',
    headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    },
    json={
        'field1': 'value',
        'field2': 123
    }
)

data = response.json()
```

---

## Data Models

### [Model Name]

**Description:** [What this model represents]

**Schema:**

```typescript
interface ModelName {
  id: string;                    // Unique identifier (UUID v4)
  field1: string;                // Description, constraints
  field2: number;                // Description, range: 0-100
  field3: string | null;         // Optional field
  status: 'active' | 'inactive'; // Enum values
  metadata: Record<string, any>; // Flexible metadata object
  createdAt: Date;               // ISO 8601 timestamp
  updatedAt: Date;               // ISO 8601 timestamp
}
```

**JSON Schema:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["id", "field1", "field2", "status"],
  "properties": {
    "id": {
      "type": "string",
      "format": "uuid"
    },
    "field1": {
      "type": "string",
      "minLength": 1,
      "maxLength": 255
    },
    "field2": {
      "type": "number",
      "minimum": 0,
      "maximum": 100
    },
    "field3": {
      "type": ["string", "null"]
    },
    "status": {
      "type": "string",
      "enum": ["active", "inactive"]
    },
    "metadata": {
      "type": "object"
    },
    "createdAt": {
      "type": "string",
      "format": "date-time"
    },
    "updatedAt": {
      "type": "string",
      "format": "date-time"
    }
  }
}
```

**Database Schema (SQL):**
```sql
CREATE TABLE model_name (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    field1 VARCHAR(255) NOT NULL,
    field2 INTEGER NOT NULL CHECK (field2 >= 0 AND field2 <= 100),
    field3 VARCHAR(255),
    status VARCHAR(20) NOT NULL CHECK (status IN ('active', 'inactive')),
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_model_name_status ON model_name(status);
CREATE INDEX idx_model_name_created_at ON model_name(created_at);
```

**Validation Rules:**
- `field1`: Required, non-empty string, max 255 characters
- `field2`: Required, integer between 0 and 100 (inclusive)
- `field3`: Optional string
- `status`: Required, must be either "active" or "inactive"
- `metadata`: Optional object with arbitrary key-value pairs

**Example:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "field1": "Example value",
  "field2": 42,
  "field3": null,
  "status": "active",
  "metadata": {
    "source": "api",
    "version": "1.0"
  },
  "createdAt": "2025-01-01T12:00:00Z",
  "updatedAt": "2025-01-01T12:00:00Z"
}
```

---

## Interfaces & Contracts

### [Interface Name]

**Purpose:** [What this interface defines]

**Type Definition:**

```typescript
interface InterfaceName {
  method1(param1: string, param2: number): Promise<ReturnType>;
  method2(options: OptionsType): ReturnType;
}

interface OptionsType {
  option1: string;
  option2?: boolean;
}

interface ReturnType {
  success: boolean;
  data: any;
}
```

**Implementation Requirements:**
- [Requirement 1]
- [Requirement 2]
- [Requirement 3]

**Behavior Contracts:**
- **method1:** [Detailed behavior description]
  - Input validation: [What to validate]
  - Side effects: [Any side effects]
  - Error handling: [How errors should be handled]
  - Return value: [What should be returned]

- **method2:** [Detailed behavior description]
  - Input validation: [What to validate]
  - Side effects: [Any side effects]
  - Error handling: [How errors should be handled]
  - Return value: [What should be returned]

**Example Implementation:**

```typescript
class ConcreteImplementation implements InterfaceName {
  async method1(param1: string, param2: number): Promise<ReturnType> {
    // Validate inputs
    if (!param1 || param2 < 0) {
      throw new Error('Invalid parameters');
    }

    // Implementation logic
    const result = await someOperation(param1, param2);

    return {
      success: true,
      data: result
    };
  }

  method2(options: OptionsType): ReturnType {
    // Implementation
  }
}
```

---

## Business Logic Rules

### [Rule Name]

**Description:** [What this rule governs]

**Conditions:**
```
IF [condition1] AND [condition2]
THEN [action]
ELSE IF [condition3]
THEN [alternative action]
ELSE [default action]
```

**Implementation:**

```typescript
function applyRule(input: InputType): OutputType {
  if (condition1 && condition2) {
    return action();
  } else if (condition3) {
    return alternativeAction();
  } else {
    return defaultAction();
  }
}
```

**Examples:**

**Scenario 1:** [Description]
- Input: `[input values]`
- Expected Output: `[output values]`
- Explanation: [Why this output]

**Scenario 2:** [Description]
- Input: `[input values]`
- Expected Output: `[output values]`
- Explanation: [Why this output]

---

## State Machines

### [State Machine Name]

**Description:** [What this state machine models]

**States:**
- `STATE_1`: [Description]
- `STATE_2`: [Description]
- `STATE_3`: [Description]

**Transitions:**

```
STATE_1 --[event1]--> STATE_2
STATE_2 --[event2]--> STATE_3
STATE_2 --[event3]--> STATE_1
STATE_3 --[event4]--> STATE_1
```

**Transition Rules:**

| From State | Event | To State | Conditions | Side Effects |
|------------|-------|----------|------------|--------------|
| STATE_1 | event1 | STATE_2 | [condition] | [side effect] |
| STATE_2 | event2 | STATE_3 | [condition] | [side effect] |
| STATE_2 | event3 | STATE_1 | [condition] | [side effect] |

**Diagram:**
```
     ┌─────────┐
     │ STATE_1 │◄───┐
     └────┬────┘    │
          │         │
      event1    event3/event4
          │         │
          ▼         │
     ┌─────────┐    │
     │ STATE_2 │    │
     └────┬────┘    │
          │         │
      event2        │
          │         │
          ▼         │
     ┌─────────┐    │
     │ STATE_3 │────┘
     └─────────┘
```

**Implementation:**

```typescript
type State = 'STATE_1' | 'STATE_2' | 'STATE_3';
type Event = 'event1' | 'event2' | 'event3' | 'event4';

class StateMachine {
  private state: State = 'STATE_1';

  transition(event: Event): void {
    const transitions: Record<State, Partial<Record<Event, State>>> = {
      STATE_1: { event1: 'STATE_2' },
      STATE_2: { event2: 'STATE_3', event3: 'STATE_1' },
      STATE_3: { event4: 'STATE_1' }
    };

    const nextState = transitions[this.state][event];
    if (nextState) {
      this.state = nextState;
      // Execute side effects
    } else {
      throw new Error(`Invalid transition: ${event} from ${this.state}`);
    }
  }

  getState(): State {
    return this.state;
  }
}
```

---

## Error Handling

### Error Codes

| Code | HTTP Status | Description | Recovery Action |
|------|-------------|-------------|-----------------|
| `ERROR_CODE_1` | 400 | [Description] | [How to recover] |
| `ERROR_CODE_2` | 404 | [Description] | [How to recover] |
| `ERROR_CODE_3` | 500 | [Description] | [How to recover] |

### Error Response Format

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {
      "field": "Additional context"
    },
    "requestId": "uuid",
    "timestamp": "2025-01-01T00:00:00Z"
  }
}
```

---

## Performance Requirements

### Response Time
- **API endpoints:** < 200ms (p95), < 500ms (p99)
- **Database queries:** < 50ms (p95), < 100ms (p99)
- **Batch operations:** < 5s for 1000 items

### Throughput
- **Requests per second:** 1000 RPS sustained, 5000 RPS peak
- **Concurrent connections:** 10,000

### Resource Limits
- **Memory:** < 512 MB per instance
- **CPU:** < 50% utilization at normal load
- **Database connections:** Max 100 per instance

---

## Security Specifications

### Authentication
- Method: [OAuth 2.0 | JWT | API Key]
- Token lifetime: [duration]
- Refresh mechanism: [description]

### Authorization
- Model: [RBAC | ABAC | ACL]
- Permissions: [list of permissions]
- Role definitions: [role descriptions]

### Data Security
- Encryption at rest: [AES-256 | other]
- Encryption in transit: [TLS 1.3 | other]
- PII handling: [requirements]
- Data retention: [policies]

### Input Validation
- Sanitization: [rules]
- Validation: [rules]
- Rate limiting: [limits]

---

## Testing Specifications

### Unit Test Requirements

**Coverage:** Minimum 80% line coverage

**Test Cases:**

```typescript
describe('ComponentName', () => {
  it('should handle valid input', () => {
    // Test specification
  });

  it('should reject invalid input', () => {
    // Test specification
  });

  it('should handle edge case', () => {
    // Test specification
  });
});
```

### Integration Test Scenarios

1. **Scenario 1:** [Description]
   - Setup: [Initial state]
   - Actions: [Steps to perform]
   - Expected: [Expected outcome]

2. **Scenario 2:** [Description]
   - Setup: [Initial state]
   - Actions: [Steps to perform]
   - Expected: [Expected outcome]

### Performance Test Criteria

- Load test: [specifications]
- Stress test: [specifications]
- Endurance test: [specifications]

---

## Implementation Checklist

- [ ] Implement data models with validation
- [ ] Implement API endpoints per specification
- [ ] Implement error handling
- [ ] Add input validation and sanitization
- [ ] Implement authentication/authorization
- [ ] Add logging and monitoring
- [ ] Write unit tests (>80% coverage)
- [ ] Write integration tests
- [ ] Perform security review
- [ ] Conduct performance testing
- [ ] Update API documentation
- [ ] Review against specification

---

## Changelog

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | YYYY-MM-DD | Initial specification | [Name] |
| 1.1.0 | YYYY-MM-DD | Added error codes | [Name] |

---

## Appendix

### Glossary
- **[Term 1]:** [Definition]
- **[Term 2]:** [Definition]

### References
- [External specification]
- [RFC or standard]
- [Related documentation]
