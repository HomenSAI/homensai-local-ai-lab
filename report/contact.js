/* Local AI Lab · © 2026 Serhii Khomenko · https://homensai.com/ */
/* "Contact" page required in every HomenS.AI project: the contact block of HomenS.AI Style (texts, links and the address
   come from the brand data, robot to the right of the heading), in the interface language chosen in i18n.js. */
(() => {
  const host = document.getElementById("contact");
  const lang = (window.i18n && window.i18n.lang()) || "ru";
  window.HomenS.brandUi.renderContact(host, lang, {heading: host.getAttribute("data-heading") || "h2"});
})();
