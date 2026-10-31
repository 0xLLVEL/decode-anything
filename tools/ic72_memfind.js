/**
 * Find the opcode-mask array in the live loader process.
 *
 * The mask bytes are known (runtime dump ^ stored payload). Scan for them after
 * the op arrays are built, then dump the surrounding struct - if the generator
 * state sits next to the array, the seed is right there.
 */

const PATTERNS = {
  api: "00 97 0b c4 2c 80 d1 f6 ef 25 80 ca 0c ce 06 00",
  link: "9f f4 ff 2d d5 9b 7f af 48 b2 41 a6 3e cc 31 99",
  proxy: "cd 74 b1 8e 43 a3 2f 52 9b 9a d7 46 dc 08 f8 80",
};

function dumpHex(addr, len) {
  try {
    const bytes = new Uint8Array(addr.readByteArray(len));
    let out = "";
    for (let i = 0; i < bytes.length; i += 16) {
      const row = [];
      for (let j = 0; j < 16 && i + j < bytes.length; j++) {
        row.push(bytes[i + j].toString(16).padStart(2, "0"));
      }
      out += `${addr.add(i)}  ${row.join(" ")}\n`;
    }
    return out;
  } catch (e) {
    return `read fail ${e}`;
  }
}

function scanAll() {
  const ranges = Process.enumerateRanges("rw-");
  console.log(`[scan] ${ranges.length} writable ranges`);
  for (const [tag, pat] of Object.entries(PATTERNS)) {
    let found = 0;
    for (const r of ranges) {
      let hits;
      try {
        hits = Memory.scanSync(r.base, r.size, pat);
      } catch (e) {
        continue;
      }
      for (const h of hits) {
        found++;
        console.log(`[hit] ${tag} @ ${h.address} in ${r.base}-${r.base.add(r.size)}`);
        console.log(dumpHex(h.address.sub(0x40), 0x100));
        if (found >= 2) break;
      }
      if (found >= 2) break;
    }
    if (!found) console.log(`[miss] ${tag} not found in writable memory`);
  }
}

setTimeout(scanAll, 2500);

