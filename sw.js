// Hangul with PV service worker: works offline, but always tries the network first
// so updates you push to GitHub show up on the next open.
const CACHE = "hangul-v13", NOTIFY_CACHE = "hangul-notify";
const SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./icon-maskable-512.png", "./apple-touch-icon.png"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(SHELL.map(u => c.add(u).catch(() => {})))));   // one missing file must not break install
  self.skipWaiting();
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE && k !== NOTIFY_CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});
self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET" || url.origin !== location.origin) return; // Gemini, translate, CDNs: untouched
  e.respondWith(
    fetch(e.request).then(r => { const copy = r.clone(); caches.open(CACHE).then(c => c.put(e.request, copy)); return r; })
      .catch(() => caches.match(e.request).then(r => r || caches.match("./index.html")))
  );
});

// Review reminders: the page keeps a small snapshot (due times, new-word counts) in NOTIFY_CACHE.
const STATE = "./__notify-state";
const today = () => { const d = new Date(); return d.getFullYear()+"-"+(d.getMonth()+1)+"-"+d.getDate(); };
async function remind(){
  const c = await caches.open(NOTIFY_CACHE);
  const r = await c.match(STATE); if (!r) return;
  const st = await r.json();
  if (!st.on || Notification.permission !== "granted") return;
  const h = new Date().getHours(); if (h < 5) return;   // quiet hours 00:00–05:00
  if (st.lastNotified && Date.now() - st.lastNotified < 6*60*60*1000) return;
  const now = Date.now(), due = (st.dues || []).filter(t => t <= now).length;
  const newLeft = Math.min(st.newTotal || 0, Math.max(0, (st.newPerDay || 0) - (st.date === today() ? st.newCount || 0 : 0)));
  if (!due && !newLeft) return;
  const vi = st.ui !== "en";
  const parts = [];
  if (due) parts.push(vi ? `${due} từ cần ôn` : `${due} word${due === 1 ? "" : "s"} to review`);
  if (newLeft) parts.push(vi ? `${newLeft} từ mới` : `${newLeft} new word${newLeft === 1 ? "" : "s"}`);
  await self.registration.showNotification(vi ? "🎯 Đến giờ ôn tiếng Hàn!" : "🎯 Time for Korean!", {
    body: parts.join(" · "), icon: "./icon-192.png", badge: "./icon-192.png", tag: "review-reminder", renotify: true
  });
  st.lastNotified = Date.now();
  await c.put(STATE, new Response(JSON.stringify(st), { headers: { "Content-Type": "application/json" } }));
}
self.addEventListener("periodicsync", e => { if (e.tag === "review-reminder") e.waitUntil(remind()); });
self.addEventListener("notificationclick", e => {
  e.notification.close();
  e.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(ws => {
    const w = ws.find(x => "focus" in x); return w ? w.focus() : self.clients.openWindow("./");
  }));
});
