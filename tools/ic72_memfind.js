const TARGETS = [
  { tag: "api", addr: "3f ?? ?? ?? a8 ?? ?? ?? 34 ?? ?? ?? fb ?? ?? ??", count: 111 },
  { tag: "proxy", addr: "f2 ?? ?? ?? 4b ?? ?? ?? 8a ?? ?? ?? 0d ?? ?? ??", count: 49 },
];

function scanAll() {
  const ranges = Process.enumerateRanges("rw-");
  for (const t of TARGETS) {
    let hitAddr = null;
    for (const r of ranges) {
      let hits;
      try { hits = Memory.scanSync(r.base, r.size, t.addr); } catch (e) { continue; }
      if (hits.length) { hitAddr = hits[0].address; break; }
    }
    if (!hitAddr) { console.log(`[${t.tag}] miss`); continue; }
    const raw = new Uint8Array(hitAddr.readByteArray(t.count * 4));
    console.log(`[${t.tag}] ${hitAddr} ${[...raw].map((x) => x.toString(16).padStart(2, "0")).join(" ")}`);
    const before = new Uint8Array(hitAddr.sub(0x40).readByteArray(0x30));
    console.log(`[${t.tag}-before] ${[...before].map((x) => x.toString(16).padStart(2, "0")).join(" ")}`);
    const after = new Uint8Array(hitAddr.add(t.count * 4).readByteArray(0x40));
    console.log(`[${t.tag}-after] ${[...after].map((x) => x.toString(16).padStart(2, "0")).join(" ")}`);
  }
}

setTimeout(scanAll, 2500);
