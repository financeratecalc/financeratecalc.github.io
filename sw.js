// Figure Radar service worker. It does one thing: when a push arrives (it carries no content), ask the server what
// changed for this device's chosen reports and show it. Nothing is cached and no page request is intercepted.
var API = self.location.origin;   // /radar/* on this domain is answered by the server
function hex(buf) { return Array.prototype.map.call(new Uint8Array(buf), function (b) { return ("0" + b.toString(16)).slice(-2); }).join(""); }
self.addEventListener("install", function () { self.skipWaiting(); });
self.addEventListener("activate", function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener("push", function (e) {
  e.waitUntil((async function () {
    var d = { title: "FinanceRateCalc", body: "An official report was updated.", url: "https://financeratecalc.com/official-figures.html" };
    try {
      var sub = await self.registration.pushManager.getSubscription(), id = "";
      if (sub) id = hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(sub.endpoint))).slice(0, 32);
      var r = await fetch(API + "/radar/latest?e=" + id, { cache: "no-store" });
      if (r.ok) d = await r.json();
    } catch (err) {}
    await self.registration.showNotification(d.title, { body: d.body, icon: "/apple-touch-icon.png", badge: "/favicon-32.png", tag: "frc-radar", data: { url: d.url } });
  })());
});
self.addEventListener("notificationclick", function (e) {
  e.notification.close();
  e.waitUntil(self.clients.openWindow((e.notification.data && e.notification.data.url) || "https://financeratecalc.com/radar.html"));
});
