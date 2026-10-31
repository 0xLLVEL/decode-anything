/**
 * ionCube 7.2 opcode-mask source, 32-bit loader (base 0x10000000).
 *
 *   0x10088BC0  next():  al = [ecx+0x18][ [ecx+0x20] ]
 *                        cursor wraps at [ecx+0x1c]-1 back to 0
 *   0x10088BF0  decrypt(stored):  [ecx+0x18] ? next() ^ stored : stored
 *   0x10088C10  set_key(buf, len): [0x18]=buf [0x1c]=len [0x20]=0
 *
 * So the opcode mask is a repeating buffer, not a PRNG stream. Read the buffer.
 */

const MODULE = "ioncube_loader_win_7.2.dll";
let installed = false;

function hx(p, n) {
  try {
    const b = new Uint8Array(p.readByteArray(n));
    return [...b].map((x) => x.toString(16).padStart(2, "0")).join(" ");
  } catch (e) {
    return `read fail ${e}`;
  }
}

function install(module) {
  if (installed) return;
  installed = true;
  const base = module.base;
  console.log(`[hook] base=${base}`);

  Interceptor.attach(base.add(0x88c10), {
    onEnter(args) {
      const buf = args[0];
      const len = args[1].toInt32();
      if (len <= 0 || len > 0x100000) return;
      console.log(`[set_key] buf=${buf} len=${len}`);
      if (len <= 512 || len === 234 || len === 111 || len === 49 || len === 3) {
        console.log(`[set_key] ${hx(buf, Math.min(len, 128))}`);
      }
    },
  });

  Interceptor.attach(base.add(0x88bf0), {
    onEnter() {
      this.src = this.context.ecx;
      this.stored = this.context.edx & 0xff;
    },
    onLeave(r) {
      if (this.stored === undefined) return;
      const out = r.toInt32() & 0xff;
      if (this.n === undefined) this.n = 0;
      this.n++;
      if (this.n < 6) console.log(`[decrypt] stored=0x${this.stored.toString(16)} -> 0x${out.toString(16)}`);
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
