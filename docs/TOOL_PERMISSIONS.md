# Agent tool permissions

| Tool | Allowed | Guard |
|---|---:|---|
| `read_project_state` | Yes | User's firm only; read-only. |
| `search_catalogue` | Yes | Verified entries only; read-only. |
| `propose_change_ops` | Yes | Schema validated; produces proposals only. |
| `create_draft_revision` | Yes | Deterministic service validates all rates, units, quantities and base version. |
| `approve_revision` | No | Human authenticated OWNER or APPROVER action only. |
| `send_to_client` | No | Not implemented. |
| `edit_rate_card` / `delete_data` | No | Admin and privacy workflows are future work. |

The offline mock uses bounded classification and fixed responses. Untrusted message and spreadsheet content is treated as data and cannot override these permissions.

