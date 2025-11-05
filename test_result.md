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
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Added SSH password encryption in create_partner and update_partner endpoints. SSH passwords are now encrypted before storing in database, similar to privateKey and passphrase."
  
  - task: "Handle SSH key update without double encryption"
    implemented: true
    working: "NA"
    file: "/app/backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: "Backend update_partner endpoint now only encrypts SSH credentials if they are provided in the update request. Empty/missing fields are not included in the update, preventing double encryption."

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
  version: "1.0"
  test_sequence: 1
  run_ui: true

test_plan:
  current_focus:
    - "Add SSH password field to partner form"
    - "Fix SSH key double encryption bug"
    - "Add validation requiring at least one of password or privateKey"
    - "Encrypt SSH passwords in backend"
  stuck_tasks: []
  test_all: true
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
