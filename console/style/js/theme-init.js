// HomenS.AI Style · © 2026 Serhii Khomenko · https://homensai.com/ · https://github.com/HomenSAI · https://www.linkedin.com/in/serhii-khomenko-homensai/
// Тема оформления: выбор пользователя (светлая/тёмная) из localStorage, иначе — системная.
// Подключать в <head> обычным <script src> БЕЗ defer, чтобы страница не мигала при загрузке.
(function () {
  try {
    var saved = localStorage.getItem("homensai.theme");
    if (saved === "light" || saved === "dark") document.documentElement.setAttribute("data-theme", saved);
  } catch (e) {
    /* хранилище недоступно: остаётся системная тема */
  }
})();
