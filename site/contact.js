/* Local AI Lab · © 2026 Serhii Khomenko · https://homensai.com/ */
/* "Contact" page of the documentation site, required in every HomenS.AI project: the contact block of HomenS.AI Style
   (texts, links and the address from the brand data, the robot to the right of the heading) in the language of the page. */
(function () {
  var host = document.getElementById("contact");
  if (!host || !window.HomenS || !window.HomenS.brandUi) return;
  var lang = (document.documentElement.lang || "en").slice(0, 2);
  window.HomenS.brandUi.renderContact(host, lang, { heading: host.getAttribute("data-heading") || "h2" });
})();
