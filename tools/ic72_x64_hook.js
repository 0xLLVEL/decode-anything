const MODULE = "ioncube_loader_win_7.2.dll";
let installed = false;
function install(m) {
  if (installed) return;
  installed = true;
  const base = m.base;
  console.log(`[hook] base=${base}`);
  let n = 0;
  Interceptor.attach(base.add(0x9D340), {
    onEnter() {
      n++;
      this.n = n;
      if (n > 3) return;
      const s = this.context.rcx;
      this.s = s;
      const f = [];
      for (let i = 0; i < 4; i++) f.push("0x" + s.add(i * 4).readU32().toString(16).padStart(8, "0"));
      console.log(`[d340#${n}] state=${s} ra=0x${this.returnAddress.sub(base).toString(16)} st=[${f.join(" ")}]`);
    },
    onLeave(retval) {
      if (this.n > 3) return;
      const s = this.s;
      const f = [];
      for (let i = 0; i < 4; i++) f.push("0x" + s.add(i * 4).readU32().toString(16).padStart(8, "0"));
      console.log(`   ret=0x${(retval.toInt32() >>> 0).toString(16).padStart(8, "0")}  st'=[${f.join(" ")}]`);
    },
  });
}
const m0 = Process.findModuleByName(MODULE);
if (m0) install(m0);
else { const w = setInterval(() => { const mm = Process.findModuleByName(MODULE); if (mm) { clearInterval(w); install(mm); } }, 20); }
