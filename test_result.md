#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  User reported two issues with partner configuration:
  1. SSH key saving bug - when editing a partner, the SSH key shows as encrypted string and doesn't work after re-saving
  2. Form validation - need to require at least one of SSH password OR SSH private key (not both required)
  3. Add SSH password field to the form (it was missing)

backend:
  - task: "Encrypt SSH passwords in backend"
    implemented: true
    working: true
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added SSH password encryption in create_partner and update_partner endpoints. SSH passwords are now encrypted before storing in database, similar to privateKey and passphrase."
      - working: true
        agent: "testing"
        comment: "✅ VERIFIED: SSH passwords are correctly encrypted in database. All SSH credentials (password, privateKey, passphrase) are properly encrypted using AES-256-CBC. Tested with multiple partner creation scenarios."
  
  - task: "Handle SSH key update without double encryption"
    implemented: true
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "high"
    needs_retesting: false
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Backend update_partner endpoint now only encrypts SSH credentials if they are provided in the update request. Empty/missing fields are not included in the update, preventing double encryption."
      - working: false
        agent: "testing"
        comment: "❌ CRITICAL BUG: SSH update logic has major flaw. When updating sshConfig partially (e.g., only password), the missing fields (privateKey, passphrase) are set to None, losing existing encrypted values. The update replaces entire sshConfig object instead of merging individual fields. This breaks partial SSH credential updates."
  
  - task: "Add backend SSH validation"
    implemented: false
    working: false
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "testing"
        comment: "❌ MISSING VALIDATION: Backend create_partner endpoint lacks validation to ensure at least one of SSH password or privateKey is provided when SSH is enabled. Frontend has this validation, but backend bypasses it, allowing invalid SSH configurations to be stored."

frontend:
  - task: "Add SSH password field to partner form"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/Partners.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Added SSH password field to the partner configuration form. Field is positioned as primary authentication method, with helper text 'Primary authentication method'."
  
  - task: "Fix SSH key double encryption bug"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/Partners.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Fixed openEditDialog function to clear sensitive fields (password, privateKey, passphrase) when editing. This prevents encrypted values from being shown and re-encrypted. Users now enter new values only when updating credentials."
  
  - task: "Add validation requiring at least one of password or privateKey"
    implemented: true
    working: "NA"
    file: "/app/frontend/src/pages/Partners.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added validation in handleSubmit to check if SSH is enabled, at least one of password or privateKey must be provided. Shows toast error if neither is provided."
  
  - task: "Update SSH form fields with proper labels and placeholders"
    implemented: true
    working: true
    file: "/app/frontend/src/pages/Partners.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: "Updated SSH form fields: Password shows as primary with helper text, Private Key marked as (optional) with helper text 'Alternative to password authentication', Passphrase also has contextual helper. Edit mode shows placeholders like 'Enter new password to update'."

metadata:
  created_by: "main_agent"
  version: "1.1"
  test_sequence: 2
  run_ui: true

test_plan:
  current_focus:
    - "Handle SSH key update without double encryption"
    - "Add backend SSH validation"
  stuck_tasks:
    - "Handle SSH key update without double encryption"
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      Implementation completed for SSH password authentication and double encryption bug fix.
      
      **Backend Changes:**
      - Added SSH password encryption in create_partner endpoint
      - Added SSH password encryption in update_partner endpoint
      - Update logic only encrypts fields when they are provided (no double encryption)
      
      **Frontend Changes:**
      - Added SSH Password field (primary authentication method)
      - SSH Private Key now marked as "(optional)"
      - Added validation: at least one of password OR privateKey required when SSH is enabled
      - Fixed double encryption bug: sensitive fields cleared when editing, only sent to backend if user enters new values
      - Added helper text for all SSH fields
      - Proper placeholders for edit mode
      
      **Testing Needed:**
      1. Create partner with SSH password only
      2. Create partner with SSH private key only
      3. Try to create partner with SSH enabled but no password/key (should show validation error)
      4. Edit existing partner and verify encrypted credentials don't show
      5. Edit partner and update only SSH password (verify key remains intact)
      6. Edit partner and update only SSH key (verify password remains intact)
      7. Test connection with password authentication
      8. Test connection with key authentication
      
      Please test all scenarios thoroughly, especially the edit flow and credential updates.
  
  - agent: "testing"
    message: |
      **BACKEND TESTING COMPLETED - CRITICAL ISSUES FOUND**
      
      **✅ WORKING CORRECTLY:**
      - SSH password encryption in database ✅
      - SSH private key encryption in database ✅
      - SSH passphrase encryption in database ✅
      - Partner creation with SSH password only ✅
      - Partner creation with SSH private key only ✅
      - No double encryption during basic updates ✅
      - All existing SSH credentials properly encrypted in database ✅
      
      **❌ CRITICAL ISSUES IDENTIFIED:**
      
      1. **BACKEND VALIDATION MISSING** (High Priority)
         - Backend allows creation of partners with SSH enabled but no credentials
         - Frontend has validation, but backend bypasses it
         - Security risk: Invalid SSH configs can be stored
         - Location: /app/backend/server.py create_partner endpoint (line 156)
      
      2. **SSH UPDATE BUG** (High Priority)
         - When updating SSH config partially, missing fields are set to None/null
         - Original encrypted privateKey and passphrase are lost during password-only updates
         - This breaks the "update only password, keep key intact" requirement
         - Location: /app/backend/server.py update_partner endpoint (line 191)
         - Root cause: sshConfig object replacement instead of field-level merging
      
      **IMPACT:**
      - Partners can be created with invalid SSH configurations
      - Existing SSH credentials are lost during partial updates
      - Users cannot safely update just SSH password without losing private key
      
      **RECOMMENDATION:**
      Main agent must fix these backend validation and update logic issues before deployment.
