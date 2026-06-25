---
name: REST API Design Fundamentals
created_at: '2026-06-12T14:49:58Z'
updated_at: '2026-06-12T14:49:58Z'
version: 1
---

# Knowledge Package: REST API Design Fundamentals

## Core Thesis
REST APIs adhere to a set of conventions that promote consistency, predictability, and ease of use. A primary rule is the use of plural nouns for resource endpoints (e.g., `/users` not `/user`). HTTP methods map directly to CRUD operations, with `GET` for retrieval and `POST` for creation being the most fundamental. Finally, consistent use of standard HTTP status codes is critical for clear communication between the client and server.

## Glossary
| Term | Definition | Related |
|------|-----------|---------|
| REST API | An architectural style for networked applications that uses HTTP requests to access and manipulate data. | HTTP Methods, Status Codes |
| Plural Nouns | A naming convention for API endpoints where the resource name is always in plural form (e.g., `/orders`, `/products`). | Endpoint Design |
| GET | An HTTP method used to retrieve a representation of a resource. It should not have side effects (idempotent). | POST, HTTP Methods |
| POST | An HTTP method used to create a new resource on the server. It is not idempotent. | GET, PUT, HTTP Methods |
| HTTP Status Code | A three-digit code returned by the server to indicate the result of a request (e.g., 200 for success, 404 for not found). | Error Handling, Client-Server Communication |

## Patterns & Heuristics
| Name | Description | When to Use |
|------|------------|-------------|
| Plural Resource Naming | Always name your API endpoints using plural nouns (e.g., `/customers`, `/invoices`). Avoid singular nouns or verbs. | When designing any new REST endpoint. |
| GET for Retrieval | Use the `GET` method exclusively for reading or retrieving data. Never use `GET` to create, update, or delete data. | When building a read-only operation or a list/detail view. |
| POST for Creation | Use the `POST` method to create new resources. The request body typically contains the data for the new resource. | When a client needs to add a new item to a collection. |
| Consistent Status Codes | Use standard HTTP status codes consistently (e.g., `200 OK` for success, `201 Created` for successful creation, `400 Bad Request` for client errors, `404 Not Found` for missing resources, `500 Internal Server Error` for server failures). | For every API response to ensure predictable client behavior. |

## Cheatsheet
- **Endpoint Naming:** Always use **plural nouns** (e.g., `/articles`, `/comments`).
- **Method Mapping:**
    - `GET` → **Retrieve** data (read).
    - `POST` → **Create** new data.
- **Status Code Quick Reference:**
    - `200 OK`: General success (e.g., successful GET).
    - `201 Created`: Successful resource creation (e.g., successful POST).
    - `400 Bad Request`: Client sent invalid data.
    - `404 Not Found`: Resource does not exist.
    - `500 Internal Server Error`: Server-side failure.

## Cross-References
- **HTTP Methods (PUT, PATCH, DELETE):** Extends the basic GET/POST pattern for full CRUD operations.
- **API Versioning:** How to manage changes to your API over time (e.g., `/v1/users`).
- **RESTful Resource Relationships:** Designing endpoints for nested resources (e.g., `/users/{id}/orders`).
- **Error Response Body Design:** Best practices for structuring error messages returned with 4xx and 5xx status codes.
