"use strict";
const adminCsrfToken =
  document.querySelector('meta[name="csrf-token"]')?.content || "";
function addAdminCsrf(form) {
  if (!form || (form.method || "").toLowerCase() !== "post") return;
  let field = form.querySelector('input[name="csrf_token"]');
  if (!field) {
    field = document.createElement("input");
    field.type = "hidden";
    field.name = "csrf_token";
    form.appendChild(field);
  }
  field.value = adminCsrfToken;
}
document.querySelectorAll("form").forEach(addAdminCsrf);
document.addEventListener(
  "submit",
  (event) => addAdminCsrf(event.target),
  true,
);
if (window.jQuery) {
  window.jQuery.ajaxSetup({ headers: { "X-CSRF-Token": adminCsrfToken } });
}
// Logout is a POST so a third-party link cannot end a user's session.
document.querySelectorAll("a[href]").forEach((link) => {
  if (new URL(link.href, location.href).pathname !== "/admin/logout") return;
  const form = document.createElement("form");
  form.method = "post";
  form.action = link.href;
  const button = document.createElement("button");
  button.type = "submit";
  button.className = link.className;
  while (link.firstChild) button.appendChild(link.firstChild);
  form.appendChild(button);
  addAdminCsrf(form);
  link.replaceWith(form);
});
