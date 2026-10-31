const MODULE = "ioncube_loader_win_7.2.dll";
let installed = false;
let call = 0;

function install(module) {
  if (installed) return;
  installed = true;
  console.log(`[hook] base=${module.base}`);

  Interceptor.attach(module.base.add(0x890d0), {
    onEnter() { this.s = this.context.ecx >>> 0; },
    onLeave(r) { console.log(`[seed] ${this.s} 0x${this.s.toString(16)} -> lcg 0x${(r.toUInt32()>>>0).toString(16)}`); },
  });
  Interceptor.attach(module.base.add(0x89140), {
    onEnter() { this.s = this.context.ecx >>> 0; },
    onLeave(r) { console.log(`[seed] ${this.s} -> xs 0x${(r.toUInt32()>>>0).toString(16)}`); },
  });

  Interceptor.attach(module.base.add(0x89190), {
    onEnter(args) {
      this.n = ++call;
      this.seed = args[0];
      this.ctx = args[1];
      console.log(`[gen#${this.n}] seed=${this.seed} ctx=${this.ctx}`);
    },
    onLeave() {
      try {
        const c = this.ctx;
        const count = c.readS32();
        const cursor = c.add(4).readS32();
        const lcg = c.add(8).readU32();
        const xs = c.add(0xc).readU32();
        const fnp = c.add(0x14).readPointer();
        const arr = c.add(0x18).readPointer();
        console.log(`[gen#${this.n}] count=${count} cursor=${cursor} lcg=0x${lcg.toString(16)} xs=0x${xs.toString(16)} fn=${fnp} arr=${arr}`);
        if (!arr.isNull()) {
          const words = [];
          const n = Math.min(count, 4096);
          for (let i = 0; i < n; i++) words.push(arr.add(4 * i).readU32().toString(16).padStart(8, "0"));
          console.log(`[pool#${this.n}] ${words.join("")}`);
        }
      } catch (e) {
        console.log(`[gen#${this.n}] read fail ${e}`);
      }
    },
  });
}

const m = Process.findModuleByName(MODULE);
if (m) install(m);
else {
  const w = setInterval(() => {
    const mm = Process.findModuleByName(MODULE);
    if (mm) { clearInterval(w); install(mm); }
  }, 20);
}
