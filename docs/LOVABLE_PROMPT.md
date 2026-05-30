# SiteNarrator — Frontend Prompt for Lovable

## What This App Is

SiteNarrator is an AI-powered construction daily report generator. Construction superintendents upload site photos and record voice notes at end of day. AI agents analyze the photos, extract structured data, and write a professional 10-section daily narrative report. A Project Coordinator reviews and approves before delivery to the client. Clients can ask clarifying questions via a chat widget on the delivered report.

## Design System

Use the curious.pm design language — warm, human, approachable. NOT enterprise software. NOT cold corporate blue.

### Colors (CSS Variables)
```css
:root {
  --background: hsl(36, 43%, 97%);       /* warm cream */
  --foreground: hsl(0, 0%, 8%);          /* near black */
  --card: hsl(0, 0%, 100%);             /* white cards */
  --primary: hsl(45, 90%, 60%);          /* rich amber/gold */
  --primary-hover: hsl(38, 85%, 45%);    /* darker gold */
  --secondary: hsl(36, 30%, 94%);        /* warm light */
  --muted: hsl(36, 20%, 93%);           /* warm muted */
  --muted-foreground: hsl(0, 0%, 44%);   /* gray text */
  --border: hsl(36, 20%, 85%);          /* warm border */
  --destructive: hsl(0, 70%, 55%);       /* red */
  --success: hsl(152, 60%, 42%);         /* green */
  --accent-peach: hsl(38, 65%, 88%);     /* pastel peach */
  --accent-mint: hsl(160, 40%, 88%);     /* pastel mint */
  --sidebar-bg: hsl(36, 30%, 99%);       /* off-white sidebar */
}
```

### Typography
- Font: Inter (Google Fonts)
- Headings: font-bold or font-extrabold, tracking-tight
- Body: text-sm or text-base, leading-relaxed
- Labels: text-xs, uppercase, tracking-wide, muted color

### Components Style
- Buttons: rounded-full, px-6 py-3, font-semibold, shadow-sm
- Primary buttons: amber/gold background, white text
- Secondary buttons: border-2 border-black, black text, hover inverts
- Cards: rounded-2xl, shadow-sm, border with warm border color, p-6
- Inputs: rounded-xl, border warm, px-4 py-3, focus ring amber
- Pills/Tags: rounded-full, px-4 py-1.5, border, selected = amber bg + white text
- Navigation: active item has dark background (black) with white text, not colored

### Layout Principles
- Sidebar navigation (left, 240px wide, fixed)
- Generous whitespace everywhere
- Max content width for readability
- Rounded everything (1rem radius)
- No sharp corners, no flat gray backgrounds
- Warm cream background on all pages

### Tone
- Large bold statements as page titles
- Conversational, not corporate
- Human and approachable
- Emoji used sparingly and only in conversational contexts (chat), NOT in navigation

## Pages to Build

### Page 1: Setup (shown on first visit only)
- Route: / (when no localStorage data exists)
- Centered card on cream background
- "SiteNarrator" logo at top (text-2xl font-extrabold)
- Heading: "Let's get you set up."
- Subtext: "One time only — then it's photos and go."
- Fields: Your Name, Project ID, Project Name
- Gold button: "Let's go →"
- Saves to localStorage, then shows the Capture page

### Page 2: Capture (main page — conversational agent)
- Route: /
- Left sidebar with: logo, active project card (amber accent bg), nav items (Capture, Review, Reports), system status indicator (green dot), user avatar at bottom
- Main area is a CHAT INTERFACE (not a form):
  - Messages area (scrollable, takes most of the height)
  - Agent messages: white card with warm border, left-aligned
  - User messages: amber/gold background, white text, right-aligned
  - Messages animate in (slide up)
- Bottom input area (sticky):
  - When waiting for photos: large dashed drop zone "Drop site photos here" with click-to-browse
  - When photos uploaded: text input (rounded-full) + Send button + Skip button
  - When generating: animated dots with "Agents working..." text
  - When done: success message with action buttons
