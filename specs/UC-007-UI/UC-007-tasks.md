# Tasks: UC-007 Giao diện Chat ReactJS

**Input**: Design documents from `/specs/UC-007-UI/`

**Prerequisites**: UC-007-plan.md (required), UC-007.md (spec — required), UC-007-research.md, UC-007-data-model.md, UC-007-quickstart.md

**Tests**: Not requested — test tasks are omitted.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Frontend**: `frontend/src/` (Vite + React TypeScript SPA)
- **Backend**: Already implemented in UC-006 (`src/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the Vite React project and configure the dev environment

- [x] T001 Scaffold Vite React TypeScript project via `npm create vite@latest frontend -- --template react-ts`
- [x] T002 [P] Remove Vite boilerplate files (default App.tsx content, App.css, assets/react.svg, public/vite.svg)
- [x] T003 [P] Configure `vite.config.ts` with dev server proxy to `http://localhost:8000` for `/api` routes in frontend/vite.config.ts
- [x] T004 Update `frontend/index.html` with meta tags (title "DiaCareFlow", description, charset, viewport)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: CSS design system and shared types that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Define CSS Variables and global reset styles in frontend/src/index.css (--primary-blue, --emerald-green, --white, --error-red, typography, box-sizing reset)
- [x] T006 [P] Create `Message` TypeScript interface in frontend/src/types/message.ts (id: string, role: 'user' | 'bot' | 'error', content: string, isRefused: boolean)
- [x] T007 [P] Implement `chatService` module in frontend/src/services/chatService.ts (sendMessage function: POST /api/chat with fetch, parse response.text(), error handling for E1/E2)

**Checkpoint**: Foundation ready — CSS system, types, and API service layer are in place

---

## Phase 3: User Story 1 — Chat Hỏi Đáp Bình Thường (Priority: P1) 🎯 MVP

**Goal**: Người dùng gõ câu hỏi, nhận câu trả lời từ backend hiển thị trong vùng chat

**Independent Test**: Chạy frontend + backend → gõ "Tiền tiểu đường là gì?" → hiển thị loading → hiển thị câu trả lời

### Implementation for User Story 1

- [x] T008 [US1] Create `ChatBubble` component in frontend/src/components/ChatBubble/ChatBubble.tsx (render message bubble with role-based styling: user right-aligned, bot left-aligned)
- [x] T009 [P] [US1] Create `ChatBubble.css` styles in frontend/src/components/ChatBubble/ChatBubble.css (bubble shape, colors per role, padding, border-radius, max-width)
- [x] T010 [US1] Create `ChatInput` component in frontend/src/components/ChatInput/ChatInput.tsx (text input + send button, form submit handler, disable while loading)
- [x] T011 [P] [US1] Create `ChatInput.css` styles in frontend/src/components/ChatInput/ChatInput.css (input field, send button, fixed-bottom layout)
- [x] T012 [US1] Create `MessageList` component in frontend/src/components/MessageList/MessageList.tsx (scrollable message container, auto-scroll to bottom via useRef + scrollIntoView)
- [x] T013 [P] [US1] Create `MessageList.css` styles in frontend/src/components/MessageList/MessageList.css (overflow-y scroll, flex-grow, padding)
- [x] T014 [US1] Create `useChat` custom hook in frontend/src/hooks/useChat.ts (messages state via useState, sendMessage handler calling chatService, loading state, append user/bot messages with unique id)
- [x] T015 [US1] Create `LoadingIndicator` component in frontend/src/components/LoadingIndicator/LoadingIndicator.tsx (spinner or animated dots shown during API call)
- [x] T016 [P] [US1] Create `LoadingIndicator.css` styles in frontend/src/components/LoadingIndicator/LoadingIndicator.css (animation keyframes, centered layout)
- [x] T017 [US1] Assemble `ChatPage` in frontend/src/pages/ChatPage/ChatPage.tsx (compose Header, MessageList, LoadingIndicator, ChatInput; wire useChat hook)
- [x] T018 [P] [US1] Create `ChatPage.css` styles in frontend/src/pages/ChatPage/ChatPage.css (full-height flex layout, main container)
- [x] T019 [US1] Update `App.tsx` in frontend/src/App.tsx to render ChatPage as the root route

**Checkpoint**: Happy-path chat fully functional — gõ câu hỏi, thấy loading, nhận câu trả lời

---

## Phase 4: User Story 2 — Hiển Thị Câu Từ Chối (Priority: P2)

**Goal**: Khi backend trả lời từ chối (is_refused), giao diện hiển thị styling cảnh báo (viền đỏ/icon cảnh báo)

**Independent Test**: Gõ "Kê đơn Metformin cho tôi" → câu trả lời hiển thị với viền đỏ và icon cảnh báo

### Implementation for User Story 2

- [x] T020 [US2] Add refusal detection logic in frontend/src/hooks/useChat.ts (check response text for refusal patterns like "Xin lỗi, tôi không thể", set isRefused: true on bot message)
- [x] T021 [US2] Add refused-message styling variant in frontend/src/components/ChatBubble/ChatBubble.css (red border, warning icon, distinct background color for isRefused messages)
- [x] T022 [US2] Update `ChatBubble.tsx` to conditionally apply refused class and render warning icon when message.isRefused is true in frontend/src/components/ChatBubble/ChatBubble.tsx

**Checkpoint**: Câu từ chối hiển thị với styling cảnh báo rõ ràng, phân biệt được với câu trả lời bình thường

---

## Phase 5: User Story 3 — Xử Lý Lỗi Kết Nối (Priority: P3)

**Goal**: Khi backend không chạy hoặc trả HTTP 500, giao diện hiển thị thông báo lỗi thân thiện

**Independent Test**: Dừng backend → gõ câu hỏi → thấy "Không thể kết nối đến server. Vui lòng thử lại sau."

### Implementation for User Story 3

- [x] T023 [US3] Enhance error handling in frontend/src/services/chatService.ts (catch network errors → return E1 message, catch HTTP 500 → return E2 message)
- [x] T024 [US3] Update `useChat` hook in frontend/src/hooks/useChat.ts to append error messages with role 'error' from chatService error responses
- [x] T025 [US3] Add error-message styling in frontend/src/components/ChatBubble/ChatBubble.css (distinct style for role='error': system-error background, icon, muted color)
- [x] T026 [US3] Update `ChatBubble.tsx` to render error role with error styling in frontend/src/components/ChatBubble/ChatBubble.tsx

**Checkpoint**: Lỗi kết nối và lỗi server đều hiển thị thông báo rõ ràng, không blank screen

---

## Phase 6: User Story 4 — Validation Input Trống (Priority: P4)

**Goal**: Khi người dùng nhấn Enter với ô input rỗng, không gửi request, hiển thị gợi ý

**Independent Test**: Để trống ô chat → nhấn Enter → không gửi request, có nhắc nhở

### Implementation for User Story 4

- [x] T027 [US4] Add empty-input validation in frontend/src/components/ChatInput/ChatInput.tsx (trim check, prevent submit, show placeholder hint or shake animation)
- [x] T028 [P] [US4] Add shake animation CSS in frontend/src/components/ChatInput/ChatInput.css (keyframe animation for empty-submit feedback)

**Checkpoint**: Input trống bị chặn, không request nào được gửi, có phản hồi UI

---

## Phase 7: User Story 5 — Branding Y Tế & Header (Priority: P5)

**Goal**: Giao diện hiển thị header "DiaCareFlow" với bảng màu xanh dương/xanh lá/trắng (branding y tế)

**Independent Test**: Mở trang → thấy header "DiaCareFlow", gradient y tế, bảng màu chuyên nghiệp

### Implementation for User Story 5

- [x] T029 [US5] Create `Header` component in frontend/src/components/Header/Header.tsx (app title "DiaCareFlow", subtitle/tagline, medical branding gradient)
- [x] T030 [P] [US5] Create `Header.css` styles in frontend/src/components/Header/Header.css (gradient background, typography, logo area, responsive)
- [x] T031 [US5] Integrate Header into ChatPage layout in frontend/src/pages/ChatPage/ChatPage.tsx (add Header at top of flex container)

**Checkpoint**: Header DiaCareFlow hiển thị đẹp, branding y tế rõ ràng

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [x] T032 [P] Add responsive design media queries across all CSS files for mobile/tablet views
- [x] T033 [P] Add smooth scroll animation and transition effects in frontend/src/components/MessageList/MessageList.css
- [x] T034 Long-response handling: ensure chat area scrolls properly for E3 (very long answers) in frontend/src/components/MessageList/MessageList.tsx
- [x] T035 Disable send button and input during loading for E4 (slow network) — verify in frontend/src/components/ChatInput/ChatInput.tsx
- [ ] T036 Run quickstart.md validation scenarios (all 4 kịch bản) manually

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Stories (Phase 3–7)**: All depend on Foundational phase completion
  - US1 (P1): No dependencies on other stories — **MVP target**
  - US2 (P2): Extends US1 components (ChatBubble, useChat) — best done after US1
  - US3 (P3): Extends US1 service and components — best done after US1
  - US4 (P4): Extends US1 ChatInput component — can run after US1
  - US5 (P5): Independent from other stories — can run in parallel with US2–US4
- **Polish (Phase 8)**: Depends on all desired user stories being complete

### Within Each User Story

- CSS files marked [P] can be created in parallel with their component
- Components depend on types (T006) and service (T007) from Foundational
- Compose page (T017) depends on individual components

### Parallel Opportunities

- T002, T003 can run in parallel (Setup phase)
- T006, T007 can run in parallel (Foundational phase)
- CSS files (T009, T011, T013, T016, T018) can be created in parallel with their components
- US5 (Header/Branding) can run fully in parallel with US2, US3, US4

---

## Parallel Example: User Story 1

```bash
# Launch CSS files in parallel (no dependencies between them):
Task: "Create ChatBubble.css in frontend/src/components/ChatBubble/ChatBubble.css"
Task: "Create ChatInput.css in frontend/src/components/ChatInput/ChatInput.css"
Task: "Create MessageList.css in frontend/src/components/MessageList/MessageList.css"
Task: "Create LoadingIndicator.css in frontend/src/components/LoadingIndicator/LoadingIndicator.css"
Task: "Create ChatPage.css in frontend/src/pages/ChatPage/ChatPage.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (Happy-path chat)
4. **STOP and VALIDATE**: Test với quickstart.md Kịch bản 1
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (**MVP!**)
3. Add User Story 2 (Refusal) → Test → Demo
4. Add User Story 3 (Error handling) → Test → Demo
5. Add User Story 4 (Validation) → Test → Demo
6. Add User Story 5 (Branding) → Test → Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (MVP — priority)
   - After US1 complete: Developer A: US2, Developer B: US5 (parallel)
   - Developer C: US3, US4

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Backend API: `POST http://localhost:8000/api/chat` (raw string response, parse with `.text()`)
- CSS Variables defined in T005 are the single source of truth for colors/typography
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
