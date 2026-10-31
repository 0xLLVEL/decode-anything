const MODULE = "ioncube_loader_win_7.2.dll";
let installed = false;

function install(module) {
  if (installed) return;
  installed = true;
  const base = module.base;
  const end = base.add(module.size);
  console.log(`[hook] base=${base} end=${end}`);

  const counts = new Map();
  let total = 0;

  const threads = Process.enumerateThreads();
  const main = threads.length ? threads[0].id : Process.getCurrentThreadId();
  console.log(`[stalk] following thread ${main}`);

  Stalker.follow(main, {
    events: { call: true, ret: false },
    onReceive(events) {
      const p = ptr(events);
      const n = events.byteLength / 4;
      for (let i = 0; i < n; i += 4) {
        const type = p.add(i * 4).readU32();
        if (type !== 1) continue;
        const target = p.add((i + 2) * 4).readU32();
        const tp = ptr(target);
        if (tp.compare(base) < 0 || tp.compare(end) >= 0) continue;
        total++;
        const key = tp.sub(base).toUInt32 ? (target - base.toUInt32()) : target;
        counts.set(key, (counts.get(key) || 0) + 1);
      }
    },
  });

  setTimeout(() => {
    try { Stalker.unfollow(main); Stalker.flush(); } catch (e) {}
    const rows = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 40);
    console.log(`[stalk] total module calls ${total}, distinct ${counts.size}`);
    for (const [off, c] of rows) {
      console.log(`   0x${off.toString(16).padStart(6, "0")}  ${c}`);
    }
  }, 2600);
}
const m = Process.findModuleByName(MODULE);
if (m) install(m);
else { const w = setInterval(() => { const mm = Process.findModuleByName(MODULE); if (mm) { clearInterval(w); install(mm); } }, 20); }
