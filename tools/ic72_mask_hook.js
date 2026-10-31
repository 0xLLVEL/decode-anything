const MODULE = "ioncube_loader_win_7.2.dll";
let installed = false;

function install(module) {
  if (installed) return;
  installed = true;
  const base = module.base;
  console.log(`[hook] base=${base}`);
  const stat = {};

  const sites = {
    lcg: 0x890d0,
    xsA: 0x890e0,
    xsB: 0x89100,
    pick: 0x89120,
    xsC: 0x89140,
    gen: 0x89190,
  };

  for (const [name, rva] of Object.entries(sites)) {
    stat[name] = 0;
    Interceptor.attach(base.add(rva), {
      onEnter() {
        stat[name]++;
      },
    });
  }

  setInterval(() => {
    console.log(`[stat] ${Object.entries(stat).map(([k, v]) => k + "=" + v).join(" ")}`);
  }, 1500);
}
const m = Process.findModuleByName(MODULE);
if (m) install(m);
else { const w = setInterval(() => { const mm = Process.findModuleByName(MODULE); if (mm) { clearInterval(w); install(mm); } }, 20); }
