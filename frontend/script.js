/**
 * script.js — Gradient Birthday Loader
 *
 * Responsibilities:
 *   1. Poll the Flask backend's /health endpoint until it responds HTTP 200.
 *   2. Cycle status messages while waiting.
 *   3. Show a timeout warning after 90 seconds (keep polling indefinitely).
 *   4. On success: complete the progress animation, show success state,
 *      fade the page out, then redirect to the backend login page.
 *
 * The only place backend URLs appear is the CONFIG block below.
 * To point at a different backend, change BACKEND_URL — nothing else.
 */

/* ============================================================
   CONFIG — change BACKEND_URL if you ever migrate backends.
   The frontend requires zero other changes.
   ============================================================ */
var CONFIG = {
  BACKEND_URL: 'https://birthday-api.gradientclub.in',
  POLL_INTERVAL_MS: 2000,    // poll every 2 seconds
  TIMEOUT_MS: 90000,   // show warning after 90 seconds
  REDIRECT_DELAY_MS: 650,     // brief pause so user sees success state
  MSG_CYCLE_MS: 5000,    // rotate status messages every 5 seconds
};

/* ============================================================
   STATUS MESSAGES
   Cycled in order while the backend is waking up.
   ============================================================ */
var MESSAGES = [
  'Starting Birthday Poster Generator...',
  'Connecting to Server...',
  'Waking Backend...',
  'Preparing Dashboard...',
  'Almost Ready...',
];

/* ============================================================
   DOM REFERENCES
   Gathered once at startup.
   ============================================================ */
var DOM = {
  status: document.getElementById('js-status'),
  progress: document.getElementById('js-progress'),
  spinner: document.getElementById('js-spinner'),
  timeout: document.getElementById('js-timeout'),
  success: document.getElementById('js-success'),
};

/* ============================================================
   STATE
   ============================================================ */
var state = {
  msgIndex: 0,
  redirecting: false,
  pollTimer: null,
  msgTimer: null,
  warnTimer: null,
};

/* ============================================================
   MESSAGE CYCLING
   Fades out current message, swaps text, fades back in.
   ============================================================ */
function cycleMessage() {
  DOM.status.classList.add('is-fading');

  setTimeout(function () {
    state.msgIndex = (state.msgIndex + 1) % MESSAGES.length;
    DOM.status.textContent = MESSAGES[state.msgIndex];
    DOM.status.classList.remove('is-fading');
  }, 350); // matches CSS transition duration
}

/* ============================================================
   HEALTH POLL
   Fetches BACKEND_URL/health.
   On HTTP 200  → calls onServerReady().
   On failure   → silently continues (server still asleep).
   ============================================================ */
function poll() {
  if (state.redirecting) return;

  /* AbortSignal.timeout is available in all modern browsers;
     gracefully degrade for older ones by omitting the signal. */
  var fetchOpts = { method: 'GET', cache: 'no-store' };
  if (typeof AbortSignal !== 'undefined' && AbortSignal.timeout) {
    fetchOpts.signal = AbortSignal.timeout(5000);
  }

  fetch(CONFIG.BACKEND_URL + '/health', fetchOpts)
    .then(function (res) {
      if (res.ok) {
        onServerReady();
      }
      /* Non-200 response: backend is reachable but not healthy — keep polling */
    })
    .catch(function () {
      /* Network error / server still cold — keep polling silently */
    });
}

/* ============================================================
   ON SERVER READY
   Called exactly once when /health returns HTTP 200.
   Stops all timers, transitions to success state, then redirects.

   Redirect priority:
   1. __gradient_return_path in sessionStorage (set by Flask's fetch interceptor
      when a request failed while the user was inside the app). Clears after use.
   2. Falls back to BACKEND_URL + '/login'.
   ============================================================ */
function onServerReady() {
  state.redirecting = true;

  /* Stop all timers */
  clearInterval(state.pollTimer);
  clearInterval(state.msgTimer);
  clearTimeout(state.warnTimer);

  /* Update status text */
  DOM.status.classList.remove('is-fading');
  DOM.status.textContent = 'Server ready!';
  DOM.status.classList.add('is-ready');

  /* Complete progress bar */
  DOM.progress.classList.add('is-complete');

  /* Stop spinner */
  DOM.spinner.classList.add('is-done');

  /* Hide timeout warning if it was shown */
  DOM.timeout.hidden = true;

  /* Show success flash */
  DOM.success.hidden = false;

  /* Determine redirect target */
  var returnPath = null;
  try {
    returnPath = sessionStorage.getItem('__gradient_return_path');
    if (returnPath) {
      sessionStorage.removeItem('__gradient_return_path');
      sessionStorage.removeItem('__gradient_redirect_in_progress');
    }
  } catch (e) {
    /* sessionStorage unavailable (private browsing, etc.) — ignore */
  }

  var redirectTarget = returnPath
    ? CONFIG.BACKEND_URL + returnPath
    : CONFIG.BACKEND_URL + '/login';

  /* Fade the whole page out, then redirect */
  setTimeout(function () {
    document.body.classList.add('is-redirecting');

    setTimeout(function () {
      window.location.href = redirectTarget;
    }, 600); /* matches page-fade-out animation duration in CSS */

  }, CONFIG.REDIRECT_DELAY_MS);
}

/* ============================================================
   TIMEOUT WARNING
   Shown after CONFIG.TIMEOUT_MS without a successful response.
   Polling continues — we never give up automatically.
   ============================================================ */
function showTimeoutWarning() {
  DOM.timeout.hidden = false;
}

/* ============================================================
   INIT
   Kick everything off as soon as the script runs
   (script tag is at the bottom of <body>, so DOM is ready).
   ============================================================ */
function init() {
  /* Immediate first poll — no waiting for the interval */
  poll();

  /* Start recurring poll */
  state.pollTimer = setInterval(poll, CONFIG.POLL_INTERVAL_MS);

  /* Start message cycling */
  state.msgTimer = setInterval(cycleMessage, CONFIG.MSG_CYCLE_MS);

  /* Schedule timeout warning */
  state.warnTimer = setTimeout(showTimeoutWarning, CONFIG.TIMEOUT_MS);
}

init();
