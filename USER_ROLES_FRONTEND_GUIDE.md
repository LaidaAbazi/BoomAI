# User Roles Implementation - Frontend Developer Guide

## Overview
The backend has been fully implemented with a role-based system where:
- **Owners**: Can create stories, generate all "booms" (videos, podcasts), invite employees, and view all company stories (including submitted employee stories)
- **Employees**: Can create stories and view their own stories, but cannot generate booms. Employees can submit stories to owners, and once submitted, they cannot edit them further.

## New Endpoints Added

### 1. Company Invite Management (Owner Only)

#### POST `/api/companies/invites`
Create an invite for an employee to join the company.

**Authentication**: Required (Owner only - returns 403 for employees)

**Request Body**:
```json
{
  "email": "employee@example.com"
}
```

**Response (201 Created)**:
```json
{
  "success": true,
  "message": "Invite created and sent successfully",
  "invite": {
    "id": 1,
    "email": "employee@example.com",
    "expires_at": "2025-12-03T12:00:00Z"
  }
}
```

**Error Responses**:
- `400`: Invalid email, user already exists, or active invite already exists
- `403`: Only owners can create invites
- `401`: Not authenticated

---

#### GET `/api/companies/invites`
List all invites for the current user's company.

**Authentication**: Required (Owner only - returns 403 for employees)

**Response (200 OK)**:
```json
{
  "success": true,
  "invites": [
    {
      "id": 1,
      "email": "employee@example.com",
      "role": "employee",
      "expires_at": "2025-12-03T12:00:00Z",
      "accepted_at": null,
      "used": false,
      "created_at": "2025-11-26T12:00:00Z"
    }
  ]
}
```

**Error Responses**:
- `403`: Only owners can view invites
- `401`: Not authenticated

---

#### DELETE `/api/companies/invites/<invite_id>`
Cancel/delete an invite.

**Authentication**: Required (Owner only - returns 403 for employees)

**Response (200 OK)**:
```json
{
  "success": true,
  "message": "Invite cancelled successfully"
}
```

**Error Responses**:
- `404`: Invite not found
- `403`: Only owners can cancel invites
- `401`: Not authenticated

---

#### GET `/api/companies/invites/validate/<token>` (Public)
Validate an invite token and get invite details. Used during signup flow.

**Authentication**: Not required (public endpoint)

**Response (200 OK)**:
```json
{
  "success": true,
  "valid": true,
  "email": "employee@example.com",
  "company_name": "Acme Corp"
}
```

**Error Responses**:
- `404`: Invalid or expired invite

---

### 2. Story Submission (Employee Only)

#### POST `/api/case_studies/<case_study_id>/submit`
Submit a case study to the company owner. Once submitted, employees cannot edit the story.

**Authentication**: Required (Employee only - returns 403 for owners)

**Response (200 OK)**:
```json
{
  "status": "success",
  "message": "Case study submitted successfully to owner",
  "submitted_at": "2025-11-26T14:30:00Z"
}
```

**Error Responses**:
- `400`: Case study already submitted
- `403`: Only employees can submit stories
- `404`: Case study not found
- `401`: Not authenticated

---

## Modified Endpoints

### 1. POST `/api/signup`
Now accepts an optional `invite_token` field for employee signup.