- Flow:
  1. Agent greets user by name: "Hey [name], end of day on [project]. Drop your site photos and I'll build today's report."
  2. User drops photos → thumbnails appear in a grid inside a message bubble
  3. Agent says: "Got [N] photos. Analyzing... Anything the photos don't show? Crew counts, delays, deliveries?"
  4. User types context OR clicks Skip
  5. Agent says: "On it. Pulling weather, extracting observations, writing narrative..."
  6. Agent says: "✅ Report ready. Confidence: High." with buttons: "Preview Report" and "Go to Dashboard"

### Page 3: Review (PC reviews the draft)
- Route: /review
- Same sidebar layout
- Top: quality badge (green if passed, amber if needs attention) showing confidence %
- Main: white card containing the full narrative report rendered as formatted text
  - H2 headings for each section (10 sections)
  - Tables rendered properly
  - Photo citations highlighted in amber
- Bottom: two action buttons
  - Green "Approve & Generate PDF" (full width left)
  - Red outline "Request Revision" (right)
- If revision clicked: expandable textarea appears asking "What needs to change?"
- After approval: success screen with "Download PDF" button and "View Client Report" link

### Page 4: Dashboard / Reports
- Route: /dashboard
- Same sidebar layout
- Section 1: "Recent Reports" — list of report cards showing date, status badge, project name
- Section 2: "Generate Period Summary" — date range picker (From/To) with "Generate Summary" button
- Section 3: "Quick Stats" — 3 stat cards in a row (Reports Today, Quality Score, Pending Review)

### Page 5: Client Report View (what the client sees)
- Route: /report/:id
- NO sidebar (this is a public-facing page)
- Clean top bar: "SiteNarrator" logo + "Daily Construction Report" subtitle
- Main: white card with the full formatted report (same rendering as Review page)
- FLOATING CHAT WIDGET (bottom-right corner):
  - Collapsed: amber circle button with chat icon
  - Expanded: 400px wide panel with:
    - Amber header: "Ask about this report" + "Powered by SiteNarrator AI"
    - Message area with bubbles (user = amber, assistant = white)
    - Welcome message: "Hi! Ask me anything about this report."
    - Input: rounded-full text input + send button
  - The chat answers questions about the report content
  - When it can't answer: "I don't have enough info in this report. Would you like me to connect you with the Project Operations team?"
  - If user says yes: "Done — I've connected you with Project Operations. They'll respond within 1 business hour."

## API Integration

The backend runs at `http://localhost:8000`. All API calls go there.

### Endpoints:
- `POST /api/v1/submissions` — multipart form: project_id, report_date, superintendent_name, lat, lon, trade_tags, text_notes, zones, photos[], voice_note (optional)
- `GET /api/v1/drafts/{draft_id}` — returns: { draft_id, status, narrative, quality_report, eval_report, trace_id }
- `POST /api/v1/drafts/{draft_id}/approve` — body: { approved_by, edits_made }. Returns: { pdf_download_url, client_report_url }
- `POST /api/v1/drafts/{draft_id}/reject` — body: { rejected_by, section_comments: { "section": "comment" } }
- `GET /api/v1/drafts/{draft_id}/pdf` — returns PDF file download
- `POST /api/v1/reports/{report_id}/chat` — body: { message }. Returns: { response: { content, citations, confidence, escalated } }
- `POST /api/v1/reports/generate` — body: { project_id, date_from, date_to, requested_by }
- `GET /health` — returns { status: "ok" }

### Key behaviors:
- After POST /submissions succeeds, store `draft_id` in localStorage and navigate to /review
- The draft endpoint returns `status: "draft_ready"` when the narrative is available
- After approval, the PDF is downloadable at the returned URL
- Chat endpoint returns `escalated: true` when the AI can't answer

## Important Notes
- Use React + TypeScript + Tailwind CSS
- Use react-dropzone for photo uploads
- Use react-router-dom for routing
- Store superintendent name, project_id, project_name in localStorage
- The app should feel WARM and HUMAN — like curious.pm, not like Jira
- No cold blues, no flat grays, no sharp corners
- The sidebar active state uses BLACK background with white text (not colored highlight)
- The primary action color is always the warm amber/gold
- Every page has generous padding and breathing room
