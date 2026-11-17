# WhatsApp customer journey

## Mode A (first pilot)

The designer forwards a client request to Qshift's dedicated business number. Qshift cannot see
the original client chat. The designer remains the operator and receives the approved PDF back.

```text
Designer: projects
Qshift: permitted project list
Designer: use project-sharma
Designer: Kitchen granite badulu quartz pettandi; guest bedroom false ceiling remove cheyyandi.
Qshift: separate proposed operations and verified catalogue options
Designer: choose <verified option>
Designer: review
Qshift: before/after lines, amounts, tax, total, exact approval token
Approver: approve <one-time token>
Qshift: immutable version; PDF queued
Designer: history
Qshift: approved versions and delivery state
```

Buttons/lists are additive metadata; every choice has a text fallback. A plain `yes` never
approves. Ambiguous project, room, material or quantity remains pending clarification.

## Mode B (future)

An eligible firm-number integration can route permitted client events to the same tenant-scoped
business services. Coexistence, historical chats, groups and personal chats are not assumed.
Client delivery requires the connected account's authorization and applicable message window or
template rules.