**Request Body** (with invite):
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "email": "employee@example.com",
  "password": "securepassword123",
  "invite_token": "abc123..." // Optional: from URL query param
}
```

**Note**: If `invite_token` is provided:
- Email must match the invite email
- User will be created as `role: "employee"` and linked to the company
- Invite will be marked as used

**Request Body** (without invite - owner signup):
```json
{
  "first_name": "Jane",
  "last_name": "Smith",
  "email": "owner@example.com",
  "password": "securepassword123",
  "company_name": "My Company" // Optional
}
```

**Note**: Without invite token, user is created as `role: "owner"` and a company is automatically created.

---

### 2. GET `/api/user`
Returns user information including role and company_id.

**Response (200 OK)**:
```json
{
  "user": {
    "id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "email": "user@example.com",
    "company_name": "Acme Corp",
    "role": "owner", // or "employee"
    "company_id": 1,
    "created_at": "2025-11-26T12:00:00Z",
    "last_login": "2025-11-26T14:00:00Z",
    "stories_used_this_month": 3,
    "extra_credits": 0,
    "last_reset_date": "2025-11-01",
    "has_active_subscription": true,
    "subscription_start_date": "2025-11-01"
  }
}
```

**Important**: The frontend should store `user.role` and `user.company_id` to conditionally show/hide features.

---

### 3. GET `/api/case_studies`
Returns case studies with role-based filtering:
- **Owners**: See their own stories (always) + submitted employee stories from their company
- **Employees**: See all their own stories (submitted or not)

**Response (200 OK)**:
```json
{
  "success": true,
  "case_studies": [
    {
      "id": 1,
      "title": "Case Study Title",
      "final_summary": "...",
      "created_at": "2025-11-26T12:00:00Z",
      "created_by": { // Only present for owners viewing employee stories
        "id": 2,
        "first_name": "Employee",
        "last_name": "Name",
        "email": "employee@example.com"
      },
      // ... other fields
    }
  ]
}
```

**Note**: The `created_by` field is only included when:
- Current user is an owner
- The story was created by a different user (employee)

**New Fields**:
- `submitted`: Boolean - Whether the story has been submitted to owner
- `submitted_at`: String (ISO datetime) - When the story was submitted (null if not submitted)

---

## Owner-Only Endpoints (Return 403 for Employees)

These endpoints are restricted to owners only. Employees will receive a 403 Forbidden response.

### 1. POST `/api/generate_video`
Generate HeyGen video (1-minute)

**Request Body**:
```json
{
  "case_study_id": 1
}
```

**Error Response (403)**:
```json
{
  "error": "Owner access required",
  "message": "Only company owners can perform this action"
}
```

---

### 2. POST `/api/generate_newsflash_video`
Generate HeyGen newsflash video (30-second)

**Request Body**:
```json
{
  "case_study_id": 1
}
```

**Error Response (403)**: Same as above

---

### 3. POST `/api/generate_pictory_video`
Generate Pictory video

**Request Body**:
```json
{
  "case_study_id": 1
}
```

**Error Response (403)**: Same as above

---

### 4. POST `/api/generate_podcast`
Generate Wondercraft podcast

**Request Body**:
```json
{
  "case_study_id": 1
}
```

**Error Response (403)**:
```json
{
  "error": "Only owners can generate booms"
}
```

---

## Story Submission Workflow

### How It Works

1. **Owners create stories** - Owners can create stories and they are immediately visible to them
2. **Employees create and edit stories** - They can make changes to title, summary, LinkedIn posts, email drafts, etc.
3. **Employee stories are private** - Unsubmitted employee stories are NOT visible to owners
4. **Employees submit stories** - When ready, they click "Submit" button which calls `POST /api/case_studies/<id>/submit`
5. **Submitted stories appear on owner's dashboard** - Only AFTER submission, employee stories show up in owner's case studies list
6. **Employees cannot edit submitted stories** - All edit endpoints return 403 for employees trying to edit submitted stories
7. **Owners can view and generate booms** - Owners can see their own stories (always) + submitted employee stories and generate videos/podcasts for them

### Endpoints That Block Editing for Submitted Stories (Employees)

These endpoints return `403` with message `"Cannot edit submitted case study. Please contact your owner to make changes."` when employees try to edit submitted stories:

- `POST /api/save_final_summary`
- `PUT /api/case_studies/<id>/title`
- `POST /api/save_linkedin_post`
- `POST /api/save_email_draft`

**Note**: Owners can always edit any company story, regardless of submission status.

---

## Frontend Implementation Checklist

### ✅ Required Changes

1. **Story Submission Button (Employees Only)**
   - Add a "Submit to Owner" button for each story (only visible to employees)
   - Button should only show if `story.submitted === false`
   - On click, call `POST /api/case_studies/<id>/submit`
   - After successful submission, disable edit functionality and show "Submitted" status
   - Hide the submit button after submission

2. **Disable Editing for Submitted Stories (Employees)**
   - Check `story.submitted` before allowing edits
   - Disable/hide edit buttons for submitted stories
   - Show message: "This story has been submitted. Contact your owner to make changes."
   - Handle 403 errors gracefully with user-friendly message

3. **Show Submission Status**
   - Display "Submitted" badge/indicator for submitted stories
   - Show submission date if available
   - Owners should see which stories are submitted by employees

4. **Store User Role and Company ID**
   - After login/signup, store `user.role` and `user.company_id` in global state
   - Update these values when fetching `/api/user`

2. **Conditionally Show/Hide Boom Generation Buttons**
   - Only show video/podcast generation buttons if `user.role === 'owner'`
   - Hide for employees

3. **Display Creator Info for Owners**
   - When `user.role === 'owner'` and story has `created_by` field, display creator information

4. **Invite Management UI (Owners Only)**
   - Show "Invite Employees" section only for owners
   - Implement:
     - Form to enter email and call `POST /api/companies/invites`
     - List view to show all invites (call `GET /api/companies/invites`)
     - Cancel button for each invite (call `DELETE /api/companies/invites/<id>`)

5. **Handle Invite Token in Signup**
   - Check URL for `?invite_token=...` parameter
   - Include `invite_token` in signup request body
   - Pre-fill email from invite validation endpoint (`GET /api/companies/invites/validate/<token>`)

6. **Error Handling for 403 Responses**
   - Show user-friendly message: "Only company owners can perform this action"
   - Don't show boom generation buttons to employees (prevent the error)

### 📋 Example Frontend Code Snippets

#### Store User Role After Login
```javascript
async function fetchUser() {
  const res = await fetch('/api/user');
  if (res.status === 401) {
    window.location.href = '/login';
    return;
  }
  const data = await res.json();
  if (data.user) {
    // Store globally
    window.currentUserRole = data.user.role;
    window.currentUserCompanyId = data.user.company_id;
    
    // Use in UI
    updateUIForRole(data.user.role);
  }
}
```

#### Conditionally Show Boom Buttons
```javascript
function renderStoryActions(story) {
  const actionsDiv = document.createElement('div');
  
  // Only show boom generation for owners
  if (window.currentUserRole === 'owner') {
    const videoBtn = createButton('Generate Video', () => generateVideo(story.id));
    const podcastBtn = createButton('Generate Podcast', () => generatePodcast(story.id));
    actionsDiv.appendChild(videoBtn);
    actionsDiv.appendChild(podcastBtn);
  }
  
  return actionsDiv;
}
```

#### Handle Invite Token in Signup
```javascript
// In signup form handler
const urlParams = new URLSearchParams(window.location.search);
const inviteToken = urlParams.get('invite_token');

