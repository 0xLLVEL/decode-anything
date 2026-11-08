const MODULE = "ioncube_loader_win_7.2.dll";
let installed = false;
function hx(p, n) {
  const b = new Uint8Array(p.readByteArray(n));
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join(" ");
}
function install(m) {
  if (installed) return;
  installed = true;
  const base = m.base;
  console.log(`[hook] base=${base}`);
  Interceptor.attach(base.add(0xA1090), {
    onEnter() {
      const c = this.context;
      const size = c.r8.toInt32();
      if (size < 400) return;
      this.dst = c.rdx;
      this.size = size;
      this.on = true;
      console.log(`[read] dst=${c.rdx} size=${size}`);
    },
    onLeave() {
      if (!this.on) return;
      console.log(`[read] plain ${hx(this.dst, Math.min(this.size, 640))}`);
    },
  });
}
const m0 = Process.findModuleByName(MODULE);
if (m0) install(m0);
else { const w = setInterval(() => { const mm = Process.findModuleByName(MODULE); if (mm) { clearInterval(w); install(mm); } }, 20); }
