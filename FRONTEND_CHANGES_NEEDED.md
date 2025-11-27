# Frontend Changes Needed for Role-Based System

## Summary
The backend is fully implemented with role-based permissions. The frontend needs updates to reflect these permissions in the UI.

## Required Changes

### 1. **Store User Role and Company ID** (dashboard.html)
   - **Location**: `fetchUser()` function (around line 1766)
   - **Change**: Store `user.role` and `user.company_id` in global variables
   - **Code**:
   ```javascript
   let currentUserRole = null;
   let currentUserCompanyId = null;
   
   async function fetchUser() {
     const res = await fetch('/api/user');
     if (res.status === 401) { window.location.href = '/login'; return; }
     const data = await res.json();
     if (data.user) {
       document.getElementById('userName').textContent = `Hi, ${data.user.first_name} ${data.user.last_name}`.trim();
       currentUserRole = data.user.role; // Store role
       currentUserCompanyId = data.user.company_id; // Store company_id
     } else {
       document.getElementById('userName').textContent = 'Hi, User';
     }
   }
   ```

### 2. **Hide Boom Generation Buttons for Employees** (dashboard.html)
   - **Locations**: 
     - Line ~3088: Podcast generation button
     - Line ~3141: Video generation button  
     - Line ~3197: Newsflash video generation button
     - Line ~3254: Pictory video generation button
   - **Change**: Conditionally show these buttons only for owners
   - **Example** (for podcast button around line 3088):
   ```javascript
   // Only show generate button if user is owner
   if (currentUserRole === 'owner') {
     const podcastBtn = document.createElement('button');
     podcastBtn.className = 'action-btn generate-podcast-btn';
     podcastBtn.id = `podcastBtn-${story.id}`;
     podcastBtn.innerHTML = '<i class="fas fa-microphone"></i> Generate Podcast';
     // ... rest of button setup
     podcastBtn.onclick = () => generatePodcast(story.id);
     podcastSection.appendChild(podcastBtn);
   }
   ```
   - **Apply same pattern** to all boom generation buttons (video, newsflash, pictory)

### 3. **Show Creator Info for Owners** (dashboard.html)
   - **Location**: Story rendering function (around line 2400-2500)
   - **Change**: Display creator information when owner views employee stories
   - **Code**: The backend already returns `created_by` in story data. Add display:
   ```javascript
   // In renderMainContent() or story rendering section
   if (currentUserRole === 'owner' && story.created_by) {
     const creatorInfo = document.createElement('div');
     creatorInfo.className = 'creator-info';
     creatorInfo.style.marginBottom = '12px';
     creatorInfo.style.padding = '8px 12px';
     creatorInfo.style.backgroundColor = '#e0e7ff';
     creatorInfo.style.borderRadius = '6px';
     creatorInfo.style.fontSize = '0.9rem';
     creatorInfo.innerHTML = `👤 Created by: ${story.created_by.first_name} ${story.created_by.last_name} (${story.created_by.email})`;
     // Insert before story content
   }
   ```

### 4. **Add Invite Management UI for Owners** (dashboard.html)
   - **Location**: Sidebar or top navigation
   - **Change**: Add "Invite Employees" section visible only to owners
   - **Code**:
   ```javascript
   // In sidebar or after user name display
   if (currentUserRole === 'owner') {
     const inviteSection = document.createElement('div');
     inviteSection.className = 'invite-section';
     inviteSection.style.marginTop = '20px';
     inviteSection.style.padding = '16px';
     inviteSection.style.backgroundColor = '#f8fafc';
     inviteSection.style.borderRadius = '8px';
     
     const inviteHeader = document.createElement('h3');
     inviteHeader.textContent = 'Team Management';
     inviteHeader.style.marginBottom = '12px';
     inviteSection.appendChild(inviteHeader);
     
     const inviteBtn = document.createElement('button');
     inviteBtn.textContent = '➕ Invite Employee';
     inviteBtn.onclick = () => showInviteModal();
     inviteSection.appendChild(inviteBtn);
     
     // Add to sidebar
     document.querySelector('.sidebar').appendChild(inviteSection);
   }
   
   // Invite modal function
   async function showInviteModal() {
     // Create modal with form to enter email
     // On submit, call POST /api/companies/invites
   }
   
   // Function to list invites
   async function loadInvites() {
     const res = await fetch('/api/companies/invites');
     const data = await res.json();
     // Display list of invites with status
   }
   ```

### 5. **Handle Invite Token in Signup** (signup page)
   - **Location**: Signup form submission
   - **Change**: Check for `invite_token` in URL params and include in signup request
   - **Code**:
   ```javascript
   // In signup form handler
   const urlParams = new URLSearchParams(window.location.search);
   const inviteToken = urlParams.get('invite_token');
   
   const signupData = {
     email: emailInput.value,
     password: passwordInput.value,
     first_name: firstNameInput.value,
     last_name: lastNameInput.value,
     invite_token: inviteToken // Include if present
   };
   ```

### 6. **Error Handling for Permission Denied** (dashboard.html)
   - **Location**: All boom generation functions (generateVideo, generatePodcast, etc.)
   - **Change**: Handle 403 errors gracefully
   - **Code**:
   ```javascript
   async function generateVideo(storyId) {
     try {
       const response = await fetch('/api/generate_video', {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ case_study_id: storyId })
       });
       
       if (response.status === 403) {
         const data = await response.json();
         alert('Only company owners can generate booms. Please contact your company owner.');
         return;
       }
       // ... rest of function
     } catch (error) {
       // ... error handling
     }
   }
   ```

## Files to Modify
1. `templates/dashboard.html` - Main dashboard with story display
2. `templates/signup.html` (if exists) - Signup form
3. `static/script.js` - If any story creation logic is there

## Testing Checklist
- [ ] Owners see all boom generation buttons
- [ ] Employees don't see boom generation buttons
- [ ] Employees can create stories
- [ ] Employees can view/download PDF/Word for their stories
- [ ] Owners see creator info for employee stories
- [ ] Owners can access invite management UI
- [ ] Invite links work in signup flow
- [ ] Permission errors show user-friendly messages

## Notes
- The backend already returns `role` and `company_id` in `/api/user` response
- The backend already returns `created_by` in story data for owners
- All boom generation endpoints return 403 for employees
- Invite endpoints are ready at `/api/companies/invites`