if (inviteToken) {
  // Validate invite and pre-fill email
  fetch(`/api/companies/invites/validate/${inviteToken}`)
    .then(res => res.json())
    .then(data => {
      if (data.valid) {
        document.getElementById('email').value = data.email;
        document.getElementById('email').readOnly = true; // Lock email
        // Show company name
        document.getElementById('company-info').textContent = 
          `Joining: ${data.company_name}`;
      }
    });
}

// In signup submission
const signupData = {
  first_name: firstNameInput.value,
  last_name: lastNameInput.value,
  email: emailInput.value,
  password: passwordInput.value,
  invite_token: inviteToken // Include if present
};
```

#### Create Invite (Owner Only)
```javascript
async function createInvite(email) {
  const res = await fetch('/api/companies/invites', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  
  if (res.status === 403) {
    alert('Only owners can invite employees');
    return;
  }
  
  const data = await res.json();
  if (data.success) {
    alert('Invite sent successfully!');
    loadInvites(); // Refresh list
  }
}
```

#### List Invites (Owner Only)
```javascript
async function loadInvites() {
  const res = await fetch('/api/companies/invites');
  if (res.status === 403) {
    return; // Not an owner
  }
  
  const data = await res.json();
  if (data.success) {
    displayInvites(data.invites);
  }
}
```

#### Handle 403 Errors
```javascript
async function generateVideo(caseStudyId) {
  const res = await fetch('/api/generate_video', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_study_id: caseStudyId })
  });
  
  if (res.status === 403) {
    const data = await res.json();
    alert(data.message || 'Only company owners can generate booms.');
    return;
  }
  
  // Handle success...
}
```

#### Submit Story (Employee Only)
```javascript
async function submitStory(caseStudyId) {
  if (!confirm('Are you sure you want to submit this story to the owner? You will not be able to edit it after submission.')) {
    return;
  }
  
  const res = await fetch(`/api/case_studies/${caseStudyId}/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  });
  
  if (res.status === 403) {
    alert('Only employees can submit stories');
    return;
  }
  
  if (res.status === 400) {
    const data = await res.json();
    alert(data.message || 'Story already submitted');
    return;
  }
  
  const data = await res.json();
  if (data.status === 'success') {
    alert('Story submitted successfully!');
    // Update UI: disable edit buttons, show submitted status
    updateStoryUI(caseStudyId, { submitted: true, submitted_at: data.submitted_at });
  }
}

function updateStoryUI(storyId, submissionData) {
  // Hide submit button
  const submitBtn = document.getElementById(`submit-btn-${storyId}`);
  if (submitBtn) submitBtn.style.display = 'none';
  
  // Disable edit buttons
  const editButtons = document.querySelectorAll(`[data-story-id="${storyId}"] .edit-btn`);
  editButtons.forEach(btn => {
    btn.disabled = true;
    btn.style.opacity = '0.5';
  });
  
  // Show submitted badge
  const storyElement = document.querySelector(`[data-story-id="${storyId}"]`);
  if (storyElement) {
    const badge = document.createElement('span');
    badge.className = 'submitted-badge';
    badge.textContent = '✓ Submitted';
    badge.style.cssText = 'background: #10b981; color: white; padding: 4px 8px; border-radius: 4px; font-size: 0.875rem;';
    storyElement.querySelector('.story-header').appendChild(badge);
  }
}
```

#### Check Submission Status Before Editing
```javascript
function canEditStory(story) {
  // Owners can always edit
  if (window.currentUserRole === 'owner') {
    return true;
  }
  
  // Employees cannot edit submitted stories
  if (window.currentUserRole === 'employee' && story.submitted) {
    return false;
  }
  
  return true;
}

// Use in edit functions
function editStoryTitle(storyId) {
  const story = getStoryById(storyId);
  if (!canEditStory(story)) {
    alert('Cannot edit submitted story. Please contact your owner to make changes.');
    return;
  }
  
  // Proceed with edit...
}
```

---

## Summary

### New Endpoints
1. `POST /api/companies/invites` - Create invite (owner only)
2. `GET /api/companies/invites` - List invites (owner only)
3. `DELETE /api/companies/invites/<id>` - Cancel invite (owner only)
4. `GET /api/companies/invites/validate/<token>` - Validate invite token (public)
5. `POST /api/case_studies/<id>/submit` - Submit story to owner (employee only)

### Modified Endpoints
1. `POST /api/signup` - Now accepts `invite_token` field
2. `GET /api/user` - Returns `role` and `company_id`
3. `GET /api/case_studies` - Returns `created_by`, `submitted`, and `submitted_at` fields
4. `GET /api/case_studies/<id>` - Returns `submitted` and `submitted_at` fields
5. `POST /api/save_final_summary` - Blocks employees from editing submitted stories
6. `PUT /api/case_studies/<id>/title` - Blocks employees from editing submitted stories
7. `POST /api/save_linkedin_post` - Blocks employees from editing submitted stories
8. `POST /api/save_email_draft` - Blocks employees from editing submitted stories

### Owner-Only Endpoints (403 for employees)
1. `POST /api/generate_video`
2. `POST /api/generate_newsflash_video`
3. `POST /api/generate_pictory_video`
4. `POST /api/generate_podcast`

### Data Passed from Frontend
- **Signup with invite**: Include `invite_token` in request body
- **Create invite**: Send `email` in request body
- **All other endpoints**: No additional fields needed (role is determined from session)

### Data Returned to Frontend
- **User object**: Always includes `role` and `company_id`
- **Case studies**: Include `created_by` object for owners viewing employee stories, plus `submitted` (boolean) and `submitted_at` (ISO datetime string or null)
- **Invites**: Full invite objects with status, expiration, etc.

---

## Testing Checklist

- [ ] Owners can see all boom generation buttons
- [ ] Employees cannot see boom generation buttons
- [ ] Employees can create stories
- [ ] Employees can view/download PDF/Word for their stories
- [ ] Owners see creator info for employee stories
- [ ] Owners can access invite management UI
- [ ] Owners can create invites
- [ ] Owners can list invites
- [ ] Owners can cancel invites
- [ ] Invite links work in signup flow (with token in URL)
- [ ] Signup with invite token creates employee account
- [ ] Signup without invite token creates owner account
- [ ] Permission errors (403) show user-friendly messages
- [ ] 403 errors are handled gracefully in all boom generation functions
- [ ] Employees can see "Submit" button for their stories
- [ ] Submit button only shows for non-submitted stories
- [ ] Employees can submit stories successfully
- [ ] Submitted stories show "Submitted" status/badge
- [ ] Employees cannot edit submitted stories (all edit endpoints blocked)
- [ ] Owners can see their own stories (always visible)
- [ ] Owners can see submitted employee stories
- [ ] Unsubmitted employee stories are NOT visible to owners
- [ ] Owners can edit submitted stories (no restrictions)
- [ ] Submission status is displayed correctly in UI

---

## Notes

- All authentication is session-based (cookies)
- The backend automatically filters case studies based on role
- Invite tokens expire after 7 days
- Email addresses in invites are case-insensitive (lowercased)
- The `created_by` field is only present when an owner views an employee's story
- Submission is one-way: employees cannot "unsubmit" stories once submitted
- Owners can always edit any company story, regardless of submission status
- The `submitted` field defaults to `false` for all existing stories
- The `submitted_at` field is `null` for non-submitted stories

