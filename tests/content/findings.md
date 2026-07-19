# Findings

The findings below are ordered by severity — including those the client called
“critical” and the team’s notes on response times → remediation.

## SQL Injection in Search Endpoint

| Field | Value |
|-------|-------|
| Severity | Medium |
| Component | `api.example.com/v2/search` |
| Status | Open |

The search endpoint concatenates user input directly into a query. Use
parameterized queries to remediate.

```sql
SELECT * FROM products WHERE name = ?;
```

## Missing Security Headers

The application does not set `Content-Security-Policy`. Add the following:

- `Content-Security-Policy`
- `X-Content-Type-Options: nosniff`
- `Strict-Transport-Security`

> Defense in depth: headers complement, but do not replace, input validation.

## Remediation Steps

1. Parameterize all queries and review the data-access layer for any remaining
   string concatenation.
2. Add the missing security headers at the edge proxy.
3. Add regression tests so the headers cannot silently regress.
