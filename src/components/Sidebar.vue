<script setup lang="ts">
// added. Sidebar had no script block at all, so the "Log Out" item below
// was an inert <a> - logout() existed in the auth store and NOTHING called it.
// With route guards now in place that was a trap: once signed in there was no
// way out, and /login is guestOnly so it redirects a signed-in user away.
import { useAuthStore } from '@/stores/useAuth';
import { useRouter } from 'vue-router';

const { logout } = useAuthStore();
const router = useRouter();

async function handleLogout() {
  await logout();
  // replace() rather than push() so Back cannot return to a page that is
  // now unauthorised - the guard would bounce it, but the flash is avoidable.
  await router.replace('/login');
}
</script>
<template>
    <div class="sidebar">
        <ul class="sidebar-items">
            <div class="sidebar-group">
                <li class="sidebar-item">
                    <div class="sidebar-icon sidebar-header-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="35" height="35" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-layout-dashboard-icon lucide-layout-dashboard"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
                    </div>
                    <h1 class="sidebar-text sidebar-header-text">CambridgeParser</h1>
                </li>
            </div>
            <div class="sidebar-group">
                <label class="sidebar-label">Overview</label>
                <li class="sidebar-item">
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-layout-dashboard-icon lucide-layout-dashboard"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
                    </div>
                    <router-link to="/dashboard" class="sidebar-text" active-class="active-link" exact>
                      Dashboard
                    </router-link>                
                </li>
            </div>
            <div class="sidebar-group">
                <label class="sidebar-label">MCQ Solver</label>
                <li class="sidebar-item">
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-compass"><circle cx="12" cy="12" r="10"></circle><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"></polygon></svg>
                    </div>
                    <router-link to="/browser" class="sidebar-text" active-class="active-link" exact>
                      Paper Browser
                    </router-link>                   
                </li>
                <!-- no generator route or implementation exists yet. -->
                <li
                  class="sidebar-item sidebar-item--disabled"
                  aria-disabled="true"
                  aria-label="Paper Generator (coming soon)"
                  title="Paper Generator is coming soon"
                >
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-sparkles-icon lucide-sparkles"><path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/></svg>
                    </div>
                    <span class="sidebar-text">Paper Generator</span>
                </li>
                <!-- the "Paper Solver" item was removed. It was a
                     router-link hardcoded to /solver/0455_w22_12, so every
                     student who clicked it sat the same Economics paper
                     regardless of what they wanted. The solver is a page ABOUT
                     a specific paper; it has no meaning without one, so it is
                     now reached only by picking a paper in the browser. -->
            </div>
            <!-- the Cambridge IDE, merged in from what was a separate site.
                 It is a page group here rather than a separate application:
                 same shell, same sidebar, same session. -->
            <div class="sidebar-group">
                <label class="sidebar-label">Cambridge IDE</label>
                <li class="sidebar-item">
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 18l6-6-6-6"/><path d="M8 6l-6 6 6 6"/></svg>
                    </div>
                    <router-link to="/ide" class="sidebar-text" active-class="active-link">
                      Pseudocode IDE
                    </router-link>
                </li>
                <li class="sidebar-item">
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                    </div>
                    <router-link to="/problems" class="sidebar-text" active-class="active-link" exact>
                      Problems
                    </router-link>
                </li>
                <li class="sidebar-item">
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                    </div>
                    <router-link to="/learn" class="sidebar-text" active-class="active-link" exact>
                      Learn
                    </router-link>
                </li>
            </div>
            <div class="sidebar-group">
                <label class="sidebar-label">Data</label>
                <li class="sidebar-item">
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-bar-chart-2"><line x1="18" y1="20" x2="18" y2="10"></line><line x1="12" y1="20" x2="12" y2="4"></line><line x1="6" y1="20" x2="6" y2="14"></line></svg>
                    </div>
                    <router-link to="/stats" class="sidebar-text" active-class="active-link" exact>
                      Stats
                    </router-link>                   
                </li>
                <!-- no calendar route or implementation exists yet. -->
                <li
                  class="sidebar-item sidebar-item--disabled"
                  aria-disabled="true"
                  aria-label="Calendar (coming soon)"
                  title="Calendar is coming soon"
                >
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-calendar"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                    </div>
                    <span class="sidebar-text">Calendar</span>
                </li>
            </div>
            <div class="sidebar-group">
                <label class="sidebar-label">Tools</label>
                <!-- no settings route or implementation exists yet. -->
                <li
                  class="sidebar-item sidebar-item--disabled"
                  aria-disabled="true"
                  aria-label="Settings (coming soon)"
                  title="Settings is coming soon"
                >
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-settings"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>                        
                    </div>
                    <span class="sidebar-text">Settings</span>
                </li>
                <li class="sidebar-item">
                    <div class="sidebar-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="feather feather-log-out"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
                    </div>
                    <!-- a real button is keyboard-operable without faking
                         link semantics or relying on a mouse-only click. -->
                    <button type="button" class="sidebar-text logout-link" @click="handleLogout">
                      Log Out
                    </button>
                </li>
            </div>
        </ul>
    </div>
</template>

<style lang="scss" scoped>
/* preserve the sidebar typography while using correct button semantics. */
.logout-link {
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  text-align: left;
}

.sidebar {
  @extend %centered;
  position: fixed;
  top: 0;
  left: 0;
  height: 100%;
  width: 5vw;
  background-color: $secondary-background;
  flex-direction: column;
  border-top-right-radius: 20px;
  border-bottom-right-radius: 20px;
  overflow: hidden;
  transition: width 0.3s ease;
  z-index: 10;

  .sidebar-items {
    @extend %filler;
    position: relative;
    border-radius: inherit;

    .sidebar-group {
      width: 100%;
      padding-top: 1rem;
      padding-left: 1rem;
      padding-right: 1rem;

      &:last-child {
        position: absolute;
        bottom: 0;
      }

      .sidebar-label {
        font-family: 'Inter';
        font-weight: 500;
        color: #6c757d;
        opacity: 0;
        white-space: nowrap;
        transition: opacity 0.2s ease;
      }

      .sidebar-item {
        display: flex;
        align-items: center;
        column-gap: 15px;
        list-style-type: none;
        width: 100%;
        padding: 1rem;
        cursor: pointer;
        transition: filter 1s ease;

        &:hover {
          .sidebar-icon {
            svg {
              color: $accent;
            }
          }
        }

        .sidebar-icon {
          font-size: 25px;
          display: flex;
          align-items: center;
          justify-content: center;
          svg {
            transition: color 1s ease-in-out;
            color: lightgrey;
          }
        }

        .sidebar-text {
          font-family: 'Lexend';
          font-weight: 250;
          opacity: 0;
          white-space: nowrap;
          transition: opacity 0.2s ease;
          color: $text;
        }
      }
      /* placeholders no longer advertise an action they cannot perform. */
      .sidebar-item--disabled {
        cursor: not-allowed;
        opacity: 0.5;

        &:hover .sidebar-icon svg { color: lightgrey; }
      }
      .sidebar-header-icon {
        justify-content: center;
      }
    }
  }

  &:hover {
    width: 15vw;
    .sidebar-label,
    .sidebar-text {
      opacity: 1 !important;
    }
  }
}
</style>
