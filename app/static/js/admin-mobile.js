(() => {
  const MOBILE_QUERY = "(max-width: 767.98px)";

  function setupMobileFilters() {
    const sidebar = document.getElementById("filter-sidebar");
    if (!sidebar) return;

    const header = sidebar.querySelector(".card-header");
    if (!header) return;

    const title = header.querySelector(".card-title");
    if (title && title.textContent.trim() === "Filters") {
      title.textContent = "Фильтры";
    }

    header.setAttribute("role", "button");
    header.setAttribute("tabindex", "0");
    header.setAttribute(
      "aria-expanded",
      String(sidebar.classList.contains("is-open")),
    );

    const toggle = () => {
      if (!window.matchMedia(MOBILE_QUERY).matches) return;

      sidebar.classList.toggle("is-open");
      header.setAttribute(
        "aria-expanded",
        String(sidebar.classList.contains("is-open")),
      );
    };

    header.addEventListener("click", toggle);

    header.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        toggle();
      }
    });
  }

  function setupAdminPage() {
    const actions = document.getElementById("dropdownMenuButton");
    if (actions?.disabled) {
      actions.closest(".dropdown")?.remove();
      document
        .querySelectorAll("#select-all, input.select-box[type='checkbox']")
        .forEach((checkbox) => checkbox.closest("th, td")?.remove());
    }
    setupMobileFilters();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", setupAdminPage);
  } else {
    setupAdminPage();
  }
})();
