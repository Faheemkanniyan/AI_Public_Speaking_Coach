/**
 * SpeakPro AI – General UI & Utility JavaScript
 * Handles notifications, dark mode toggle, and smooth transitions.
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Auto-dismiss Bootstrap alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert-auto-dismiss");
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    }, 5000);
  });

  // 2. Dark Mode Toggle
  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) {
    themeBtn.addEventListener("click", function () {
      const currentTheme = document.body.getAttribute("data-bs-theme");
      const newTheme = currentTheme === "dark" ? "light" : "dark";
      document.body.setAttribute("data-bs-theme", newTheme);
      localStorage.setItem("speakpro_theme", newTheme);
    });
  }

  // Restore saved theme
  const savedTheme = localStorage.getItem("speakpro_theme");
  if (savedTheme) {
    document.body.setAttribute("data-bs-theme", savedTheme);
  }
});

/**
 * Utility function to display toast notifications dynamically
 */
function showToast(message, type = "success") {
  const toastContainer = document.getElementById("toastContainer");
  if (!toastContainer) return;

  const toastId = "toast_" + Date.now();
  const bgClass = type === "success" ? "bg-success" : (type === "error" ? "bg-danger" : "bg-info");
  
  const toastHtml = `
    <div id="${toastId}" class="toast align-items-center text-white ${bgClass} border-0 mb-2" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">
          ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;

  toastContainer.insertAdjacentHTML("beforeend", toastHtml);
  const toastEl = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastEl, { delay: 4000 });
  toast.show();
}
