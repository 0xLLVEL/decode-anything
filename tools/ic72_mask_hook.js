const MODULE = "ioncube_loader_win_7.2.dll";
let installed = false;

function install(module) {
  if (installed) return;
  installed = true;
  const base = module.base;
  console.log(`[hook] base=${base}`);
  let n = 0;

  Interceptor.attach(base.add(0x8dc40), {
    onEnter() {
      n++;
      const esp = this.context.esp;
      let a1 = null, a2 = null;
      try { a1 = esp.add(4).readPointer(); a2 = esp.add(8).readPointer(); } catch (e) { return; }
      let cnt = -1, maskPtr = null, wordsPtr = null;
      try {
        cnt = a2.add(4).readS32();
        maskPtr = a2.add(0x20).readPointer();
        wordsPtr = a2.add(0xc).readPointer();
      } catch (e) {}
      console.log(`[enter#${n}] a1=${a1} a2=${a2} count=${cnt} maskPtr=${maskPtr} words=${wordsPtr}`);
      try {
        const b = new Uint8Array(maskPtr.readByteArray(Math.min(cnt > 0 ? cnt : 16, 128)));
        console.log(`   mask  ${[...b].map((x) => x.toString(16).padStart(2, "0")).join(" ")}`);
      } catch (e) { console.log(`   mask unreadable ${e}`); }
      try {
        const w = new Uint8Array(wordsPtr.readByteArray(Math.min((cnt > 0 ? cnt : 8) * 4, 256)));
        console.log(`   words ${[...w].map((x) => x.toString(16).padStart(2, "0")).join(" ")}`);
      } catch (e) { console.log(`   words unreadable ${e}`); }
    },
  });
}
const m = Process.findModuleByName(MODULE);
if (m) install(m);
else { const w = setInterval(() => { const mm = Process.findModuleByName(MODULE); if (mm) { clearInterval(w); install(mm); } }, 20); }
