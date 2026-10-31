const MODULE = "ioncube_loader_win_7.2.dll";
let installed = false;
function install(module) {
  if (installed) return;
  installed = true;
  const base = module.base;
  console.log(`[hook] base=${base}`);
  let keyed = 0, plain = 0;
  Interceptor.attach(base.add(0x88bf0), {
    onEnter() {
      const src = this.context.ecx;
      this.hasKey = false;
      try { this.hasKey = src.add(0x18).readU32() !== 0; } catch (e) {}
      if (this.hasKey) {
        keyed++;
        if (keyed < 12) {
          const buf = src.add(0x18).readPointer();
          const len = src.add(0x1c).readS32();
          const cur = src.add(0x20).readS32();
          console.log(`[keyed#${keyed}] buf=${buf} len=${len} cursor=${cur} stored=0x${(this.context.edx & 0xff).toString(16)}`);
        }
      } else { plain++; }
    },
  });
  setInterval(() => {
    console.log(`[stats] keyed=${keyed} plain=${plain}`);
  }, 1200);
}
const m = Process.findModuleByName(MODULE);
if (m) install(m);
else {
  const w = setInterval(() => {
    const mm = Process.findModuleByName(MODULE);
    if (mm) { clearInterval(w); install(mm); }
  }, 20);
}
